from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMResponse:
    answer: str


class LLMAdapter:
    def generate(self, *, prompt: str) -> LLMResponse:
        raise NotImplementedError


class StubPrivateLLMAdapter(LLMAdapter):
    def generate(self, *, prompt: str) -> LLMResponse:
        if "No indexed context is currently available" in prompt:
            return LLMResponse(
                answer="No indexed context is available yet. Upload processing may still be in progress."
            )
        return LLMResponse(
            answer="Grounded answer generated from authorized indexed context."
        )

