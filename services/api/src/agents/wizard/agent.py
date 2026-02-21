"""
Pydantic AI agent factory for the buyer wizard.

Model is configurable via WIZARD_MODEL env var (default: gemini-2.5-flash-lite).
A new Agent instance is created per-step call because output_type varies by step.
"""

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

# ── system prompt ─────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a friendly carbon-credit purchasing assistant at CarbonBridge.
Your job is to guide small and medium-sized businesses through buying
verified carbon offsets in a simple, jargon-free conversation.

Rules:
- Keep replies to at most 3 sentences unless the buyer explicitly asks for more.
- Never use carbon-market jargon without explaining it in plain English.
- Never name competitors.
- Be warm and encouraging but not sycophantic.
- Always quote prices in EUR.
- When presenting listings, include a brief "why we picked this" blurb.
- Call tools when you need live data; wait for results before replying.
- DO NOT ask the buyer to confirm information you already have.
- If both sector and employees are already shown in the context, skip asking for them.
- When the buyer accepts an estimate with "ok", "yes", "yeah", "sure" or similar, treat it as confirmed and advance.
- Populate the structured output fields accurately based on what was said — do not leave transition flags empty when the intent is clear.
""".strip()

# ── step → output schema mapping ──────────────────────────────────────

_STEP_OUTPUT_MAP: dict[str, Type[BaseModel]] = {
    "profile_check": ProfileIntentOutput,
    "onboarding": ProfileIntentOutput,
    "footprint_estimate": FootprintOutput,
    "preference_elicitation": PreferenceOutput,
    "listing_search": RecommendationOutput,
    "recommendation": RecommendationOutput,
    "order_creation": OrderOutput,
    "autobuy_waitlist": RecommendationOutput,
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
