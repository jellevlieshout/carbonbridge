"""
LangGraph step graph for the buyer wizard.

Design: one user message → one LangGraph node → END.
Step transitions are persisted in Couchbase by the runner and applied on
the NEXT user message.

Conversation quality rules enforced here:
1. Profile is always hydrated from the User doc at every turn.
2. Deterministic guards override LLM flags — state always wins.
3. Every node either advances the step OR emits a single follow-up question.
4. No node asks for data already in the state.
5. Buyer agent handoff is triggered inline when user accepts a listing.
6. Autobuy waitlist is a clear yes/no branch — no open-ended loops.
"""

from __future__ import annotations

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


# ── helpers ────────────────────────────────────────────────────────────


def _build_deps(state: WizardState) -> WizardDeps:
    return WizardDeps(
        buyer_id=state.get("buyer_id", ""),
        session_id=state.get("session_id", ""),
    )


def _history_text(state: WizardState) -> str:
    """Format last 12 turns of conversation history as a prompt string."""
    lines = []
    for msg in (state.get("conversation_history") or [])[-12:]:
        role = "Buyer" if msg.role == "user" else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


def _build_context_block(state: WizardState) -> str:
    """Build a rich context block injected into every step prompt."""
    parts: list[str] = [
        f"[Current wizard step: {state.get('current_step', 'profile_check')}]"
    ]

    # Company / profile data — hydrated from User doc
    company_name = state.get("company_name")
    if company_name:
        parts.append(f"Company name: {company_name}")

    sector = state.get("company_sector")
    employees = state.get("company_size_employees")
    country = state.get("company_country")

    # Also check nested buyer_profile dict for backwards compat
    bp = state.get("buyer_profile") or {}
    if not sector:
        sector = bp.get("sector") or bp.get("company_sector")
    if not employees:
        employees = bp.get("company_size_employees")
    if not country:
        country = bp.get("country")

    if sector:
        parts.append(f"Sector (KNOWN — do not ask again): {sector}")
    if employees:
        parts.append(f"Employees (KNOWN — do not ask again): {employees}")
    if country:
        parts.append(f"Country: {country}")

    motivation = bp.get("primary_offset_motivation")
    if motivation:
        parts.append(f"Offset motivation: {motivation}")

    if bp.get("annual_co2_tonnes_estimate"):
        parts.append(f"Saved annual footprint: {bp['annual_co2_tonnes_estimate']} tonnes")

    if bp.get("preferred_project_types"):
        parts.append(f"Saved project preferences: {', '.join(bp['preferred_project_types'])}")

    if bp.get("budget_per_tonne_max_eur"):
        parts.append(f"Saved budget ceiling: €{bp['budget_per_tonne_max_eur']}/tonne")

    # Session-level context
    fp = state.get("footprint_estimate")
    if fp:
        parts.append(
            f"Estimated footprint: {fp.get('estimated_tonnes_low')}–"
            f"{fp.get('estimated_tonnes_high')} tonnes/yr "
            f"(midpoint {fp.get('midpoint')})"
        )

    prefs = state.get("extracted_preferences")
    if prefs:
        if prefs.project_types:
            parts.append(f"Project type preferences: {', '.join(prefs.project_types)}")
        if prefs.regions:
            parts.append(f"Preferred regions: {', '.join(prefs.regions)}")
        if prefs.max_price_eur:
            parts.append(f"Budget ceiling: €{prefs.max_price_eur}/tonne")

    listings = state.get("recommended_listings") or []
    if listings:
        parts.append(f"{len(listings)} listings already shown to buyer")

    if state.get("search_broadened"):
        parts.append("[Search has already been broadened once — no more broadening]")

    draft_id = state.get("draft_order_id")
    if draft_id:
        parts.append(
            f"Draft order exists: {draft_id} (€{state.get('draft_order_total_eur')})"
        )

    return "\n".join(parts)


