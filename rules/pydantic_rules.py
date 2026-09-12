"""Breaking change rules for Pydantic v1 -> v2 migration."""

from devrel_guard.core.models import BreakingRule, BreakingChangeType, Severity
from devrel_guard.rules.catalog import catalog


PYDANTIC_RULES = [
    BreakingRule(
        id="pydantic-validator-to-field-validator",
        package="pydantic",
        target_version_min="2.0.0",
        rule_type=BreakingChangeType.RENAMED_METHOD,
        symbol="validator",
        description="In Pydantic v2, `@validator` is deprecated in favor of `@field_validator`. Field validators must be classmethods.",
        migration_guide_url="https://docs.pydantic.dev/2.0/migration/#changes-to-validators",
        old_pattern="@validator('field')",
        new_pattern="@field_validator('field')\n@classmethod",
        severity=Severity.CRITICAL,
        examples=[
            {
                "old": "@validator('name')\ndef check_name(cls, v):\n    return v.title()",
                "new": "@field_validator('name')\n@classmethod\ndef check_name(cls, v):\n    return v.title()",
            }
        ],
    ),
    BreakingRule(
        id="pydantic-dict-to-model-dump",
        package="pydantic",
        target_version_min="2.0.0",
        rule_type=BreakingChangeType.RENAMED_METHOD,
        symbol="dict",
        description="In Pydantic v2, `.dict()` is deprecated in favor of `.model_dump()`.",
        migration_guide_url="https://docs.pydantic.dev/2.0/migration/#changes-to-pydanticbasemodel",
        old_pattern="instance.dict()",
        new_pattern="instance.model_dump()",
        severity=Severity.HIGH,
        examples=[
            {
                "old": "user_data = user.dict()",
                "new": "user_data = user.model_dump()",
            }
        ],
    ),
    BreakingRule(
        id="pydantic-parse-raw-to-model-validate-json",
        package="pydantic",
        target_version_min="2.0.0",
        rule_type=BreakingChangeType.RENAMED_METHOD,
        symbol="parse_raw",
        description="In Pydantic v2, `.parse_raw(...)` has been removed and replaced by `.model_validate_json(...)`.",
        migration_guide_url="https://docs.pydantic.dev/2.0/migration/#changes-to-pydanticbasemodel",
        old_pattern="Model.parse_raw(json_str)",
        new_pattern="Model.model_validate_json(json_str)",
        severity=Severity.CRITICAL,
        examples=[
            {
                "old": "user = User.parse_raw(payload)",
                "new": "user = User.model_validate_json(payload)",
            }
        ],
    ),
    BreakingRule(
        id="pydantic-config-class-to-model-config",
        package="pydantic",
        target_version_min="2.0.0",
        rule_type=BreakingChangeType.CLASS_DEPRECATION,
        symbol="Config",
        description="In Pydantic v2, inner `class Config:` is deprecated in favor of `model_config = ConfigDict(...)`.",
        migration_guide_url="https://docs.pydantic.dev/2.0/migration/#changes-to-config",
        old_pattern="class Config:\n    frozen = True",
        new_pattern="model_config = ConfigDict(frozen=True)",
        severity=Severity.MEDIUM,
        examples=[
            {
                "old": "class Config:\n    extra = 'forbid'",
                "new": "model_config = ConfigDict(extra='forbid')",
            }
        ],
    ),
    BreakingRule(
        id="pydantic-basesettings-moved",
        package="pydantic",
        target_version_min="2.0.0",
        rule_type=BreakingChangeType.MOVED_IMPORT,
        symbol="BaseSettings",
        description="`BaseSettings` has been moved to the standalone package `pydantic-settings` (`from pydantic_settings import BaseSettings`).",
        migration_guide_url="https://docs.pydantic.dev/2.0/migration/#basesettings-has-moved-to-pydantic-settings",
        old_pattern="from pydantic import BaseSettings",
        new_pattern="from pydantic_settings import BaseSettings",
        severity=Severity.CRITICAL,
        examples=[
            {
                "old": "from pydantic import BaseModel, BaseSettings",
                "new": "from pydantic import BaseModel\nfrom pydantic_settings import BaseSettings",
            }
        ],
    ),
    BreakingRule(
        id="pydantic-json-to-model-dump-json",
        package="pydantic",
        target_version_min="2.0.0",
        rule_type=BreakingChangeType.RENAMED_METHOD,
        symbol="json",
        description="In Pydantic v2, `.json()` is deprecated in favor of `.model_dump_json()`.",
        migration_guide_url="https://docs.pydantic.dev/2.0/migration/#changes-to-pydanticbasemodel",
        old_pattern="instance.json()",
        new_pattern="instance.model_dump_json()",
        severity=Severity.HIGH,
        examples=[
            {
                "old": "json_str = user.json()",
                "new": "json_str = user.model_dump_json()",
            }
        ],
    ),
]

for r in PYDANTIC_RULES:
    catalog.register(r)
