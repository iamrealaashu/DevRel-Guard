"""GitHub PR Review and Inline Suggestion Formatter."""

from __future__ import annotations
from typing import List, Optional
from devrel_guard.core.models import (
    ASTViolation,
    DependencyChange,
    FixSuggestion,
    GuardReport,
    PRReviewComment,
)


class PRReviewFormatter:
    """Formats findings into GitHub native inline suggestions and executive summary comments."""

    def format_inline_comment(
        self,
        violation: ASTViolation,
        fix: Optional[FixSuggestion],
    ) -> PRReviewComment:
        rule = violation.rule
        confidence_pct = int((fix.confidence if fix else 0.8) * 100)

        badge_color = {
            "CRITICAL": "🔴 CRITICAL",
            "HIGH": "🟠 HIGH",
            "MEDIUM": "🟡 MEDIUM",
            "LOW": "🔵 LOW",
        }.get(rule.severity.value, "⚪ INFO")

        lines = [
            "### 🛡️ DevRel Guard: Breaking Change Detected",
            "",
            f"**Severity**: `{badge_color}` | **Rule**: `{rule.id}` | **Confidence**: `{confidence_pct}%`",
            "",
            f"> **Issue**: {rule.description}",
            "",
        ]

        suggestion_block = ""
        if fix and fix.replacement_code:
            suggestion_block = f"```suggestion\n{fix.replacement_code}\n```"
            lines.append("**Suggested Fix:**")
            lines.append(suggestion_block)
            lines.append("")

        lines.extend([
            f"📖 **Migration Docs**: [{rule.package} Migration Guide]({rule.migration_guide_url})",
            "",
            "_Generated autonomously by [DevRel Guard](https://github.com/google/devrel-guard) AST Static Analysis._",
        ])

        body = "\n".join(lines)
        return PRReviewComment(
            path=violation.file_path,
            line=violation.line_number,
            side="RIGHT",
            suggestion_block=suggestion_block,
            body=body,
            title=f"Breaking change in `{rule.symbol}` ({rule.package})",
            violation_id=violation.id,
        )

    def format_executive_summary(
        self,
        dependency_changes: List[DependencyChange],
        violations: List[ASTViolation],
        fixes: List[FixSuggestion],
        nodes_scanned: int = 0,
        duration: float = 0.0,
    ) -> str:
        passed = len(violations) == 0

        status_header = (
            "## 🛡️ DevRel Guard: All Dependency Changes Verified Clean ✅"
            if passed
            else "## 🛡️ DevRel Guard: Action Required — Breaking Changes Detected ⚠️"
        )

        lines = [
            status_header,
            "",
            "DevRel Guard static AST analyzer and agentic CI/CD bot has inspected this PR for dependency breaking changes.",
            "",
            "### 📦 Dependency Upgrades Detected",
            "",
            "| Package | Current Version | PR Version | Major / Breaking? | Status |",
            "| :--- | :--- | :--- | :---: | :--- |",
        ]

        for dep in dependency_changes:
            is_major = "🚨 YES" if dep.is_major_bump else "🟢 Minor/Patch"
            pkg_violations = [v for v in violations if v.rule.package == dep.package_name]
            dep_status = f"⚠️ {len(pkg_violations)} breaking call-sites" if pkg_violations else "✅ Safe"
            lines.append(
                f"| `{dep.package_name}` | `{dep.old_version}` | `{dep.new_version}` | {is_major} | {dep_status} |"
            )

        if not dependency_changes:
            lines.append("| _No manifest changes detected_ | - | - | - | - |")

        lines.extend([
            "",
            "### 🔍 Static Analysis & AST Audit Results",
            "",
            f"- **AST Nodes Scanned**: `{nodes_scanned}`",
            f"- **Breaking Call-Sites Pinpointed**: `{len(violations)}`",
            f"- **Automated Verified Fixes Generated**: `{len(fixes)}`",
            f"- **Scan Duration**: `{duration:.2f}s`",
            "",
        ])

        if violations:
            lines.extend([
                "### 🚨 Detected Violations & Inline Suggestions",
                "",
                "| Location | Symbol | Rule ID | Severity | Action |",
                "| :--- | :--- | :--- | :---: | :--- |",
            ])
            for v in violations:
                loc = f"`{v.file_path}:{v.line_number}`"
                action_text = "✅ Inline suggestion posted" if any(f.violation_id == v.id for f in fixes) else "⚠️ Manual review"
                lines.append(
                    f"| {loc} | `{v.symbol}` | `{v.rule.id}` | `{v.rule.severity.value}` | {action_text} |"
                )

            lines.extend([
                "",
                "> **Next Steps**: Review the inline suggestions below and click **Commit suggestion** to merge fixes directly.",
            ])

        lines.extend([
            "",
            "---",
            "_Protected by **DevRel Guard** • Automated Dependency Health for Modern Software_",
        ])

        return "\n".join(lines)
