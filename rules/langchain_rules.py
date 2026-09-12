"""Breaking change rules for LangChain 0.1 -> 0.2/0.3 migration."""

from devrel_guard.core.models import BreakingRule, BreakingChangeType, Severity
from devrel_guard.rules.catalog import catalog


LANGCHAIN_RULES = [
    BreakingRule(
        id="langchain-chatopenai-import-moved",
        package="langchain",
        target_version_min="0.2.0",
        rule_type=BreakingChangeType.MOVED_IMPORT,
        symbol="ChatOpenAI",
        description="`ChatOpenAI` moved from `langchain.chat_models` to partner package `langchain_openai` (`from langchain_openai import ChatOpenAI`).",
        migration_guide_url="https://python.langchain.com/v0.2/docs/versions/v0_2/",
        old_pattern="from langchain.chat_models import ChatOpenAI",
        new_pattern="from langchain_openai import ChatOpenAI",
        severity=Severity.CRITICAL,
        examples=[
            {
                "old": "from langchain.chat_models import ChatOpenAI",
                "new": "from langchain_openai import ChatOpenAI",
            }
        ],
    ),
    BreakingRule(
        id="langchain-openaiembeddings-import-moved",
        package="langchain",
        target_version_min="0.2.0",
        rule_type=BreakingChangeType.MOVED_IMPORT,
        symbol="OpenAIEmbeddings",
        description="`OpenAIEmbeddings` moved from `langchain.embeddings` to partner package `langchain_openai` (`from langchain_openai import OpenAIEmbeddings`).",
        migration_guide_url="https://python.langchain.com/v0.2/docs/versions/v0_2/",
        old_pattern="from langchain.embeddings import OpenAIEmbeddings",
        new_pattern="from langchain_openai import OpenAIEmbeddings",
        severity=Severity.CRITICAL,
        examples=[
            {
                "old": "from langchain.embeddings import OpenAIEmbeddings",
                "new": "from langchain_openai import OpenAIEmbeddings",
            }
        ],
    ),
    BreakingRule(
        id="langchain-chain-run-deprecated",
        package="langchain",
        target_version_min="0.2.0",
        rule_type=BreakingChangeType.RENAMED_METHOD,
        symbol="run",
        description="In LangChain 0.2+, `.run(...)` is deprecated in favor of `.invoke(...)`.",
        migration_guide_url="https://python.langchain.com/v0.2/docs/versions/migrating_chains/llm_chain/",
        old_pattern="chain.run(input_text)",
        new_pattern="chain.invoke({'input': input_text})",
        severity=Severity.HIGH,
        examples=[
            {
                "old": "result = chain.run(query)",
                "new": "result = chain.invoke(query)",
            }
        ],
    ),
    BreakingRule(
        id="langchain-llmchain-migration",
        package="langchain",
        target_version_min="0.2.0",
        rule_type=BreakingChangeType.CLASS_DEPRECATION,
        symbol="LLMChain",
        description="`LLMChain` is deprecated in favor of LangChain Expression Language (LCEL): `prompt | llm | StrOutputParser()`.",
        migration_guide_url="https://python.langchain.com/v0.2/docs/versions/migrating_chains/llm_chain/",
        old_pattern="from langchain.chains import LLMChain\nchain = LLMChain(llm=llm, prompt=prompt)",
        new_pattern="chain = prompt | llm",
        severity=Severity.MEDIUM,
        examples=[
            {
                "old": "chain = LLMChain(llm=model, prompt=prompt)",
                "new": "chain = prompt | model",
            }
        ],
    ),
]

for r in LANGCHAIN_RULES:
    catalog.register(r)