def _prompt_for_step(state: WizardState, extra_instructions: str = "") -> str:
    context = _build_context_block(state)
    history = _history_text(state)
    extra = f"\n\n[Step instructions: {extra_instructions}]" if extra_instructions else ""
    return (
        f"{context}{extra}\n\n"
        f"Conversation so far:\n{history}\n\n"
        f"Buyer just said: {state.get('latest_user_message', '')}"
    )


# ── deterministic transition guards ───────────────────────────────────
# These run AFTER the LLM call to ensure we advance when clearly ready.


def _profile_has_minimum(state: WizardState, output: ProfileIntentOutput) -> bool:
    """Return True when sector AND employees are known from any source."""
    sector = (
        output.sector
        or state.get("company_sector")
        or (state.get("buyer_profile") or {}).get("sector")
        or (state.get("buyer_profile") or {}).get("company_sector")
    )
    employees = (
        output.employees
        or state.get("company_size_employees")
        or (state.get("buyer_profile") or {}).get("company_size_employees")
    )
    return bool(sector and employees)


def _footprint_is_accepted(state: WizardState, output: FootprintOutput) -> bool:
    """Return True when there is an accepted or provided footprint."""
    if output.accepted_tonnes or output.buyer_provided_tonnes:
        return True
    fp = state.get("footprint_estimate")
    if fp and fp.get("midpoint"):
        msg = (state.get("latest_user_message") or "").lower()
        acceptance_words = {
            "ok", "okay", "yes", "yeah", "sure", "fine", "good", "correct",
            "right", "proceed", "go", "continue", "accept", "next", "sounds",
            "that", "perfect", "great", "makes", "seems", "looks", "alright",
            "all", "yep", "yup", "definitely", "absolutely", "please",
        }
        if acceptance_words & set(msg.split()):
            return True
        # Also handle "I'm not sure" → accept estimate and move on
        unsure_phrases = ["not sure", "don't know", "no idea", "unsure", "whatever"]
        if any(phrase in msg for phrase in unsure_phrases):
            return True
    return False


def _preferences_captured(state: WizardState, output: PreferenceOutput) -> bool:
    """Return True when at least one project type is known."""
    if output.project_types:
        return True
    prefs = state.get("extracted_preferences")
    if prefs and prefs.project_types:
        return True
    bp = state.get("buyer_profile") or {}
    return bool(bp.get("preferred_project_types"))


def _extract_profile_updates(
    state: WizardState, output: ProfileIntentOutput
) -> Dict[str, Any]:
    """Extract any new profile fields the LLM identified and merge with existing."""
    bp = dict(state.get("buyer_profile") or {})
    updated = False

    if output.sector and not (state.get("company_sector") or bp.get("sector")):
        bp["sector"] = output.sector
        updated = True
    elif output.sector:
        bp["sector"] = output.sector  # always keep freshest value
        updated = True

    if output.employees and not (state.get("company_size_employees") or bp.get("company_size_employees")):
        bp["company_size_employees"] = output.employees
        updated = True
    elif output.employees:
        bp["company_size_employees"] = output.employees
        updated = True

    if output.motivation:
        bp["primary_offset_motivation"] = output.motivation
        updated = True

    return bp if updated else (state.get("buyer_profile") or {})


# ── node implementations ───────────────────────────────────────────────


async def _hydrate_user_profile(state: WizardState) -> Dict[str, Any]:
    """
    Load and return user profile fields from the User doc.
    Returns a dict of state updates (partial state).
    Called at the start of profile_check to populate known data.
    """
    buyer_id = state.get("buyer_id", "")
    updates: Dict[str, Any] = {}

    try:
        from models.operations.users import user_get_data_for_frontend
        data = await user_get_data_for_frontend(buyer_id)
        user = data.get("user", {})

        if user.get("company_name"):
            updates["company_name"] = user["company_name"]
        if user.get("sector"):
            updates["company_sector"] = user["sector"]
        if user.get("country"):
            updates["company_country"] = user["country"]
        if user.get("company_size_employees"):
            updates["company_size_employees"] = user["company_size_employees"]

        bp = user.get("buyer_profile") or {}
        if bp:
            updates["buyer_profile"] = bp

    except Exception as exc:
        logger.warning("Could not hydrate user profile for buyer %s: %s", buyer_id, exc)

    return updates


