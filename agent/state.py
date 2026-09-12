"""LangGraph state definition for DevRel Guard agent."""

from __future__ import annotations
from typing import Dict, List, Optional
from typing_extensions import TypedDict
from devrel_guard.core.models import (
    ASTViolation,
    BreakingRule,
    DependencyChange,
    FixSuggestion,
    PRReviewComment,
)


class GuardAgentState(TypedDict, total=False):
    # Input
    raw_diff: str
    repo_root: Optional[str]
    source_files: Dict[str, str]  # file_path -> code content
    custom_changelogs: Optional[Dict[str, str]]

    # Step 1: Scanner output
    dependency_changes: List[DependencyChange]
    modified_source_files: List[str]

    # Step 2: Miner output
    applicable_rules: List[BreakingRule]

    # Step 3: Inspector output
    violations: List[ASTViolation]
    nodes_scanned: int

    # Step 4: Refactorer output
    fixes: List[FixSuggestion]

    # Step 5: Verifier output
    refactored_files: Dict[str, str]
    verified_fixes: List[FixSuggestion]
    verification_passed: bool

    # Step 6: PR Review Formatter output
    review_comments: List[PRReviewComment]
    summary_markdown: str
    passed: bool

    # Execution telemetry
    step_history: List[str]
    error_message: Optional[str]
