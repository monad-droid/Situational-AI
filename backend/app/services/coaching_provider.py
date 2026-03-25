"""Coaching provider abstraction — tiered model routing.

GPT-5 Mini: nudges (push notifications) — cheap, good at conversational text
Claude Haiku 4.5: deep coaching chat — higher quality reasoning, less sycophantic

Each provider implements its own caching mechanics. Do NOT assume they work the same.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.config import settings
from backend.app.services.system_prompt import COACHING_SYSTEM_PROMPT, build_user_context


class CoachingProvider(ABC):
    @abstractmethod
    async def generate_nudge(self, system_prompt: str, user_context: str) -> str:
        """Generate a short coaching nudge for push notification (2-3 sentences)."""
        ...

    @abstractmethod
    async def generate_chat_response(self, system_prompt: str, user_context: str, conversation: list[dict]) -> str:
        """Generate a chat response for an active coaching session."""
        ...


class OpenAIProvider(CoachingProvider):
    """GPT-5 Mini for nudges.

    Caching: Automatic prefix caching. The system prompt must be the exact same
    character-for-character prefix across requests. User-specific context is injected
    as a separate user message AFTER the system prompt, never inside it.
    Cache eviction is controlled by OpenAI — at low volume, cache may not persist.
    """

    async def generate_nudge(self, system_prompt: str, user_context: str) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.nudge_model,
            max_tokens=150,  # Short nudges only
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{user_context}\n\nSend a coaching nudge. 2-3 sentences max. Be direct."},
            ],
        )
        return response.choices[0].message.content

    async def generate_chat_response(self, system_prompt: str, user_context: str, conversation: list[dict]) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_context},
        ] + conversation
        response = await client.chat.completions.create(
            model=settings.nudge_model,
            max_tokens=500,
            messages=messages,
        )
        return response.choices[0].message.content


class AnthropicProvider(CoachingProvider):
    """Claude Haiku 4.5 for deep coaching chat.

    Caching: Supports explicit cache breakpoints via cache_control on content blocks.
    The static system prompt gets a cache breakpoint so it persists across calls.
    User context is appended without caching since it changes per call.
    """

    async def generate_nudge(self, system_prompt: str, user_context: str) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.chat_model,
            max_tokens=150,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[
                {"role": "user", "content": f"{user_context}\n\nSend a coaching nudge. 2-3 sentences max. Be direct."},
            ],
        )
        return response.content[0].text

    async def generate_chat_response(self, system_prompt: str, user_context: str, conversation: list[dict]) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        messages = [
            {"role": "user", "content": user_context},
        ] + conversation
        response = await client.messages.create(
            model=settings.chat_model,
            max_tokens=500,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=messages,
        )
        return response.content[0].text


# Singleton instances — model routing is decided at call site, not here
_openai_provider = None
_anthropic_provider = None


def get_nudge_provider() -> CoachingProvider:
    """GPT-5 Mini for nudges."""
    global _openai_provider
    if _openai_provider is None:
        _openai_provider = OpenAIProvider()
    return _openai_provider


def get_chat_provider() -> CoachingProvider:
    """Claude Haiku 4.5 for deep coaching."""
    global _anthropic_provider
    if _anthropic_provider is None:
        _anthropic_provider = AnthropicProvider()
    return _anthropic_provider