async def node_profile_check(state: WizardState) -> Dict[str, Any]:
    """Step 0: Hydrate profile from User doc; auto-advance if complete."""
    # Always hydrate user profile first
    profile_updates = await _hydrate_user_profile(state)
    enriched: WizardState = {**state, **profile_updates}  # type: ignore[misc]

    # Check if we already have sector + employees from the hydrated profile
    sector = (
        enriched.get("company_sector")
        or (enriched.get("buyer_profile") or {}).get("sector")
    )
    employees = (
        enriched.get("company_size_employees")
        or (enriched.get("buyer_profile") or {}).get("company_size_employees")
    )

    if sector and employees:
        # Profile already complete — auto-advance without calling LLM for a confirmation
        instructions = (
            "The buyer's sector and employee count are ALREADY KNOWN (shown above in context). "
            "Set profile_complete=True and advance_to_footprint=True. "
            "Write a brief welcoming message acknowledging their company/sector "
            "and say you'll estimate their carbon footprint. "
            "Do NOT ask for sector or employees again."
        )
    else:
        missing = []
        if not sector:
            missing.append("sector")
        if not employees:
            missing.append("number of employees")
        instructions = (
            f"Ask the buyer for their {' and '.join(missing)}. "
            "One friendly question. Keep it short."
        )

    agent = create_wizard_agent("profile_check")
    result = await agent.run(_prompt_for_step(enriched, instructions), deps=_build_deps(state))
    output: ProfileIntentOutput = result.output

    bp = _extract_profile_updates(enriched, output)
    advance = output.advance_to_footprint or _profile_has_minimum(enriched, output)

    return {
        **profile_updates,
        "response_text": output.response_text,
        "next_step": "footprint_estimate" if advance else None,
        "buyer_profile": bp,
    }


async def node_onboarding(state: WizardState) -> Dict[str, Any]:
    """Step 0 (continued): Collect missing sector and/or employees."""
    sector = (
        state.get("company_sector")
        or (state.get("buyer_profile") or {}).get("sector")
    )
    employees = (
        state.get("company_size_employees")
        or (state.get("buyer_profile") or {}).get("company_size_employees")
    )

    if sector and employees:
        instructions = (
            "You already have sector and employees from context. "
            "Set profile_complete=True and advance_to_footprint=True immediately."
        )
    elif sector and not employees:
        instructions = (
            f"You know the sector ({sector}) but not the employee count. "
            "Ask only for the number of employees."
        )
    elif employees and not sector:
        instructions = (
            f"You know the employee count ({employees}) but not the sector. "
            "Ask only for the sector."
        )
    else:
        instructions = (
            "Ask for both sector and number of employees in one friendly question."
        )

    agent = create_wizard_agent("onboarding")
    result = await agent.run(_prompt_for_step(state, instructions), deps=_build_deps(state))
    output: ProfileIntentOutput = result.output

    bp = _extract_profile_updates(state, output)
    advance = _profile_has_minimum(state, output)

    return {
        "response_text": output.response_text,
        "next_step": "footprint_estimate" if advance else None,
        "buyer_profile": bp,
    }


