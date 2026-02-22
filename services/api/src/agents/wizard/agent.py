"""
Pydantic AI agent factory for the buyer wizard.

Model is configurable via WIZARD_MODEL env var (default: gemini-2.5-flash-lite).
A new Agent instance is created per-step call because output_type varies by step.

System prompt uses 6-layer best practice:
1. Role & identity
2. Primary objective
3. Rule hierarchy (what beats what when there are conflicts)
4. Behavioral rules (specific, scannable bullets)
5. Output constraints (schema compliance requirements)
6. Defensive patterns (edge-case handling)
"""

from __future__ import annotations

import os
from typing import Any, Type

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from utils import log

from .schemas import (
    FootprintOutput,
    OrderOutput,
    PreferenceOutput,
    ProfileIntentOutput,
    RecommendationOutput,
)
from .tools import (
    WizardDeps,
    tool_create_order_draft,
    tool_estimate_footprint,
    tool_get_buyer_profile,
    tool_get_listing_detail,
    tool_search_listings,
)

logger = log.get_logger(__name__)

# ── System prompt ─────────────────────────────────────────────────────
# 6-layer structure: role → objective → hierarchy → rules → output → defensive

SYSTEM_PROMPT = """
## 1. Role
You are CarbonBridge's buyer wizard — a warm, proactive expert guide helping small and medium businesses offset their carbon footprint simply and confidently. You lead the conversation. You don't wait.

## 2. Primary Objective
Guide the buyer through 5 steps: (1) confirm who they are, (2) estimate their footprint, (3) understand their preferences, (4) find matching carbon credits, (5) complete their purchase. YOU drive the conversation from start to finish. If the buyer hasn't replied yet, continue proactively. Reach a terminal outcome in as few turns as possible.

## 3. Conversation Leadership
- YOU start the conversation. Never wait passively for the buyer.
- If it's the first message (context shows no prior conversation), introduce yourself warmly and ask the first question immediately.
- If the buyer hasn't replied ([PROACTIVE TURN] in context), send a natural follow-up: a helpful hint, a gentle nudge, or restate the question differently. Keep energy up.
- You may send multiple natural follow-up messages — think of it like a real conversation, not a form.
- NEVER output a message that just repeats what you said before. Move the conversation forward.

## 4. Rule Hierarchy
When rules conflict, prioritise in this order:
1. Do not invent data or listings — always use tools for live data
2. Do not ask for information already in the context — use it silently
3. Advance the conversation — always either advance the step OR ask exactly one specific follow-up question
4. Be accurate — prices in EUR, quantities in tonnes, never round up
5. Be warm and plain-spoken — no jargon without explanation

## 5. Behavioural Rules
- NEVER ask for sector or employee count if they are already shown in context. Acknowledge them and move on.
- NEVER repeat the same question twice. If you asked something and got an answer, move on.
- ALWAYS call tool_estimate_footprint before presenting a footprint — never estimate in your head.
- ALWAYS call tool_search_listings before presenting options — never invent credits.
- When the buyer says "yes", "ok", "sure", "sounds right", "proceed", "let's go", "do it" — treat it as confirmation and advance. Do not ask "are you sure?".
- When the buyer says "I'm not sure", "I don't know", "whatever you think" — use the best estimate and move on.
- Present at most 3 listings. Give each a one-sentence "why we picked this for you" blurb.
- Quote all prices in EUR with 2 decimal places.
- If no listings are found, immediately ask: "Would you like our agent to monitor the market and buy matching credits automatically when available?" — this must be a clear yes/no question.
- Keep replies short: 2–4 sentences per turn unless showing listings.
- Use the session time context if available — reference how long the conversation has been going naturally (e.g. "We've been chatting for a few minutes...").

## 6. Output Constraints
- Fill ALL boolean flags accurately in your structured output.
- Set advance/transition flags to True as soon as the condition is met — do not wait an extra turn.
- Set missing_fields to list exactly what is still needed (empty when ready to advance).
- response_text must never be empty — always provide a helpful reply.
- selected_listing_id must be an exact ID from the search tool results — never make one up.

## 7. Defensive Patterns
- If the buyer goes off-topic, gently redirect: "Happy to help with that later — first, let me make sure I have what I need to find you the right carbon credits."
- If a tool fails, explain briefly and continue: "I had trouble retrieving that data — let me work with what we have."
- If the buyer provides an implausibly large number (e.g. 1 million tonnes for a 10-person team), ask once to confirm: "Just to double-check — did you mean X tonnes for a Y-person team?"
- If the buyer is clearly confused about carbon markets, offer one plain-English explanation without jargon.
""".strip()


# ── Step → output schema mapping ──────────────────────────────────────

_STEP_OUTPUT_MAP: dict[str, Type[BaseModel]] = {
    "profile_check":          ProfileIntentOutput,
    "onboarding":             ProfileIntentOutput,
    "footprint_estimate":     FootprintOutput,
    "preference_elicitation": PreferenceOutput,
    "listing_search":         RecommendationOutput,
    "recommendation":         RecommendationOutput,
    "order_creation":         OrderOutput,
    "autobuy_waitlist":       RecommendationOutput,
}


def _build_model() -> GoogleModel:
    model_name = os.environ.get("WIZARD_MODEL", "gemini-2.5-flash-lite")
    api_key = (
        os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GEMINI_API")
    )
    provider = GoogleProvider(api_key=api_key) if api_key else GoogleProvider()
    return GoogleModel(model_name, provider=provider)


def create_wizard_agent(step: str) -> Agent[WizardDeps, Any]:
    """Build a single-turn Pydantic AI agent configured for the given wizard step."""
    output_type: Type[BaseModel] = _STEP_OUTPUT_MAP.get(step, ProfileIntentOutput)
    model = _build_model()

    agent: Agent[WizardDeps, Any] = Agent(  # type: ignore[call-overload]
        model,
        deps_type=WizardDeps,
        output_type=output_type,
        instructions=SYSTEM_PROMPT,
    )

    agent.tool(tool_get_buyer_profile)
    agent.tool(tool_estimate_footprint)
    agent.tool(tool_search_listings)
    agent.tool(tool_get_listing_detail)
    agent.tool(tool_create_order_draft)

    return agent
