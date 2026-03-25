"""AI Coach — the persistent motivator that won't leave you alone.

Uses the user's own API key (Anthropic or OpenAI). Zero server costs.
The coach is context-aware: it knows the threshold, current value, goal,
and full conversation history. It adapts intensity based on config.
"""

from __future__ import annotations

from datetime import datetime

from situational_ai.config import Settings
from situational_ai.health_data import get_history
from situational_ai.thresholds import (
    Threshold,
    ThresholdState,
    get_coach_history,
    save_coach_message,
)


def _build_system_prompt(threshold: Threshold, state: ThresholdState, settings: Settings) -> str:
    history = get_history(threshold.metric, limit=10)
    trend_lines = ""
    if history:
        trend_lines = "\n".join(
            f"  {r.recorded_at.strftime('%Y-%m-%d')}: {r.value} {r.unit}" for r in history
        )

    intensity_desc = {
        1: "gentle and encouraging",
        2: "supportive and kind",
        3: "friendly but firm",
        4: "direct and motivating",
        5: "assertive coach energy",
        6: "no-nonsense accountability partner",
        7: "relentless but caring",
        8: "drill sergeant with a heart",
        9: "absolutely will not let you slack",
        10: "MAXIMUM INTENSITY — you are an unstoppable force of accountability",
    }
    intensity = intensity_desc.get(settings.coach_intensity, intensity_desc[7])

    return f"""{threshold.coach_persona}

SITUATION:
- Metric: {threshold.metric.replace('_', ' ').title()}
- Threshold: {threshold.value} {threshold.unit} ({threshold.direction.value})
- Current value: {state.current_value} {threshold.unit}
- Goal: {threshold.goal_value} {threshold.unit}
- Triggered since: {state.triggered_at.strftime('%Y-%m-%d %H:%M') if state.triggered_at else 'just now'}
- Today: {datetime.now().strftime('%Y-%m-%d %H:%M')}

RECENT TREND:
{trend_lines if trend_lines else '  No history yet.'}

COACHING STYLE:
- Intensity level: {settings.coach_intensity}/10 — be {intensity}
- You do NOT stop until the goal is reached
- Give specific, actionable advice (meal ideas, workouts, habits)
- Keep messages concise but impactful (2-4 sentences for check-ins)
- Celebrate progress, no matter how small
- If the user is making excuses, call them out with love
- Reference their actual data and trends when possible
- You are NOT an AI assistant — you are their COACH. Talk like one."""


def get_coach_response(
    threshold: Threshold,
    state: ThresholdState,
    settings: Settings,
    user_message: str | None = None,
) -> str:
    """Generate a coach message using the user's own AI credits."""
    provider = settings.get_provider()
    system_prompt = _build_system_prompt(threshold, state, settings)

    # Build message history
    messages = get_coach_history(threshold.id, limit=20)

    if user_message:
        messages.append({"role": "user", "content": user_message})
        save_coach_message(threshold.id, "user", user_message)
    elif not messages:
        # First activation — coach initiates
        messages.append({
            "role": "user",
            "content": f"[SYSTEM: Threshold just triggered. Current {threshold.metric.replace('_', ' ')}: {state.current_value} {threshold.unit}. Goal: {threshold.goal_value} {threshold.unit}. Send your first coaching message.]",
        })
    else:
        # Periodic check-in — coach nags
        messages.append({
            "role": "user",
            "content": f"[SYSTEM: Periodic check-in. Current {threshold.metric.replace('_', ' ')}: {state.current_value} {threshold.unit}. Goal: {threshold.goal_value} {threshold.unit}. Keep coaching.]",
        })

    if provider == "anthropic":
        response = _call_anthropic(system_prompt, messages, settings)
    else:
        response = _call_openai(system_prompt, messages, settings)

    save_coach_message(threshold.id, "assistant", response)
    return response


def _call_anthropic(system_prompt: str, messages: list[dict], settings: Settings) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=512,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text


def _call_openai(system_prompt: str, messages: list[dict], settings: Settings) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    oai_messages = [{"role": "system", "content": system_prompt}] + messages
    response = client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=512,
        messages=oai_messages,
    )
    return response.choices[0].message.content


def get_goal_celebration(threshold: Threshold, state: ThresholdState, settings: Settings) -> str:
    """Generate a celebration message when the user hits their goal."""
    provider = settings.get_provider()
    system_prompt = f"""{threshold.coach_persona}

THE USER HIT THEIR GOAL! 🎉
- Metric: {threshold.metric.replace('_', ' ').title()}
- Was at: {threshold.value} {threshold.unit} (threshold)
- Now at: {state.current_value} {threshold.unit}
- Goal was: {threshold.goal_value} {threshold.unit}

Celebrate them! Be genuinely proud. Recap the journey. Encourage them to maintain it.
Keep it to 3-5 sentences."""

    messages = [{"role": "user", "content": "I did it!"}]

    if provider == "anthropic":
        return _call_anthropic(system_prompt, messages, settings)
    return _call_openai(system_prompt, messages, settings)
