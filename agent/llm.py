"""LLM Integration for DevRel Guard supporting Gemini and OpenAI."""

from __future__ import annotations
import os
import re
from typing import Optional


class AgentLLMClient:
    """Provides LLM-assisted reasoning for novel breaking changes and changelog mining."""

    def __init__(self) -> None:
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self._gemini_client = None

        if self.gemini_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.gemini_key)
            except Exception:
                self._gemini_client = None

    @property
    def is_available(self) -> bool:
        return self._gemini_client is not None or bool(self.openai_key)

    def synthesize_refactor(
        self,
        snippet: str,
        rule_description: str,
        old_pattern: str,
        new_pattern: str,
        package_name: str,
    ) -> Optional[str]:
        """Synthesize an AST-compliant refactor using LLM when rule patterns require reasoning."""
        if not self._gemini_client:
            return None

        prompt = f"""You are DevRel Guard, an expert code refactoring agent.
A dependency '{package_name}' was bumped, causing a breaking change.

Issue: {rule_description}
Old pattern: {old_pattern}
New pattern: {new_pattern}

Original code snippet to update:
```python
{snippet}
```

Respond with ONLY the exact replacement python code for this snippet.
Do not include markdown code block backticks (no ```).
Preserve exact indentation and surrounding structure.
"""
        try:
            response = self._gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            if response and response.text:
                cleaned = response.text.strip()
                # Remove code fences if LLM included them
                cleaned = re.sub(r"^```(?:python)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)
                return cleaned
        except Exception:
            return None

        return None


# Global singleton LLM client
llm_client = AgentLLMClient()
