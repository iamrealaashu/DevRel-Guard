"""Breaking change rule catalog registry."""

from __future__ import annotations
import re
from typing import Dict, List, Optional
from devrel_guard.core.models import BreakingRule, BreakingChangeType, Severity


class RuleCatalog:
    """Central repository of known breaking changes across the open-source ecosystem."""

    def __init__(self) -> None:
        self._rules: Dict[str, List[BreakingRule]] = {}

    def register(self, rule: BreakingRule) -> None:
        pkg = rule.package.lower().replace("_", "-")
        if pkg not in self._rules:
            self._rules[pkg] = []
        self._rules[pkg].append(rule)

    def get_rules_for_package(
        self, package_name: str, target_version: Optional[str] = None
    ) -> List[BreakingRule]:
        pkg = package_name.lower().replace("_", "-")
        rules = self._rules.get(pkg, [])
        if not target_version:
            return list(rules)

        # Filter by target version if specified
        applicable = []
        for r in rules:
            if self._is_version_applicable(target_version, r.target_version_min, r.target_version_max):
                applicable.append(r)
        return applicable

    def get_all_rules(self) -> List[BreakingRule]:
        all_rules = []
        for r_list in self._rules.values():
            all_rules.extend(r_list)
        return all_rules

    def get_rule_by_id(self, rule_id: str) -> Optional[BreakingRule]:
        for r_list in self._rules.values():
            for r in r_list:
                if r.id == rule_id:
                    return r
        return None

    @staticmethod
    def _is_version_applicable(
        version: str, min_ver: str, max_ver: Optional[str] = None
    ) -> bool:
        def to_ints(v: str) -> List[int]:
            return [int(x) for x in re.findall(r"\d+", v)] or [0]

        v_parts = to_ints(version)
        min_parts = to_ints(min_ver)

        # Pad to equal length
        max_len = max(len(v_parts), len(min_parts))
        v_parts += [0] * (max_len - len(v_parts))
        min_parts += [0] * (max_len - len(min_parts))

        if v_parts < min_parts:
            return False

        if max_ver:
            max_parts = to_ints(max_ver)
            max_len2 = max(len(v_parts), len(max_parts))
            v_parts_padded = v_parts + [0] * (max_len2 - len(v_parts))
            max_parts += [0] * (max_len2 - len(max_parts))
            if v_parts_padded >= max_parts:
                return False

        return True


# Global singleton catalog instance
catalog = RuleCatalog()
