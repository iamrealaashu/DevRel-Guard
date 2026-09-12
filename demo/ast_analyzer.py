#!/usr/bin/env python3
import ast
import json
import sys

RULES_PATH = 'demo/extraction.json'

def load_rules(path):
    with open(path, 'r') as f:
        return json.load(f)


def build_import_map(tree):
    # map local name -> actual module (e.g., ml -> mylib)
    mapping = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                asname = alias.asname or alias.name
                mapping[asname] = name
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            for alias in node.names:
                asname = alias.asname or alias.name
                mapping[asname] = f"{module}.{alias.name}" if module else alias.name
    return mapping


def analyze_file(file_path, rules):
    with open(file_path, 'r') as f:
        src = f.read()
    tree = ast.parse(src)
    import_map = build_import_map(tree)
    issues = []

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node):
            # function name detection
            func = node.func
            # Check attribute calls like mylib.foo or ml.foo
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                base = func.value.id
                attr = func.attr
                resolved = import_map.get(base, base)
                # rule: mylib.foo removed
                if resolved == 'mylib' and attr == 'foo':
                    issues.append({
                        'line_number': node.lineno,
                        'affected_code': src.splitlines()[node.lineno-1].rstrip(),
                        'rule_matched': 'mylib.foo -> mylib.bar (renamed + signature change)',
                        'reason': "`mylib.foo` was removed; use `mylib.bar(a, b=b)`."
                    })
                # rule: mylib.process_items count type changed
                if resolved == 'mylib' and attr == 'process_items':
                    # second arg (index 1) if present
                    if len(node.args) >= 2:
                        arg = node.args[1]
                        if isinstance(arg, ast.Constant):
                            if not isinstance(arg.value, str):
                                issues.append({
                                    'line_number': node.lineno,
                                    'affected_code': src.splitlines()[node.lineno-1].rstrip(),
                                    'rule_matched': 'mylib.process_items.count type_changed',
                                    'reason': '`count` argument is a non-string constant; must be a string in new API.'
                                })
                        else:
                            # variable or expression
                            issues.append({
                                'line_number': node.lineno,
                                'affected_code': src.splitlines()[node.lineno-1].rstrip(),
                                'rule_matched': 'mylib.process_items.count type_changed',
                                'reason': '`count` is passed via variable/expression; ensure it is converted to string when migrating.'
                            })
            self.generic_visit(node)

    Visitor().visit(tree)
    return issues


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: ast_analyzer.py <target-file> [output-json]')
        sys.exit(2)
    target = sys.argv[1]
    outpath = sys.argv[2] if len(sys.argv) > 2 else None
    rules = load_rules(RULES_PATH)
    issues = analyze_file(target, rules)
    out = json.dumps(issues, indent=2)
    if outpath:
        with open(outpath, 'w') as f:
            f.write(out)
    else:
        print(out)
