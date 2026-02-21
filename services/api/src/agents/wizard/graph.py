"""
LangGraph step graph for the buyer wizard.

Design: one user message → one LangGraph node → END.
Step transitions are persisted in Couchbase by the runner and applied on
the NEXT user message.

Key change from original: each node applies deterministic transition guards
AFTER the LLM call, overriding/correcting the model's next_step output when
the data state clearly dictates a transition. This prevents the "ok/yeah" loop
where the agent waits for explicit confirmation even though it already has all
needed fields.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

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
    )


def _history_text(state: WizardState) -> str:
    """Format last 10 turns of conversation history as a prompt string."""
    lines = []
    for msg in (state.get("conversation_history") or [])[-10:]:
        role = "Buyer" if msg.role == "user" else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


def _prompt_for_step(state: WizardState, extra_instructions: str = "") -> str:
    history = _history_text(state)
    context_parts = [
        f"[Current wizard step: {state.get('current_step', 'profile_check')}]"
    ]

    buyer_profile = state.get("buyer_profile")
    if buyer_profile:
        sector = buyer_profile.get("sector") or buyer_profile.get("company_sector")
        employees = buyer_profile.get("company_size_employees")
        if sector:
            context_parts.append(f"Buyer sector already known: {sector}")
        if employees:
            context_parts.append(f"Buyer employees already known: {employees}")
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

    search_broadened = state.get("search_broadened")
    if search_broadened:
        context_parts.append("[Search has already been broadened once]")

    draft_id = state.get("draft_order_id")
    if draft_id:
        context_parts.append(
            f"Draft order created: {draft_id} (€{state.get('draft_order_total_eur')})"
        )

    context_block = "\n".join(context_parts)

    extra = f"\n\n[Step instructions: {extra_instructions}]" if extra_instructions else ""

    return (
        f"{context_block}{extra}\n\n"
        f"Conversation so far:\n{history}\n\n"
        f"Buyer just said: {state.get('latest_user_message', '')}"
    )


# ── deterministic transition guards ───────────────────────────────────
# These run AFTER the LLM call to ensure we advance when clearly ready,
# regardless of whether the model emitted the right boolean flags.


def _profile_has_minimum(
    state: WizardState, output: ProfileIntentOutput
) -> bool:
    """Return True when sector AND employees are known from any source."""
    bp = state.get("buyer_profile") or {}
    sector = output.sector or bp.get("sector") or bp.get("company_sector")
    employees = output.employees or bp.get("company_size_employees")
    return bool(sector and employees)


def _footprint_is_accepted(
    state: WizardState, output: FootprintOutput
) -> bool:
    """Return True when there is an accepted footprint estimate."""
    if output.accepted_tonnes:
        return True
    fp = state.get("footprint_estimate")
    if fp and fp.get("midpoint"):
        msg = (state.get("latest_user_message") or "").lower()
        acceptance_words = {"ok", "okay", "yes", "yeah", "sure", "fine", "good", "correct",
                            "right", "proceed", "go", "continue", "accept", "next", "sounds"}
        return bool(acceptance_words & set(msg.split()))
    return False


def _preferences_captured(
    state: WizardState, output: PreferenceOutput
) -> bool:
    """Return True when at least one project type is known."""
    if output.project_types:
        return True
    prefs = state.get("extracted_preferences")
    return bool(prefs and prefs.project_types)


# ── node implementations ───────────────────────────────────────────────


async def node_profile_check(state: WizardState) -> Dict[str, Any]:
    """Step 0: Check buyer profile; if complete auto-advance to footprint."""
    deps = _build_deps(state)
    buyer_profile = state.get("buyer_profile")

    if not buyer_profile:
        try:
            from models.operations.users import user_get_buyer_profile
            profile = await user_get_buyer_profile(deps.buyer_id)
            if profile:
                buyer_profile = profile.model_dump()
        except Exception as exc:
            logger.warning("Could not fetch buyer profile: %s", exc)

    enriched: WizardState = {**state, "buyer_profile": buyer_profile}  # type: ignore[misc]

    instructions = (
        "You are in the profile collection step. "
        "If the buyer's sector and employee count are already known (shown in context), "
        "set profile_complete=true and advance_to_footprint=true and proceed. "
        "Do NOT ask for confirmation again if both fields are present."
    )
    agent = create_wizard_agent("profile_check")
    result = await agent.run(_prompt_for_step(enriched, instructions), deps=deps)
    output: ProfileIntentOutput = result.output

    # ── deterministic guard ──────────────────────────────────────────
    advance = output.advance_to_footprint or _profile_has_minimum(enriched, output)
    next_step: Optional[str] = "footprint_estimate" if advance else None

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": next_step,
        "buyer_profile": buyer_profile,
    }
    if output.sector or output.employees:
        bp = dict(buyer_profile or {})
        if output.sector:
            bp["sector"] = output.sector
        if output.employees:
            bp["company_size_employees"] = output.employees
        if output.motivation:
            bp["primary_offset_motivation"] = output.motivation
        updates["buyer_profile"] = bp

    return updates


async def node_onboarding(state: WizardState) -> Dict[str, Any]:
    """Step 0 (continued): Collect sector, employees, motivation."""
    deps = _build_deps(state)

    instructions = (
        "Collect the buyer's sector and employee count. "
        "Once BOTH are known, set profile_complete=true and advance_to_footprint=true "
        "immediately — do not wait for an extra confirmation message. "
        "If already known, advance now."
    )
    agent = create_wizard_agent("onboarding")
    result = await agent.run(_prompt_for_step(state, instructions), deps=deps)
    output: ProfileIntentOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    # ── deterministic guard ──────────────────────────────────────────
    if _profile_has_minimum(state, output):
        updates["next_step"] = "footprint_estimate"

    if output.sector or output.employees:
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
    """Step 1: Estimate footprint; auto-advance when buyer accepts."""
    deps = _build_deps(state)

    instructions = (
        "Present the footprint estimate (call the tool if not yet done). "
        "If the buyer shows any acceptance (ok, yes, sure, good, sounds right, etc.), "
        "set advance_to_preferences=true and accepted_tonnes to the midpoint. "
        "Do NOT ask for re-confirmation if the buyer already agreed in a previous message."
    )
    agent = create_wizard_agent("footprint_estimate")
    result = await agent.run(_prompt_for_step(state, instructions), deps=deps)
    output: FootprintOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    # persist footprint from tool result even if model forgot accepted_tonnes
    fp = state.get("footprint_estimate")
    if output.accepted_tonnes:
        updates["footprint_estimate"] = {
            "midpoint": output.accepted_tonnes,
            "estimated_tonnes_low": output.accepted_tonnes,
            "estimated_tonnes_high": output.accepted_tonnes,
        }

    # ── deterministic guard ──────────────────────────────────────────
    if output.advance_to_preferences or _footprint_is_accepted(state, output):
        updates["next_step"] = "preference_elicitation"
        if not output.accepted_tonnes and fp:
            updates["footprint_estimate"] = fp  # carry forward existing estimate

    return updates


async def node_preference_elicitation(state: WizardState) -> Dict[str, Any]:
    """Step 2: Capture project type preferences; auto-advance when at least one known."""
    deps = _build_deps(state)

    instructions = (
        "Ask about project type preferences (forestry, renewable energy, cookstoves, etc.). "
        "As soon as the buyer names at least one type, set advance_to_search=true. "
        "Do NOT keep asking for more confirmation; one type is enough to proceed."
    )
    agent = create_wizard_agent("preference_elicitation")
    result = await agent.run(_prompt_for_step(state, instructions), deps=deps)
    output: PreferenceOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    if output.project_types or output.regions or output.max_price_eur:
        from models.entities.couchbase.wizard_sessions import ExtractedPreferences
        updates["extracted_preferences"] = ExtractedPreferences(
            project_types=output.project_types,
            regions=output.regions,
            max_price_eur=output.max_price_eur,
            co_benefits=output.co_benefits,
        )

    # ── deterministic guard ──────────────────────────────────────────
    if output.advance_to_search or _preferences_captured(state, output):
        updates["next_step"] = "listing_search"

    return updates


async def node_listing_search(state: WizardState) -> Dict[str, Any]:
    """Step 3a: Search listings; deterministically handle found/not-found."""
    deps = _build_deps(state)

    instructions = (
        "Call tool_search_listings with the buyer's preferences. "
        "If listings are found, present up to 3 with a 'why we picked this' blurb for each. "
        "If NO listings are found, set listings_found=false and ask if they want "
        "to broaden the search or join a waitlist for future purchases. "
        "Do NOT invent listings."
    )
    agent = create_wizard_agent("listing_search")
    result = await agent.run(_prompt_for_step(state, instructions), deps=deps)
    output: RecommendationOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    if output.advance_to_order or output.selected_listing_id:
        updates["next_step"] = "order_creation"
    elif not output.listings_found or output.buyer_wants_autobuy_waitlist:
        updates["next_step"] = "autobuy_waitlist"
        updates["autobuy_opt_in"] = output.buyer_wants_autobuy_waitlist
    # else: stay on recommendation step for follow-up

    return updates


async def node_recommendation(state: WizardState) -> Dict[str, Any]:
    """Step 3b: Handle buyer selection, broadening, or no-match fallback."""
    deps = _build_deps(state)
    search_broadened = state.get("search_broadened", False)

    if search_broadened:
        instructions = (
            "The search has already been broadened once. "
            "If still no match or buyer declines, offer the autonomous-buy waitlist: "
            "'We can notify you when matching credits become available and optionally buy on your behalf.' "
            "Set buyer_wants_autobuy_waitlist=true if they agree. "
            "Set buyer_declined_all=true if they explicitly decline everything."
        )
    else:
        instructions = (
            "Help the buyer select a listing or adjust the search. "
            "If they want something different, set buyer_wants_broader_search=true. "
            "If they have selected a listing, set selected_listing_id and advance_to_order=true."
        )

    agent = create_wizard_agent("recommendation")
    result = await agent.run(_prompt_for_step(state, instructions), deps=deps)
    output: RecommendationOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    if output.advance_to_order or output.selected_listing_id:
        updates["next_step"] = "order_creation"
    elif output.buyer_wants_autobuy_waitlist:
        updates["next_step"] = "autobuy_waitlist"
        updates["autobuy_opt_in"] = True
    elif output.buyer_wants_broader_search and not search_broadened:
        updates["search_broadened"] = True
        updates["next_step"] = "listing_search"
    elif output.buyer_declined_all or (output.buyer_wants_broader_search and search_broadened):
        # already broadened once, nothing found — offer waitlist
        updates["next_step"] = "autobuy_waitlist"

    return updates


async def node_order_creation(state: WizardState) -> Dict[str, Any]:
    """Step 4: Create draft order and present summary for buyer confirmation."""
    deps = _build_deps(state)

    instructions = (
        "Create the draft order using tool_create_order_draft. "
        "Present a clear summary: project name, quantity, price per tonne, total EUR. "
        "Ask the buyer to confirm. Set order_confirmed=true when they agree."
    )
    agent = create_wizard_agent("order_creation")
    result = await agent.run(_prompt_for_step(state, instructions), deps=deps)
    output: OrderOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": "complete" if output.order_confirmed else None,
    }
    return updates


async def node_autobuy_waitlist(state: WizardState) -> Dict[str, Any]:
    """Terminal/handoff: Offer autonomous-buy opt-in; persist intent."""
    deps = _build_deps(state)
    already_opted_in = state.get("autobuy_opt_in", False)

    instructions = (
        "No suitable listings were found (or buyer declined all options). "
        "Explain that your team monitors the market and an autonomous agent can "
        "purchase matching credits on their behalf when they become available. "
        "Ask for their consent to be added to the waitlist. "
        "Set buyer_wants_autobuy_waitlist=true if they agree."
    )
    agent = create_wizard_agent("recommendation")  # reuse RecommendationOutput schema
    result = await agent.run(_prompt_for_step(state, instructions), deps=deps)
    output: RecommendationOutput = result.output

    opt_in = already_opted_in or output.buyer_wants_autobuy_waitlist

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
        "autobuy_opt_in": opt_in,
    }

    if opt_in:
        # Persist criteria snapshot for the future autonomous agent
        prefs = state.get("extracted_preferences")
        fp = state.get("footprint_estimate")
        updates["autobuy_criteria_snapshot"] = {
            "project_types": prefs.project_types if prefs else [],
            "regions": prefs.regions if prefs else [],
            "max_price_eur": prefs.max_price_eur if prefs else None,
            "target_tonnes": fp.get("midpoint") if fp else None,
        }

    return updates


# ── graph assembly ─────────────────────────────────────────────────────


def _route_from_step(state: WizardState) -> str:
    step_to_node = {
        "profile_check": "profile_check",
        "onboarding": "onboarding",
        "footprint_estimate": "footprint_estimate",
        "preference_elicitation": "preference_elicitation",
        "listing_search": "listing_search",
        "recommendation": "recommendation",
        "order_creation": "order_creation",
        "autobuy_waitlist": "autobuy_waitlist",
        "complete": END,
    }
    step = state.get("current_step", "profile_check")
    return step_to_node.get(step, "profile_check")


def build_wizard_graph() -> Any:
    builder = StateGraph(WizardState)

    builder.add_node("profile_check", node_profile_check)
    builder.add_node("onboarding", node_onboarding)
    builder.add_node("footprint_estimate", node_footprint_estimate)
    builder.add_node("preference_elicitation", node_preference_elicitation)
    builder.add_node("listing_search", node_listing_search)
    builder.add_node("recommendation", node_recommendation)
    builder.add_node("order_creation", node_order_creation)
    builder.add_node("autobuy_waitlist", node_autobuy_waitlist)

    builder.add_conditional_edges(START, _route_from_step)

    for node_name in [
        "profile_check",
        "onboarding",
        "footprint_estimate",
        "preference_elicitation",
        "listing_search",
        "recommendation",
        "order_creation",
        "autobuy_waitlist",
    ]:
        builder.add_edge(node_name, END)

    return builder.compile()


_wizard_graph: Any = None


def get_wizard_graph() -> Any:
    global _wizard_graph
    if _wizard_graph is None:
        _wizard_graph = build_wizard_graph()
    return _wizard_graph