async def node_footprint_estimate(state: WizardState) -> Dict[str, Any]:
    """Step 1: Estimate footprint via tool; auto-advance when buyer accepts."""
    fp_exists = bool((state.get("footprint_estimate") or {}).get("midpoint"))

    if fp_exists:
        instructions = (
            "The footprint estimate has already been calculated (shown in context). "
            "If the buyer shows any acceptance (yes, ok, sure, sounds right, proceed, etc.) "
            "OR says they're not sure — set advance_to_preferences=True. "
            "If buyer provides their own number, accept it and set advance_to_preferences=True. "
            "Do NOT recalculate unless buyer explicitly asks."
        )
    else:
        instructions = (
            "Call tool_estimate_footprint using the sector and employee count from context. "
            "Present the result clearly with the analogy. "
            "Ask if it sounds right."
        )

    agent = create_wizard_agent("footprint_estimate")
    result = await agent.run(_prompt_for_step(state, instructions), deps=_build_deps(state))
    output: FootprintOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    # Update footprint if tool was called and returned a value
    if output.buyer_provided_tonnes:
        updates["footprint_estimate"] = {
            "midpoint": output.buyer_provided_tonnes,
            "estimated_tonnes_low": output.buyer_provided_tonnes,
            "estimated_tonnes_high": output.buyer_provided_tonnes,
        }
    elif output.accepted_tonnes:
        updates["footprint_estimate"] = {
            "midpoint": output.accepted_tonnes,
            "estimated_tonnes_low": output.accepted_tonnes,
            "estimated_tonnes_high": output.accepted_tonnes,
        }

    # Deterministic guard — advance if any acceptance signal detected
    if output.advance_to_preferences or _footprint_is_accepted(state, output):
        updates["next_step"] = "preference_elicitation"
        # Carry forward existing estimate if we didn't get a new one
        if not updates.get("footprint_estimate") and state.get("footprint_estimate"):
            updates["footprint_estimate"] = state.get("footprint_estimate")

    return updates


async def node_preference_elicitation(state: WizardState) -> Dict[str, Any]:
    """Step 2: Capture project type preferences; auto-advance when at least one known."""
    # Check if we already have preferences from saved profile
    bp = state.get("buyer_profile") or {}
    saved_types = bp.get("preferred_project_types") or []
    existing_prefs = state.get("extracted_preferences")
    existing_types = (existing_prefs.project_types if existing_prefs else []) or saved_types

    if existing_types:
        instructions = (
            f"The buyer already has saved project preferences: {', '.join(existing_types)}. "
            "Set advance_to_search=True and include these in project_types. "
            "Do NOT ask again — acknowledge and say you are searching now."
        )
    else:
        instructions = (
            "Present 3–4 project type options with plain-language descriptions: "
            "afforestation (planting forests), renewable energy, clean cookstoves, "
            "methane capture, energy efficiency. "
            "Ask the buyer which appeals to them most. "
            "As soon as they mention any type, set advance_to_search=True."
        )

    agent = create_wizard_agent("preference_elicitation")
    result = await agent.run(_prompt_for_step(state, instructions), deps=_build_deps(state))
    output: PreferenceOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    # Merge project types from output + existing
    all_types = list(dict.fromkeys(output.project_types + existing_types))
    all_regions = list(dict.fromkeys(output.regions + (existing_prefs.regions if existing_prefs else [])))

    if all_types or output.project_types:
        from models.entities.couchbase.wizard_sessions import ExtractedPreferences
        updates["extracted_preferences"] = ExtractedPreferences(
            project_types=all_types or output.project_types,
            regions=all_regions,
            max_price_eur=output.max_price_eur or (existing_prefs.max_price_eur if existing_prefs else None),
            co_benefits=output.co_benefits,
        )

    if output.advance_to_search or _preferences_captured(state, output):
        updates["next_step"] = "listing_search"

    return updates


