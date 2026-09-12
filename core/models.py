"""Pydantic data models for DevRel Guard."""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class BreakingChangeType(str, Enum):
    REMOVED_METHOD = "removed_method"
    RENAMED_METHOD = "renamed_method"
    RENAMED_PARAM = "renamed_param"
    MOVED_IMPORT = "moved_import"
    SIGNATURE_CHANGE = "signature_change"
    BEHAVIOR_CHANGE = "behavior_change"
    REMOVED_ATTRIBUTE = "removed_attribute"
    CLASS_DEPRECATION = "class_deprecation"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DependencyChange(BaseModel):
    package_name: str
    old_version: str
    new_version: str
    manifest_file: str
    is_major_bump: bool = False
    details: Optional[str] = None


class BreakingRule(BaseModel):
    id: str
    package: str
    target_version_min: str
    target_version_max: Optional[str] = None
    rule_type: BreakingChangeType
    symbol: str
    description: str
    migration_guide_url: str
    old_pattern: str
    new_pattern: str
    severity: Severity = Severity.HIGH
    examples: List[Dict[str, str]] = Field(default_factory=list)


class ASTViolation(BaseModel):
    id: str
    file_path: str
    line_number: int
    end_line_number: int
    col_offset: int
    end_col_offset: int
    symbol: str
    node_type: str
    code_snippet: str
    rule: BreakingRule
    context_before: List[str] = Field(default_factory=list)
    context_after: List[str] = Field(default_factory=list)


class FixSuggestion(BaseModel):
    violation_id: str
    file_path: str
    start_line: int
    end_line: int
    original_code: str
    replacement_code: str
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    changelog_reference: str
    verified: bool = False
    verification_notes: Optional[str] = None


class PRReviewComment(BaseModel):
    path: str
    line: int
    side: str = "RIGHT"
    suggestion_block: str
    body: str
    title: str
    violation_id: Optional[str] = None


class GuardReport(BaseModel):
    pr_id: Optional[str] = None
    repo_name: Optional[str] = None
    dependency_changes: List[DependencyChange] = Field(default_factory=list)
    violations: List[ASTViolation] = Field(default_factory=list)
    fixes: List[FixSuggestion] = Field(default_factory=list)
    comments: List[PRReviewComment] = Field(default_factory=list)
    passed: bool = True
    duration_seconds: float = 0.0
    summary_markdown: str = ""
    ast_nodes_scanned: int = 0
