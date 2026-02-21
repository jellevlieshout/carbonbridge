"""
LangGraph step graph for the buyer wizard.

Design: one user message → one LangGraph node → END.
Step transitions are persisted in Couchbase by the runner and applied on
the NEXT user message. This keeps each SSE streaming call to a single
LLM invocation and avoids chaining multiple agent calls per turn.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from utils import log
from .agent import create_wizard_agent
from .schemas import (
    FootprintOutput,
    OrderOutput,
    PreferenceOutput,
    ProfileIntentOutput,
    RecommendationOutput,
)
from .state import WizardState
from .tools import WizardDeps

logger = log.get_logger(__name__)

# ── helpers ───────────────────────────────────────────────────────────


def _build_deps(state: WizardState) -> WizardDeps:
    return WizardDeps(
        buyer_id=state.get("buyer_id", ""),
        session_id=state.get("session_id", ""),
        internal_base_url=os.environ.get("INTERNAL_API_BASE_URL", "http://localhost:3030/api"),
        api_key=os.environ.get("INTERNAL_AGENT_API_KEY", ""),
    )


def _history_text(state: WizardState) -> str:
    """Format last 10 turns of conversation history as a prompt string."""
    lines = []
    for msg in (state.get("conversation_history") or [])[-10:]:
        role = "Buyer" if msg.role == "user" else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


def _prompt_for_step(state: WizardState) -> str:
    history = _history_text(state)
    context_parts = [f"[Current wizard step: {state.get('current_step', 'profile_check')}]"]

    buyer_profile = state.get("buyer_profile")
    if buyer_profile:
        if buyer_profile.get("annual_co2_tonnes_estimate"):
            context_parts.append(
                f"Buyer's saved annual footprint: {buyer_profile['annual_co2_tonnes_estimate']} tonnes"
            )
        if buyer_profile.get("preferred_project_types"):
            context_parts.append(
                f"Saved project preferences: {', '.join(buyer_profile['preferred_project_types'])}"
            )

    footprint = state.get("footprint_estimate")
    if footprint:
        context_parts.append(
            f"Estimated footprint: {footprint.get('estimated_tonnes_low')}–"
            f"{footprint.get('estimated_tonnes_high')} tonnes/yr "
            f"(midpoint {footprint.get('midpoint')})"
        )

    prefs = state.get("extracted_preferences")
    if prefs:
        if prefs.project_types:
            context_parts.append(
                f"Project type preferences: {', '.join(prefs.project_types)}"
            )
        if prefs.max_price_eur:
            context_parts.append(f"Budget ceiling: €{prefs.max_price_eur}/tonne")

    listings = state.get("recommended_listings") or []
    if listings:
        context_parts.append(f"{len(listings)} listings already shown to buyer")

    draft_id = state.get("draft_order_id")
    if draft_id:
        context_parts.append(
            f"Draft order created: {draft_id} (€{state.get('draft_order_total_eur')})"
        )

    context_block = "\n".join(context_parts)
    return (
        f"{context_block}\n\n"
        f"Conversation so far:\n{history}\n\n"
        f"Buyer just said: {state.get('latest_user_message', '')}"
    )


# ── node implementations ───────────────────────────────────────────────
# Each node runs ONE LLM call and returns a partial-state dict.
# The graph always routes to END after the node (one node per turn).


async def node_profile_check(state: WizardState) -> Dict[str, Any]:
    """Step 0: Check buyer profile; collect sector/headcount if missing."""
    deps = _build_deps(state)
    buyer_profile = state.get("buyer_profile")

    if not buyer_profile:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{deps.internal_base_url}/internal/buyers/{deps.buyer_id}/profile",
                    headers={"X-Agent-API-Key": deps.api_key},
                )
                if r.status_code == 200:
                    buyer_profile = r.json()
        except Exception as exc:
            logger.warning("Could not fetch buyer profile: %s", exc)

    # Merge fetched profile into state before building prompt
    enriched: WizardState = {**state, "buyer_profile": buyer_profile}  # type: ignore[misc]
    agent = create_wizard_agent("profile_check")
    prompt = _prompt_for_step(enriched)
    result = await agent.run(prompt, deps=deps)
    output: ProfileIntentOutput = result.output

    return {
        "response_text": output.response_text,
        "next_step": output.next_step,
        "buyer_profile": buyer_profile,
    }


async def node_onboarding(state: WizardState) -> Dict[str, Any]:
    """Step 0 (continued): Collect sector, employees, motivation."""
    deps = _build_deps(state)
    agent = create_wizard_agent("onboarding")
    result = await agent.run(_prompt_for_step(state), deps=deps)
    output: ProfileIntentOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": output.next_step,
    }

    if output.profile_complete and (output.sector or output.employees):
        bp = dict(state.get("buyer_profile") or {})
        if output.sector:
            bp["sector"] = output.sector
        if output.employees:
            bp["company_size_employees"] = output.employees
        if output.motivation:
            bp["primary_offset_motivation"] = output.motivation
        updates["buyer_profile"] = bp

    return updates


async def node_footprint_estimate(state: WizardState) -> Dict[str, Any]:
    """Step 1: Estimate carbon footprint; present in plain language with analogy."""
    deps = _build_deps(state)
    agent = create_wizard_agent("footprint_estimate")
    result = await agent.run(_prompt_for_step(state), deps=deps)
    output: FootprintOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": output.next_step,
    }
    if output.accepted_tonnes:
        updates["footprint_estimate"] = {
            "midpoint": output.accepted_tonnes,
            "estimated_tonnes_low": output.accepted_tonnes,
            "estimated_tonnes_high": output.accepted_tonnes,
        }
    return updates


async def node_preference_elicitation(state: WizardState) -> Dict[str, Any]:
    """Step 2: Ask what kind of offset project the buyer prefers."""
    deps = _build_deps(state)
    agent = create_wizard_agent("preference_elicitation")
    result = await agent.run(_prompt_for_step(state), deps=deps)
    output: PreferenceOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": output.next_step,
    }

    if output.project_types or output.regions or output.max_price_eur:
        from models.entities.couchbase.wizard_sessions import ExtractedPreferences

        updates["extracted_preferences"] = ExtractedPreferences(
            project_types=output.project_types,
            regions=output.regions,
            max_price_eur=output.max_price_eur,
            co_benefits=output.co_benefits,
        )
    return updates


async def node_listing_search(state: WizardState) -> Dict[str, Any]:
    """Step 3a: Search listings and present curated recommendations."""
    deps = _build_deps(state)
    agent = create_wizard_agent("listing_search")
    result = await agent.run(_prompt_for_step(state), deps=deps)
    output: RecommendationOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": "order_creation" if output.selected_listing_id else output.next_step,
    }
    return updates


async def node_recommendation(state: WizardState) -> Dict[str, Any]:
    """Step 3b: Handle buyer selection or re-query with loosened filters."""
    deps = _build_deps(state)
    agent = create_wizard_agent("recommendation")
    result = await agent.run(_prompt_for_step(state), deps=deps)
    output: RecommendationOutput = result.output

    return {
        "response_text": output.response_text,
        "next_step": "order_creation" if output.selected_listing_id else output.next_step,
    }


async def node_order_creation(state: WizardState) -> Dict[str, Any]:
    """Step 4: Create draft order and present summary for confirmation."""
    deps = _build_deps(state)
    agent = create_wizard_agent("order_creation")
    result = await agent.run(_prompt_for_step(state), deps=deps)
    output: OrderOutput = result.output

    return {
        "response_text": output.response_text,
        "next_step": output.next_step,
    }


# ── graph assembly ─────────────────────────────────────────────────────


def _route_from_step(state: WizardState) -> str:
    """Entry router: start at the node matching current_step."""
    step_to_node = {
        "profile_check": "profile_check",
        "onboarding": "onboarding",
        "footprint_estimate": "footprint_estimate",
        "preference_elicitation": "preference_elicitation",
        "listing_search": "listing_search",
        "recommendation": "recommendation",
        "order_creation": "order_creation",
    }
    return step_to_node.get(state.get("current_step", "profile_check"), "profile_check")


def build_wizard_graph() -> Any:
    """
    Compile the wizard state graph.

    Topology: START → (one node based on current_step) → END.
    One LLM call per user turn; step persistence is handled by the runner.
    """
    builder = StateGraph(WizardState)

    builder.add_node("profile_check", node_profile_check)
    builder.add_node("onboarding", node_onboarding)
    builder.add_node("footprint_estimate", node_footprint_estimate)
    builder.add_node("preference_elicitation", node_preference_elicitation)
    builder.add_node("listing_search", node_listing_search)
    builder.add_node("recommendation", node_recommendation)
    builder.add_node("order_creation", node_order_creation)

    builder.add_conditional_edges(START, _route_from_step)

    for node_name in [
        "profile_check",
        "onboarding",
        "footprint_estimate",
        "preference_elicitation",
        "listing_search",
        "recommendation",
        "order_creation",
    ]:
        builder.add_edge(node_name, END)

    return builder.compile()


_wizard_graph: Any = None


def get_wizard_graph() -> Any:
    global _wizard_graph
    if _wizard_graph is None:
        _wizard_graph = build_wizard_graph()
    return _wizard_graph