async def node_listing_search(state: WizardState) -> Dict[str, Any]:
    """Step 3a: Search listings; route to recommendation, handoff, or waitlist."""
    prefs = state.get("extracted_preferences")
    bp = state.get("buyer_profile") or {}
    max_price = (prefs.max_price_eur if prefs else None) or bp.get("budget_per_tonne_max_eur") or 50
    project_type_hint = prefs.project_types[0] if prefs and prefs.project_types else "any"

    instructions = (
        "Call tool_search_listings using the buyer's project type preferences and budget. "
        f"Use project_type={project_type_hint}. "
        f"Use max_price={max_price}. "
        "Present up to 3 matching listings with a 'why we picked this for you' blurb each. "
        "Include price per tonne and estimated total for their footprint. "
        "If NO listings found, ask: 'Would you like our agent to monitor the market and automatically "
        "purchase matching credits when they become available?' — clear yes/no question."
    )

    agent = create_wizard_agent("listing_search")
    result = await agent.run(_prompt_for_step(state, instructions), deps=_build_deps(state))
    output: RecommendationOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    if output.selected_listing_id or output.advance_to_order:
        # User already picked a listing → go directly to buyer agent handoff
        updates["next_step"] = "order_creation"
        if output.selected_listing_id:
            # Store selected listing in recommended_listings for order node
            updates["recommended_listings"] = [{"id": output.selected_listing_id}]
    elif not output.listings_found or output.buyer_wants_autobuy_waitlist:
        updates["next_step"] = "autobuy_waitlist"
        if output.buyer_wants_autobuy_waitlist:
            updates["autobuy_opt_in"] = True
    elif output.buyer_declined_autobuy:
        updates["waitlist_declined"] = True
        updates["conversation_complete"] = True
        updates["next_step"] = "autobuy_waitlist"
    # else: stay on recommendation step waiting for buyer selection

    return updates


async def node_recommendation(state: WizardState) -> Dict[str, Any]:
    """Step 3b: Handle buyer selection, broadening, or no-match."""
    search_broadened = state.get("search_broadened", False)

    if search_broadened:
        instructions = (
            "The search has already been broadened once. "
            "If no match or buyer declines: ask clearly: "
            "'Would you like our agent to automatically buy matching credits when available?' "
            "Set buyer_wants_autobuy_waitlist=True if they say yes. "
            "Set buyer_declined_autobuy=True if they say no."
        )
    else:
        instructions = (
            "Help the buyer select one of the shown listings. "
            "If they name or pick one — set selected_listing_id and advance_to_order=True. "
            "If they want different options — set buyer_wants_broader_search=True. "
            "If they decline all — set buyer_declined_all=True."
        )

    agent = create_wizard_agent("recommendation")
    result = await agent.run(_prompt_for_step(state, instructions), deps=_build_deps(state))
    output: RecommendationOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    if output.selected_listing_id or output.advance_to_order:
        updates["next_step"] = "order_creation"
        if output.selected_listing_id:
            updates["recommended_listings"] = [{"id": output.selected_listing_id}]
    elif output.buyer_wants_autobuy_waitlist:
        updates["next_step"] = "autobuy_waitlist"
        updates["autobuy_opt_in"] = True
    elif output.buyer_declined_autobuy:
        updates["waitlist_declined"] = True
        updates["conversation_complete"] = True
        updates["next_step"] = "autobuy_waitlist"
    elif output.buyer_wants_broader_search and not search_broadened:
        updates["search_broadened"] = True
        updates["next_step"] = "listing_search"
    elif output.buyer_declined_all or (output.buyer_wants_broader_search and search_broadened):
        updates["next_step"] = "autobuy_waitlist"

    return updates


async def node_order_creation(state: WizardState) -> Dict[str, Any]:
    """
    Step 4: Create draft order (wizard path) OR trigger buyer agent (handoff path).

    If the listing was found via wizard flow → create draft order and confirm.
    The actual buyer agent will be triggered by the runner after this node
    when order_confirmed=True.
    """
    instructions = (
        "Create the draft order using tool_create_order_draft. "
        "Use the first recommended listing ID from context and the buyer's target tonnage. "
        "Present a clear summary: project name, quantity, price per tonne, total EUR. "
        "End with: 'Shall I proceed to payment?' "
        "Set order_confirmed=True when the buyer explicitly agrees."
    )

    agent = create_wizard_agent("order_creation")
    result = await agent.run(_prompt_for_step(state, instructions), deps=_build_deps(state))
    output: OrderOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    if output.order_id:
        updates["draft_order_id"] = output.order_id

    if output.order_confirmed:
        # Signal to the runner to trigger buyer agent
        updates["next_step"] = "complete"
        updates["handoff_to_buyer_agent"] = True

    return updates


