"""Patch Verifier and Safety Guard."""

from __future__ import annotations
import ast
from typing import List, Optional, Tuple
from devrel_guard.core.models import FixSuggestion


class PatchVerifier:
    """Verifies generated patches for syntactic correctness and AST integrity."""

    def apply_and_verify(
        self,
        original_source: str,
        fixes: List[FixSuggestion],
    ) -> Tuple[bool, str, List[FixSuggestion]]:
        """Apply fixes from bottom-to-top to preserve line numbers, then verify syntax."""
        if not fixes:
            return True, original_source, []

        # Sort fixes descending by start_line to avoid index shift
        sorted_fixes = sorted(fixes, key=lambda f: f.start_line, reverse=True)
        lines = original_source.splitlines()

        for fix in sorted_fixes:
            s_idx = fix.start_line - 1
            e_idx = fix.end_line

            # Replace lines [s_idx:e_idx] with replacement_code
            rep_lines = fix.replacement_code.splitlines()
            lines[s_idx:e_idx] = rep_lines

        candidate_code = "\n".join(lines)

        # 1. Syntactic AST parse check
        try:
            ast.parse(candidate_code)
            for fix in fixes:
                fix.verified = True
                fix.verification_notes = "AST parsed successfully; valid Python syntax."
            return True, candidate_code, fixes
        except SyntaxError as e:
            for fix in fixes:
                fix.verified = False
                fix.verification_notes = f"Syntax error introduced: {e.msg} at line {e.lineno}"
                fix.confidence = max(0.0, fix.confidence - 0.4)
            return False, original_source, fixes

    def verify_single_fix(
        self,
        original_source: str,
        fix: FixSuggestion,
    ) -> Tuple[bool, Optional[str]]:
        lines = original_source.splitlines()
        s_idx = fix.start_line - 1
        e_idx = fix.end_line
        rep_lines = fix.replacement_code.splitlines()
        lines[s_idx:e_idx] = rep_lines
        candidate_code = "\n".join(lines)

        try:
            ast.parse(candidate_code)
            fix.verified = True
            fix.verification_notes = "AST syntax verified."
            return True, None
        except SyntaxError as e:
            fix.verified = False
            fix.verification_notes = f"SyntaxError: {e.msg}"
            return False, e.msg
