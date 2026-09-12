"""LangGraph Node Implementations for DevRel Guard agent workflow."""

from __future__ import annotations
import os
from typing import Any, Dict, List
from devrel_guard.agent.state import GuardAgentState
from devrel_guard.agent.llm import llm_client
from devrel_guard.core.ast_inspector import inspect_source_code
from devrel_guard.core.changelog_miner import ChangelogMiner
from devrel_guard.core.dep_scanner import scan_diff_for_dependency_changes
from devrel_guard.core.diff_parser import parse_unified_diff
from devrel_guard.core.models import ASTViolation, FixSuggestion, PRReviewComment
from devrel_guard.core.pr_formatter import PRReviewFormatter
from devrel_guard.core.refactorer import CodeRefactorer
from devrel_guard.core.verifier import PatchVerifier


def scan_diff_node(state: GuardAgentState) -> Dict[str, Any]:
    """Node 1: Parses PR diff, extracts dependency upgrades and modified source files."""
    raw_diff = state.get("raw_diff", "")
    source_files = dict(state.get("source_files", {}))
    repo_root = state.get("repo_root")
    history = list(state.get("step_history", []))

    parsed = parse_unified_diff(raw_diff)
    dep_changes = scan_diff_for_dependency_changes(parsed)

    modified_sources = [f.path for f in parsed.get_source_diffs() if f.path.endswith(".py")]

    # If repo_root is provided and files not in source_files, read from filesystem
    if repo_root and os.path.isdir(repo_root):
        for path in modified_sources:
            full_path = os.path.join(repo_root, path)
            if os.path.exists(full_path) and path not in source_files:
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        source_files[path] = f.read()
                except Exception:
                    pass

    history.append(
        f"Node 1: ScanDiff completed. Detected {len(dep_changes)} dependency bumps and {len(modified_sources)} Python source files."
    )

    return {
        "dependency_changes": dep_changes,
        "modified_source_files": modified_sources,
        "source_files": source_files,
        "step_history": history,
    }


def mine_changelog_node(state: GuardAgentState) -> Dict[str, Any]:
    """Node 2: Mines breaking change rules from ecosystem catalog and changelogs."""
    dep_changes = state.get("dependency_changes", [])
    custom_changelogs = state.get("custom_changelogs")
    history = list(state.get("step_history", []))

    miner = ChangelogMiner()
    rules = miner.mine_for_dependencies(dep_changes, custom_changelog_text=custom_changelogs)

    history.append(
        f"Node 2: MineChangelog completed. Discovered {len(rules)} applicable breaking change rules."
    )

    return {
        "applicable_rules": rules,
        "step_history": history,
    }


def inspect_ast_node(state: GuardAgentState) -> Dict[str, Any]:
    """Node 3: Static AST inspection across source files to pinpoint breaking call sites."""
    source_files = state.get("source_files", {})
    rules = state.get("applicable_rules", [])
    history = list(state.get("step_history", []))

    all_violations: List[ASTViolation] = []
    total_nodes = 0

    for file_path, code in source_files.items():
        if not file_path.endswith(".py"):
            continue
        violations, nodes_count = inspect_source_code(file_path, code, rules)
        all_violations.extend(violations)
        total_nodes += nodes_count

    history.append(
        f"Node 3: InspectAST completed. Scanned {total_nodes} AST nodes, identified {len(all_violations)} breaking call-sites."
    )

    return {
        "violations": all_violations,
        "nodes_scanned": total_nodes,
        "step_history": history,
    }


def refactor_code_node(state: GuardAgentState) -> Dict[str, Any]:
    """Node 4: Agentic refactoring synthesizing AST-sound replacement patches."""
    violations = state.get("violations", [])
    source_files = state.get("source_files", {})
    history = list(state.get("step_history", []))

    refactorer = CodeRefactorer()
    fixes: List[FixSuggestion] = []

    for v in violations:
        code = source_files.get(v.file_path, "")
        fix = refactorer.refactor_violation(v, code)

        # If deterministic pattern failed, attempt LLM synthesis if available
        if not fix and llm_client.is_available:
            llm_rep = llm_client.synthesize_refactor(
                snippet=v.code_snippet,
                rule_description=v.rule.description,
                old_pattern=v.rule.old_pattern,
                new_pattern=v.rule.new_pattern,
                package_name=v.rule.package,
            )
            if llm_rep:
                fix = FixSuggestion(
                    violation_id=v.id,
                    file_path=v.file_path,
                    start_line=v.line_number,
                    end_line=v.end_line_number,
                    original_code=v.code_snippet,
                    replacement_code=llm_rep,
                    explanation=f"LLM-synthesized refactor conforming to {v.rule.package} breaking change.",
                    confidence=0.88,
                    changelog_reference=v.rule.migration_guide_url,
                )

        if fix:
            fixes.append(fix)

    history.append(
        f"Node 4: RefactorCode completed. Synthesized {len(fixes)} code patches for {len(violations)} violations."
    )

    return {
        "fixes": fixes,
        "step_history": history,
    }


def verify_patches_node(state: GuardAgentState) -> Dict[str, Any]:
    """Node 5: Verifies patches with AST syntax checking and delta soundess."""
    fixes = state.get("fixes", [])
    source_files = state.get("source_files", {})
    history = list(state.get("step_history", []))

    verifier = PatchVerifier()
    refactored: Dict[str, str] = {}
    verified_fixes: List[FixSuggestion] = []
    overall_valid = True

    # Group fixes by file
    fixes_by_file: Dict[str, List[FixSuggestion]] = {}
    for f in fixes:
        fixes_by_file.setdefault(f.file_path, []).append(f)

    for file_path, code in source_files.items():
        file_fixes = fixes_by_file.get(file_path, [])
        if file_fixes:
            is_valid, patched_code, updated_fixes = verifier.apply_and_verify(code, file_fixes)
            if is_valid:
                refactored[file_path] = patched_code
                verified_fixes.extend(updated_fixes)
            else:
                overall_valid = False
                verified_fixes.extend(updated_fixes)
        else:
            refactored[file_path] = code

    history.append(
        f"Node 5: VerifyPatches completed. Verification status: {'PASSED' if overall_valid else 'FAILED'} across {len(verified_fixes)} patches."
    )

    return {
        "refactored_files": refactored,
        "verified_fixes": verified_fixes,
        "verification_passed": overall_valid,
        "step_history": history,
    }


def format_pr_review_node(state: GuardAgentState) -> Dict[str, Any]:
    """Node 6: Produces GitHub PR review comments with inline ```suggestion syntax and executive summary."""
    violations = state.get("violations", [])
    fixes = state.get("verified_fixes") or state.get("fixes", [])
    dep_changes = state.get("dependency_changes", [])
    nodes_scanned = state.get("nodes_scanned", 0)
    history = list(state.get("step_history", []))

    formatter = PRReviewFormatter()
    fix_map = {f.violation_id: f for f in fixes}

    comments: List[PRReviewComment] = []
    for v in violations:
        fix = fix_map.get(v.id)
        comment = formatter.format_inline_comment(v, fix)
        comments.append(comment)

    summary = formatter.format_executive_summary(
        dependency_changes=dep_changes,
        violations=violations,
        fixes=fixes,
        nodes_scanned=nodes_scanned,
    )

    history.append(
        f"Node 6: FormatPRReview completed. Generated {len(comments)} inline GitHub suggestions and executive summary report."
    )

    return {
        "review_comments": comments,
        "summary_markdown": summary,
        "fixes": fixes,
        "verified_fixes": fixes,
        "passed": len(violations) == 0,
        "step_history": history,
    }
