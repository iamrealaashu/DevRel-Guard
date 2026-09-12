"""Ecosystem breaking change rule catalog and registry."""

from devrel_guard.rules.catalog import catalog, RuleCatalog
import devrel_guard.rules.pydantic_rules
import devrel_guard.rules.langchain_rules
import devrel_guard.rules.openai_rules
import devrel_guard.rules.generic_rules

__all__ = ["catalog", "RuleCatalog"]
