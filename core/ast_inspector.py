"""AST Visitor and Static Analysis Inspector for breaking change detection."""

from __future__ import annotations
import ast
import os
from typing import Dict, List, Optional, Set, Tuple
from devrel_guard.core.models import ASTViolation, BreakingRule, BreakingChangeType


class ASTImportTracker:
    """Tracks imported symbols and their origin modules/aliases within a Python file."""

    def __init__(self) -> None:
        # local_alias -> module_name, e.g. "pd" -> "pydantic"
        self.module_aliases: Dict[str, str] = {}
        # local_name -> (module, original_name), e.g. "val" -> ("pydantic", "validator")
        self.symbol_imports: Dict[str, Tuple[str, str]] = {}

    def register_import(self, node: ast.Import) -> None:
        for alias in node.names:
            local = alias.asname or alias.name
            self.module_aliases[local] = alias.name

    def register_import_from(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            local = alias.asname or alias.name
            self.symbol_imports[local] = (module, alias.name)

    def resolves_to(self, local_name: str, package: str, symbol: Optional[str] = None) -> bool:
        """Check if local_name resolves to a package and optional symbol."""
        pkg = package.lower().replace("_", "-")

        # Direct symbol import: from package import symbol as local_name
        if local_name in self.symbol_imports:
            mod, orig_sym = self.symbol_imports[local_name]
            mod_pkg = mod.split(".")[0].lower().replace("_", "-")
            if mod_pkg == pkg:
                if symbol is None or orig_sym == symbol:
                    return True

        # Module alias: import package as local_name
        if local_name in self.module_aliases:
            mod = self.module_aliases[local_name]
            mod_pkg = mod.split(".")[0].lower().replace("_", "-")
            return mod_pkg == pkg

        return False


class CodebaseASTInspector(ast.NodeVisitor):
    """Walks the Python AST to detect call-sites and constructs matching breaking change rules."""

    def __init__(
        self,
        file_path: str,
        source_code: str,
        rules: List[BreakingRule],
    ) -> None:
        self.file_path = file_path
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.rules = rules
        self.rules_by_pkg: Dict[str, List[BreakingRule]] = {}
        for r in rules:
            pkg = r.package.lower().replace("_", "-")
            self.rules_by_pkg.setdefault(pkg, []).append(r)

        self.import_tracker = ASTImportTracker()
        self.violations: List[ASTViolation] = []
        self.nodes_scanned: int = 0
        self.current_class_name: Optional[str] = None
        self.class_stack: List[str] = []
        self.model_classes: Set[str] = set()

    def _get_snippet(self, start_line: int, end_line: int) -> str:
        s_idx = max(0, start_line - 1)
        e_idx = min(len(self.source_lines), end_line)
        return "\n".join(self.source_lines[s_idx:e_idx])

    def _get_context(self, line: int, window: int = 2) -> Tuple[List[str], List[str]]:
        before_start = max(0, line - 1 - window)
        before_end = max(0, line - 1)
        after_start = min(len(self.source_lines), line)
        after_end = min(len(self.source_lines), line + window)
        return self.source_lines[before_start:before_end], self.source_lines[after_start:after_end]

    def _add_violation(
        self,
        node: ast.AST,
        symbol: str,
        rule: BreakingRule,
        custom_snippet: Optional[str] = None,
    ) -> None:
        start_line = getattr(node, "lineno", 1)
        end_line = getattr(node, "end_lineno", start_line)
        col = getattr(node, "col_offset", 0)
        end_col = getattr(node, "end_col_offset", 0)

        snippet = custom_snippet or self._get_snippet(start_line, end_line)
        ctx_before, ctx_after = self._get_context(start_line)

        v_id = f"{os.path.basename(self.file_path)}:L{start_line}:{rule.id}"
        # Avoid duplicate violations for the same node and rule
        if any(v.id == v_id for v in self.violations):
            return

        self.violations.append(
            ASTViolation(
                id=v_id,
                file_path=self.file_path,
                line_number=start_line,
                end_line_number=end_line,
                col_offset=col,
                end_col_offset=end_col,
                symbol=symbol,
                node_type=type(node).__name__,
                code_snippet=snippet,
                rule=rule,
                context_before=ctx_before,
                context_after=ctx_after,
            )
        )

    def visit(self, node: ast.AST) -> None:
        self.nodes_scanned += 1
        super().visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        self.import_tracker.register_import(node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.import_tracker.register_import_from(node)
        module = node.module or ""
        pkg = module.split(".")[0].lower().replace("_", "-")

        if pkg in self.rules_by_pkg:
            for rule in self.rules_by_pkg[pkg]:
                if rule.rule_type == BreakingChangeType.MOVED_IMPORT:
                    # Check if imported name or module matches rule
                    for alias in node.names:
                        # e.g., from pydantic import BaseSettings
                        if rule.symbol == alias.name:
                            self._add_violation(node, alias.name, rule)
                        # e.g., from langchain.chat_models import ChatOpenAI
                        elif rule.symbol == alias.name and (rule.old_pattern in f"from {module} import {alias.name}"):
                            self._add_violation(node, alias.name, rule)

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Check if class inherits from BaseModel
        is_pydantic_model = any(
            (isinstance(b, ast.Name) and (b.id == "BaseModel" or self.import_tracker.resolves_to(b.id, "pydantic", "BaseModel")))
            or (isinstance(b, ast.Attribute) and b.attr == "BaseModel")
            for b in node.bases
        )
        if is_pydantic_model:
            self.model_classes.add(node.name)

        self.class_stack.append(node.name)
        # Check Config class inside a Pydantic model class
        if node.name == "Config" and len(self.class_stack) > 1:
            parent_class = self.class_stack[-2]
            if parent_class in self.model_classes and "pydantic" in self.rules_by_pkg:
                for rule in self.rules_by_pkg["pydantic"]:
                    if rule.symbol == "Config" and rule.rule_type == BreakingChangeType.CLASS_DEPRECATION:
                        self._add_violation(node, "class Config", rule)

        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Check decorators, e.g., @validator('field') or @check_field('field')
        for dec in node.decorator_list:
            dec_name = ""
            if isinstance(dec, ast.Name):
                dec_name = dec.id
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    dec_name = dec.func.id
                elif isinstance(dec.func, ast.Attribute):
                    dec_name = dec.func.attr

            if dec_name:
                for pkg, rules in self.rules_by_pkg.items():
                    for rule in rules:
                        # Match direct name or aliased imported symbol
                        is_match = False
                        if rule.symbol == dec_name:
                            is_match = True
                        elif self.import_tracker.resolves_to(dec_name, pkg, rule.symbol):
                            is_match = True

                        if is_match:
                            self._add_violation(dec, dec_name, rule)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check call method name, e.g. .dict(), .json(), .parse_raw(...)
        if isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr

            for pkg, rules in self.rules_by_pkg.items():
                for rule in rules:
                    # 1. Attribute call on instance or class: .dict(), .parse_raw, .run
                    if rule.symbol == attr_name and rule.rule_type in (
                        BreakingChangeType.RENAMED_METHOD,
                        BreakingChangeType.REMOVED_METHOD,
                    ):
                        self._add_violation(node, attr_name, rule)

                    # 2. Fully-qualified compound call: ChatCompletion.create
                    elif "." in rule.symbol:
                        sym_parts = rule.symbol.split(".")
                        # e.g., ChatCompletion.create
                        if attr_name == sym_parts[-1]:
                            val = node.func.value
                            if isinstance(val, ast.Attribute) and val.attr == sym_parts[0]:
                                self._add_violation(node, rule.symbol, rule)
                            elif isinstance(val, ast.Name) and val.id == sym_parts[0]:
                                self._add_violation(node, rule.symbol, rule)

        # Check call arguments / keywords: e.g. Query(..., regex="...")
        for kw in node.keywords:
            if kw.arg:
                for pkg, rules in self.rules_by_pkg.items():
                    for rule in rules:
                        if rule.symbol == kw.arg and rule.rule_type == BreakingChangeType.RENAMED_PARAM:
                            self._add_violation(kw, kw.arg, rule)

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # Check assignments like openai.api_key = ...
        for target in node.targets:
            if isinstance(target, ast.Attribute):
                attr_name = target.attr
                for pkg, rules in self.rules_by_pkg.items():
                    for rule in rules:
                        if rule.symbol == attr_name and rule.rule_type == BreakingChangeType.BEHAVIOR_CHANGE:
                            if isinstance(target.value, ast.Name) and self.import_tracker.resolves_to(
                                target.value.id, pkg
                            ):
                                self._add_violation(node, attr_name, rule)

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        # Check exception classes: except openai.error.InvalidRequestError:
        if node.type:
            exc_str = ast.unparse(node.type) if hasattr(ast, "unparse") else ""
            for pkg, rules in self.rules_by_pkg.items():
                for rule in rules:
                    if rule.symbol in exc_str and rule.rule_type == BreakingChangeType.CLASS_DEPRECATION:
                        self._add_violation(node.type, rule.symbol, rule)

        self.generic_visit(node)


def inspect_source_code(
    file_path: str,
    source_code: str,
    rules: List[BreakingRule],
) -> Tuple[List[ASTViolation], int]:
    """Parse source code into AST and inspect for breaking changes against rules."""
    try:
        tree = ast.parse(source_code, filename=file_path)
    except SyntaxError:
        # Non-python file or syntax error
        return [], 0

    inspector = CodebaseASTInspector(
        file_path=file_path,
        source_code=source_code,
        rules=rules,
    )
    inspector.visit(tree)
    return inspector.violations, inspector.nodes_scanned