async def node_autobuy_waitlist(state: WizardState) -> Dict[str, Any]:
    """Terminal branch: offer autonomous-buy opt-in or close conversation."""
    already_opted_in = state.get("autobuy_opt_in", False)
    already_declined = state.get("waitlist_declined", False)
    already_complete = state.get("conversation_complete", False)

    if already_complete or already_declined:
        # Already resolved — just send a closing message
        if already_declined:
            instructions = (
                "The buyer has declined autonomous purchasing. "
                "Write a warm closing message: thank them, let them know their "
                "preferences are saved, and they can return to the wizard any time. "
                "Set buyer_declined_autobuy=True."
            )
        else:
            instructions = (
                "Write a brief closing message confirming the conversation is complete."
            )
    elif already_opted_in:
        # They already said yes — confirm and close
        instructions = (
            "The buyer already agreed to autonomous purchasing. "
            "Confirm their preferences are saved and the agent will monitor the market. "
            "Set buyer_wants_autobuy_waitlist=True."
        )
    else:
        instructions = (
            "No suitable listings were found matching the buyer's preferences. "
            "FIRST check the buyer's CURRENT MESSAGE and conversation history: "
            "- If they already said yes / sure / ok / absolutely / definitely to monitoring → "
            "  set buyer_wants_autobuy_waitlist=True and confirm: "
            "  'Done! I've activated the monitoring agent for you. It will automatically buy "
            "  matching credits when they appear. You can cancel from your dashboard.' "
            "- If they said no / not now / maybe later → set buyer_declined_autobuy=True. "
            "- Otherwise ask clearly: 'Would you like our autonomous agent to monitor the "
            "  market and automatically purchase matching carbon credits when they become "
            "  available? You can cancel any time from your dashboard.' "
        )

    agent = create_wizard_agent("autobuy_waitlist")
    result = await agent.run(_prompt_for_step(state, instructions), deps=_build_deps(state))
    output: RecommendationOutput = result.output

    opt_in = already_opted_in or output.buyer_wants_autobuy_waitlist
    declined = already_declined or output.buyer_declined_autobuy

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
        "autobuy_opt_in": opt_in,
        "waitlist_declined": declined,
    }

    if opt_in or declined:
        updates["conversation_complete"] = True

    if opt_in:
        prefs = state.get("extracted_preferences")
        fp = state.get("footprint_estimate")
        bp = state.get("buyer_profile") or {}
        updates["autobuy_criteria_snapshot"] = {
            "project_types": (prefs.project_types if prefs else [])
                             or bp.get("preferred_project_types", []),
            "regions": (prefs.regions if prefs else [])
                       or bp.get("preferred_regions", []),
            "max_price_eur": (prefs.max_price_eur if prefs else None)
                             or bp.get("budget_per_tonne_max_eur"),
            "target_tonnes": fp.get("midpoint") if fp else None,
            "motivation": bp.get("primary_offset_motivation"),
        }
        updates["waitlist_opted_in"] = True

    return updates


# ── graph assembly ─────────────────────────────────────────────────────


def _route_from_step(state: WizardState) -> str:
    step_to_node = {
        "profile_check":          "profile_check",
        "onboarding":             "onboarding",
        "footprint_estimate":     "footprint_estimate",
        "preference_elicitation": "preference_elicitation",
        "listing_search":         "listing_search",
        "recommendation":         "recommendation",
        "order_creation":         "order_creation",
        "autobuy_waitlist":       "autobuy_waitlist",
        "complete":               END,
    }
    step = state.get("current_step", "profile_check")
    return step_to_node.get(step, "profile_check")


def build_wizard_graph() -> Any:
    builder = StateGraph(WizardState)

    builder.add_node("profile_check",          node_profile_check)
    builder.add_node("onboarding",             node_onboarding)
    builder.add_node("footprint_estimate",     node_footprint_estimate)
    builder.add_node("preference_elicitation", node_preference_elicitation)
    builder.add_node("listing_search",         node_listing_search)
    builder.add_node("recommendation",         node_recommendation)
    builder.add_node("order_creation",         node_order_creation)
    builder.add_node("autobuy_waitlist",       node_autobuy_waitlist)

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
