"""Breaking change rules for OpenAI Python SDK v0.28 -> v1.0+ migration."""

from devrel_guard.core.models import BreakingRule, BreakingChangeType, Severity
from devrel_guard.rules.catalog import catalog


OPENAI_RULES = [
    BreakingRule(
        id="openai-chatcompletion-create-deprecated",
        package="openai",
        target_version_min="1.0.0",
        rule_type=BreakingChangeType.REMOVED_METHOD,
        symbol="ChatCompletion.create",
        description="In OpenAI SDK v1.0+, module-level `openai.ChatCompletion.create` was removed in favor of `client.chat.completions.create`.",
        migration_guide_url="https://github.com/openai/openai-python/discussions/742",
        old_pattern="openai.ChatCompletion.create(model=..., messages=...)",
        new_pattern="client.chat.completions.create(model=..., messages=...)",
        severity=Severity.CRITICAL,
        examples=[
            {
                "old": "response = openai.ChatCompletion.create(model='gpt-4', messages=[{'role': 'user', 'content': 'Hello'}])",
                "new": "response = client.chat.completions.create(model='gpt-4', messages=[{'role': 'user', 'content': 'Hello'}])",
            }
        ],
    ),
    BreakingRule(
        id="openai-embedding-create-deprecated",
        package="openai",
        target_version_min="1.0.0",
        rule_type=BreakingChangeType.REMOVED_METHOD,
        symbol="Embedding.create",
        description="In OpenAI SDK v1.0+, module-level `openai.Embedding.create` was removed in favor of `client.embeddings.create`.",
        migration_guide_url="https://github.com/openai/openai-python/discussions/742",
        old_pattern="openai.Embedding.create(input=..., model=...)",
        new_pattern="client.embeddings.create(input=..., model=...)",
        severity=Severity.CRITICAL,
        examples=[
            {
                "old": "res = openai.Embedding.create(input='sample', model='text-embedding-ada-002')",
                "new": "res = client.embeddings.create(input='sample', model='text-embedding-ada-002')",
            }
        ],
    ),
    BreakingRule(
        id="openai-api-key-global-assignment",
        package="openai",
        target_version_min="1.0.0",
        rule_type=BreakingChangeType.BEHAVIOR_CHANGE,
        symbol="api_key",
        description="Global assignment `openai.api_key = ...` is deprecated in v1.0+; instantiate `client = OpenAI(api_key=...)` instead.",
        migration_guide_url="https://github.com/openai/openai-python/discussions/742",
        old_pattern="openai.api_key = os.getenv('OPENAI_API_KEY')",
        new_pattern="client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))",
        severity=Severity.HIGH,
        examples=[
            {
                "old": "openai.api_key = 'sk-...'",
                "new": "client = OpenAI(api_key='sk-...')",
            }
        ],
    ),
    BreakingRule(
        id="openai-invalid-request-error-renamed",
        package="openai",
        target_version_min="1.0.0",
        rule_type=BreakingChangeType.CLASS_DEPRECATION,
        symbol="InvalidRequestError",
        description="`openai.error.InvalidRequestError` was renamed to `openai.BadRequestError` in v1.0+.",
        migration_guide_url="https://github.com/openai/openai-python/discussions/742",
        old_pattern="except openai.error.InvalidRequestError:",
        new_pattern="except openai.BadRequestError:",
        severity=Severity.MEDIUM,
        examples=[
            {
                "old": "except openai.error.InvalidRequestError as e:",
                "new": "except openai.BadRequestError as e:",
            }
        ],
    ),
]

for r in OPENAI_RULES:
    catalog.register(r)
