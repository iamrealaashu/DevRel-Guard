"""Generic ecosystem breaking rules for FastAPI, Requests, Urllib3, Pandas."""

from devrel_guard.core.models import BreakingRule, BreakingChangeType, Severity
from devrel_guard.rules.catalog import catalog


GENERIC_RULES = [
    BreakingRule(
        id="fastapi-query-regex-to-pattern",
        package="fastapi",
        target_version_min="0.100.0",
        rule_type=BreakingChangeType.RENAMED_PARAM,
        symbol="regex",
        description="In FastAPI 0.100.0+, the `regex` parameter in `Query`, `Path`, `Header` is deprecated in favor of `pattern`.",
        migration_guide_url="https://fastapi.tiangolo.com/release-notes/#01000",
        old_pattern="Query(..., regex='^[a-z]+$')",
        new_pattern="Query(..., pattern='^[a-z]+$')",
        severity=Severity.HIGH,
        examples=[
            {
                "old": "q: str = Query(None, regex='^[a-zA-Z]+$')",
                "new": "q: str = Query(None, pattern='^[a-zA-Z]+$')",
            }
        ],
    ),
    BreakingRule(
        id="urllib3-strict-param-removed",
        package="urllib3",
        target_version_min="2.0.0",
        rule_type=BreakingChangeType.RENAMED_PARAM,
        symbol="strict",
        description="In urllib3 v2.0+, the `strict=True` parameter was removed from HTTPConnectionPool.",
        migration_guide_url="https://urllib3.readthedocs.io/en/latest/v2-migration-guide.html",
        old_pattern="HTTPConnectionPool(..., strict=True)",
        new_pattern="HTTPConnectionPool(...)",
        severity=Severity.HIGH,
        examples=[
            {
                "old": "pool = HTTPConnectionPool(host='example.com', strict=True)",
                "new": "pool = HTTPConnectionPool(host='example.com')",
            }
        ],
    ),
    BreakingRule(
        id="pandas-append-removed",
        package="pandas",
        target_version_min="2.0.0",
        rule_type=BreakingChangeType.REMOVED_METHOD,
        symbol="append",
        description="In Pandas 2.0+, `DataFrame.append` and `Series.append` have been removed. Use `pandas.concat` instead.",
        migration_guide_url="https://pandas.pydata.org/docs/whatsnew/v2.0.0.html",
        old_pattern="df = df.append(new_row, ignore_index=True)",
        new_pattern="df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)",
        severity=Severity.CRITICAL,
        examples=[
            {
                "old": "df = df.append(row)",
                "new": "df = pd.concat([df, pd.DataFrame([row])])",
            }
        ],
    ),
]

for r in GENERIC_RULES:
    catalog.register(r)
