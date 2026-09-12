"""Changelog miner and breaking change rule extractor."""

from __future__ import annotations
import re
from typing import Dict, List, Optional
from devrel_guard.core.models import BreakingRule, BreakingChangeType, DependencyChange, Severity
from devrel_guard.rules.catalog import catalog


BREAKING_SECTION_RE = re.compile(
    r"(?:^|\n)#{1,4}\s*(?:breaking\s*changes?|deprecations?|removals?|migrat\w+)(.*?)(?=\n#{1,3}\s|\Z)",
    re.IGNORECASE | re.DOTALL,
)

BULLET_ITEM_RE = re.compile(
    r"(?:^|\n)\s*[-*+]\s+(.*?)(?=\n\s*[-*+]|\Z)",
    re.DOTALL,
)


class ChangelogMiner:
    """Mines breaking change patterns from curated catalog, release notes, and changelogs."""

    def __init__(self) -> None:
        self.catalog = catalog

    def mine_for_dependencies(
        self,
        dependencies: List[DependencyChange],
        custom_changelog_text: Optional[Dict[str, str]] = None,
    ) -> List[BreakingRule]:
        """Collect all breaking rules applicable to the given dependency bumps."""
        applicable_rules: List[BreakingRule] = []
        seen_ids = set()

        for dep in dependencies:
            # 1. Search curated ecosystem catalog
            cat_rules = self.catalog.get_rules_for_package(
                dep.package_name, target_version=dep.new_version
            )
            for r in cat_rules:
                if r.id not in seen_ids:
                    applicable_rules.append(r)
                    seen_ids.add(r.id)

            # 2. If user or PR provided raw changelog markdown for this package
            if custom_changelog_text and dep.package_name in custom_changelog_text:
                parsed_rules = self.parse_markdown_changelog(
                    package_name=dep.package_name,
                    version=dep.new_version,
                    changelog_markdown=custom_changelog_text[dep.package_name],
                )
                for r in parsed_rules:
                    if r.id not in seen_ids:
                        applicable_rules.append(r)
                        seen_ids.add(r.id)

        return applicable_rules

    def parse_markdown_changelog(
        self, package_name: str, version: str, changelog_markdown: str
    ) -> List[BreakingRule]:
        """Extract breaking change rules dynamically from a markdown changelog."""
        rules: List[BreakingRule] = []
        if not changelog_markdown:
            return rules

        sections = BREAKING_SECTION_RE.findall(changelog_markdown)
        content_to_scan = " ".join(sections) if sections else changelog_markdown

        bullets = BULLET_ITEM_RE.findall(content_to_scan)
        for idx, bullet in enumerate(bullets):
            text = bullet.strip().replace("\n", " ")
            # Look for code symbols inside backticks: `symbol`
            code_symbols = re.findall(r"`([a-zA-Z0-9_\.\(\)]+)`", text)
            symbol = code_symbols[0] if code_symbols else "unknown"

            # Determine rule type heuristic
            lower = text.lower()
            if "remove" in lower or "deleted" in lower:
                rtype = BreakingChangeType.REMOVED_METHOD
            elif "rename" in lower:
                rtype = BreakingChangeType.RENAMED_METHOD
            elif "import" in lower or "moved" in lower:
                rtype = BreakingChangeType.MOVED_IMPORT
            elif "param" in lower or "arg" in lower:
                rtype = BreakingChangeType.RENAMED_PARAM
            else:
                rtype = BreakingChangeType.BEHAVIOR_CHANGE

            rules.append(
                BreakingRule(
                    id=f"{package_name}-{symbol}-{idx}",
                    package=package_name,
                    target_version_min=version,
                    rule_type=rtype,
                    symbol=symbol,
                    description=text[:200],
                    migration_guide_url="https://pypi.org/project/" + package_name,
                    old_pattern=symbol,
                    new_pattern=f"Updated API for {symbol}",
                    severity=Severity.HIGH,
                )
            )

        return rules
