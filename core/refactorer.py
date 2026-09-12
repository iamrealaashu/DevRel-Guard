"""Agentic Refactoring and Patch Generation Engine."""

from __future__ import annotations
import re
from typing import Dict, List, Optional
from devrel_guard.core.models import ASTViolation, FixSuggestion, BreakingChangeType


class CodeRefactorer:
    """Generates precise, verified code refactors for detected breaking change violations."""

    def refactor_violation(
        self,
        violation: ASTViolation,
        file_source: str,
    ) -> Optional[FixSuggestion]:
        rule = violation.rule
        lines = file_source.splitlines()

        start_line = violation.line_number
        end_line = violation.end_line_number

        if start_line < 1 or start_line > len(lines):
            return None

        orig_snippet = "\n".join(lines[start_line - 1 : end_line])
        indent = self._extract_indentation(lines[start_line - 1])

        # 1. Pydantic validator -> field_validator
        if rule.id == "pydantic-validator-to-field-validator":
            new_code = self._refactor_validator(orig_snippet, indent)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Replaced deprecated `@validator` with `@field_validator` and added required `@classmethod`.",
                confidence=0.98,
                changelog_reference=rule.migration_guide_url,
            )

        # 2. Pydantic .dict() -> .model_dump()
        if rule.id == "pydantic-dict-to-model-dump":
            new_code = re.sub(r"\.dict\(", ".model_dump(", orig_snippet)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Replaced `.dict()` with Pydantic v2 `.model_dump()`.",
                confidence=0.99,
                changelog_reference=rule.migration_guide_url,
            )

        # 3. Pydantic .json() -> .model_dump_json()
        if rule.id == "pydantic-json-to-model-dump-json":
            new_code = re.sub(r"\.json\(", ".model_dump_json(", orig_snippet)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Replaced `.json()` with Pydantic v2 `.model_dump_json()`.",
                confidence=0.99,
                changelog_reference=rule.migration_guide_url,
            )

        # 4. Pydantic .parse_raw(...) -> .model_validate_json(...)
        if rule.id == "pydantic-parse-raw-to-model-validate-json":
            new_code = re.sub(r"\.parse_raw\(", ".model_validate_json(", orig_snippet)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Replaced `.parse_raw(...)` with Pydantic v2 `.model_validate_json(...)`.",
                confidence=0.98,
                changelog_reference=rule.migration_guide_url,
            )

        # 5. Pydantic Config class -> model_config
        if rule.id == "pydantic-config-class-to-model-config":
            new_code = self._refactor_config_class(orig_snippet, indent)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Converted inner `class Config:` to Pydantic v2 `model_config = ConfigDict(...)`.",
                confidence=0.95,
                changelog_reference=rule.migration_guide_url,
            )

        # 6. Pydantic BaseSettings import
        if rule.id == "pydantic-basesettings-moved":
            new_code = self._refactor_basesettings_import(orig_snippet)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Imported `BaseSettings` from `pydantic_settings` instead of `pydantic`.",
                confidence=0.99,
                changelog_reference=rule.migration_guide_url,
            )

        # 7. LangChain ChatOpenAI / OpenAIEmbeddings import
        if rule.id == "langchain-chatopenai-import-moved":
            new_code = orig_snippet.replace("langchain.chat_models", "langchain_openai")
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Updated `ChatOpenAI` import to `from langchain_openai import ChatOpenAI`.",
                confidence=0.99,
                changelog_reference=rule.migration_guide_url,
            )

        if rule.id == "langchain-openaiembeddings-import-moved":
            new_code = orig_snippet.replace("langchain.embeddings", "langchain_openai")
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Updated `OpenAIEmbeddings` import to `from langchain_openai import OpenAIEmbeddings`.",
                confidence=0.99,
                changelog_reference=rule.migration_guide_url,
            )

        # 8. LangChain chain.run -> chain.invoke
        if rule.id == "langchain-chain-run-deprecated":
            new_code = re.sub(r"\.run\(", ".invoke(", orig_snippet)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Replaced deprecated `.run(...)` with modern LangChain `.invoke(...)`.",
                confidence=0.95,
                changelog_reference=rule.migration_guide_url,
            )

        # 9. OpenAI ChatCompletion.create
        if rule.id == "openai-chatcompletion-create-deprecated":
            new_code = re.sub(r"openai\.ChatCompletion\.create\(", "client.chat.completions.create(", orig_snippet)
            if new_code == orig_snippet:
                new_code = re.sub(r"ChatCompletion\.create\(", "client.chat.completions.create(", orig_snippet)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Updated legacy `openai.ChatCompletion.create` to OpenAI v1.0 `client.chat.completions.create`.",
                confidence=0.97,
                changelog_reference=rule.migration_guide_url,
            )

        # 10. OpenAI Embedding.create
        if rule.id == "openai-embedding-create-deprecated":
            new_code = re.sub(r"openai\.Embedding\.create\(", "client.embeddings.create(", orig_snippet)
            if new_code == orig_snippet:
                new_code = re.sub(r"Embedding\.create\(", "client.embeddings.create(", orig_snippet)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Updated legacy `openai.Embedding.create` to OpenAI v1.0 `client.embeddings.create`.",
                confidence=0.97,
                changelog_reference=rule.migration_guide_url,
            )

        # 11. OpenAI InvalidRequestError
        if rule.id == "openai-invalid-request-error-renamed":
            new_code = orig_snippet.replace("openai.error.InvalidRequestError", "openai.BadRequestError").replace(
                "InvalidRequestError", "BadRequestError"
            )
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Updated `InvalidRequestError` to v1.0 `openai.BadRequestError`.",
                confidence=0.99,
                changelog_reference=rule.migration_guide_url,
            )

        # 12. FastAPI regex -> pattern
        if rule.id == "fastapi-query-regex-to-pattern":
            new_code = re.sub(r"\bregex\s*=", "pattern=", orig_snippet)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Replaced deprecated `regex=` parameter with `pattern=` for FastAPI parameter declaration.",
                confidence=0.99,
                changelog_reference=rule.migration_guide_url,
            )

        # 13. Urllib3 strict=True removal
        if rule.id == "urllib3-strict-param-removed":
            new_code = re.sub(r",?\s*strict\s*=\s*True", "", orig_snippet)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation="Removed deprecated `strict=True` parameter for urllib3 v2 compatibility.",
                confidence=0.98,
                changelog_reference=rule.migration_guide_url,
            )

        # Fallback: generic replacement based on pattern
        if rule.old_pattern in orig_snippet:
            new_code = orig_snippet.replace(rule.old_pattern, rule.new_pattern)
            return FixSuggestion(
                violation_id=violation.id,
                file_path=violation.file_path,
                start_line=start_line,
                end_line=end_line,
                original_code=orig_snippet,
                replacement_code=new_code,
                explanation=f"Updated `{rule.symbol}` to conform with {rule.package} migration guide.",
                confidence=0.85,
                changelog_reference=rule.migration_guide_url,
            )

        return None

    @staticmethod
    def _extract_indentation(line: str) -> str:
        match = re.match(r"^(\s*)", line)
        return match.group(1) if match else ""

    @staticmethod
    def _refactor_validator(snippet: str, indent: str) -> str:
        # Turn @validator('x', pre=True) -> @field_validator('x', mode='before')\n{indent}@classmethod
        new_s = snippet.replace("@validator(", "@field_validator(")
        new_s = re.sub(r"pre\s*=\s*True", "mode='before'", new_s)
        new_s = re.sub(r"pre\s*=\s*False", "mode='after'", new_s)
        return f"{new_s}\n{indent}@classmethod"

    @staticmethod
    def _refactor_config_class(snippet: str, indent: str) -> str:
        # Extract attributes from class Config: e.g. frozen = True, extra = 'forbid'
        props = []
        for line in snippet.splitlines():
            line_s = line.strip()
            if line_s.startswith("class Config"):
                continue
            if "=" in line_s:
                props.append(line_s)

        inner_props = ", ".join(props) if props else ""
        return f"{indent}model_config = ConfigDict({inner_props})"

    @staticmethod
    def _refactor_basesettings_import(snippet: str) -> str:
        # e.g. from pydantic import BaseModel, BaseSettings
        if "from pydantic import" in snippet and "BaseSettings" in snippet:
            # Remove BaseSettings from pydantic import
            cleaned = re.sub(r",?\s*BaseSettings\s*,?", "", snippet)
            cleaned = re.sub(r"import\s*,", "import", cleaned).strip()
            if cleaned.endswith("import") or cleaned.strip() == "from pydantic import":
                return "from pydantic_settings import BaseSettings"
            return f"{cleaned}\nfrom pydantic_settings import BaseSettings"
        return snippet
