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

from datetime import datetime, timezone
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

    sustainability_goal = bp.get("sustainability_goal")
    if sustainability_goal:
        parts.append(f"Sustainability goal: {sustainability_goal}")

    emission_sources = bp.get("emission_sources") or []
    if emission_sources:
        parts.append(f"Main emission sources: {', '.join(emission_sources)}")

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
        listing_ids = [item.get("id") for item in listings if item.get("id")]
        if listing_ids:
            parts.append(f"Selected/recommended listing IDs: {', '.join(listing_ids)}")
        else:
            parts.append(f"{len(listings)} listings already shown to buyer")

    if state.get("search_broadened"):
        parts.append("[Search has already been broadened once — no more broadening]")

    draft_id = state.get("draft_order_id")
    if draft_id:
        parts.append(
            f"Draft order exists: {draft_id} (€{state.get('draft_order_total_eur')})"
        )

    # Time awareness
    try:
        now = datetime.now(timezone.utc)
        created_at = state.get("session_created_at")
        last_active = state.get("session_last_active_at")
        if created_at:
            # Ensure timezone-aware comparison
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            elapsed_total = int((now - created_at).total_seconds() / 60)
            parts.append(f"Session started {elapsed_total} minutes ago")
        if last_active:
            if last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=timezone.utc)
            idle_seconds = int((now - last_active).total_seconds())
            if idle_seconds > 30:
                idle_str = f"{idle_seconds // 60}m {idle_seconds % 60}s" if idle_seconds >= 60 else f"{idle_seconds}s"
                parts.append(f"Buyer last active {idle_str} ago")
    except Exception:
        pass  # time context is best-effort

    if state.get("is_nudge"):
        parts.append(
            "[PROACTIVE TURN — buyer has not replied yet. "
            "Continue the conversation naturally without waiting. "
            "You may offer encouragement, a helpful hint, or a gentle next question.]"
        )

    return "\n".join(parts)


def _prompt_for_step(state: WizardState, extra_instructions: str = "") -> str:
    context = _build_context_block(state)
    history = _history_text(state)
    extra = f"\n\n[Step instructions: {extra_instructions}]" if extra_instructions else ""

    latest = state.get("latest_user_message", "")
    if latest == "__nudge__":
        buyer_line = (
            "[No reply from buyer yet — send a friendly, helpful follow-up message "
            "to continue the conversation. Keep it natural and brief.]"
        )
    else:
        buyer_line = f"Buyer just said: {latest}"

    return (
        f"{context}{extra}\n\n"
        f"Conversation so far:\n{history}\n\n"
        f"{buyer_line}"
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
        msg = (state.get("latest_user_message") or "").lower().strip()
        # Only match clear, unambiguous acceptance — avoid false positives
        # from words like "that", "seems", "all" which appear in questions too
        strong_acceptance = {
            "ok", "okay", "yes", "yeah", "sure", "fine", "correct",
            "proceed", "continue", "accept", "next", "perfect",
            "yep", "yup", "definitely", "absolutely",
        }
        if strong_acceptance & set(msg.split()):
            return True
        # Phrase-level acceptance (more context = fewer false positives)
        acceptance_phrases = [
            "sounds right", "sounds good", "sounds about right",
            "looks right", "looks good", "that's fine", "that's correct",
            "let's go", "move on", "go ahead", "alright",
            "makes sense", "i agree", "good enough",
        ]
        if any(phrase in msg for phrase in acceptance_phrases):
            return True
        unsure_phrases = ["not sure", "don't know", "no idea", "unsure", "whatever"]
        if any(phrase in msg for phrase in unsure_phrases):
            return True
    return False


def _preferences_captured(state: WizardState, output: PreferenceOutput) -> bool:
    """
    Return True only when the LLM explicitly sets advance_to_search.
    We no longer auto-advance just because saved preferences exist — the user
    should be able to explore options, change their mind, and have a conversation
    about what project types they care about before we search.
    """
    return output.advance_to_search


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

    is_first_message = not (enriched.get("conversation_history") or []) or \
        all(m.role == "assistant" for m in (enriched.get("conversation_history") or []))

    if sector and employees:
        if is_first_message:
            instructions = (
                "This is the very first message — deliver a proper welcome to CarbonBridge! "
                "1. Say 'Welcome to CarbonBridge!' warmly. "
                "2. In 1-2 sentences explain what CarbonBridge does and what you'll do together "
                "   (e.g. estimate footprint → find matching projects → purchase verified offsets). "
                "3. Tell them you can see their company profile is already on file (sector + size). "
                "4. Ask ONE engaging follow-up: what drives their interest in carbon offsetting today? "
                "   Or mention their sector and ask about their biggest emission sources. "
                "Set profile_complete=True but set advance_to_footprint=FALSE — "
                "we want to get to know them before jumping to numbers. "
                "Keep it warm, friendly, 3-4 sentences max."
            )
        else:
            instructions = (
                "The buyer's sector and employee count are ALREADY KNOWN (shown above in context). "
                "Set profile_complete=True and advance_to_footprint=True. "
                "Acknowledge their response warmly. If they shared sustainability goals or "
                "emission sources, acknowledge those and say you'll use that context. "
                "Now move to footprint estimation. "
                "Do NOT ask for sector or employees again."
            )
    else:
        missing = []
        if not sector:
            missing.append("sector")
        if not employees:
            missing.append("number of employees")
        if is_first_message:
            instructions = (
                "This is the very FIRST message — deliver a proper welcome to CarbonBridge! "
                "Structure your message: "
                "1. Open with 'Welcome to CarbonBridge!' — enthusiastic and warm. "
                "2. In 1 sentence explain what you'll do together: estimate their carbon footprint, "
                "   match them to verified offset projects, and make a real climate impact. "
                "3. Tell them you just need a couple of details to get started. "
                f"4. Ask for their {' and '.join(missing)} in a friendly, conversational way — "
                "   NOT like a form. Make it feel like a real conversation. "
                "Keep it to 3-4 sentences. Be enthusiastic and approachable."
            )
        else:
            instructions = (
                f"Ask the buyer for their {' and '.join(missing)}. "
                "One friendly question. Keep it short."
            )

    agent = create_wizard_agent("profile_check")
    result = await agent.run(_prompt_for_step(enriched, instructions), deps=_build_deps(state))
    output: ProfileIntentOutput = result.output

    bp = _extract_profile_updates(enriched, output)
    # On first message, don't force-advance — let the welcome conversation breathe.
    # On subsequent messages, use the deterministic guard as a safety net.
    if is_first_message:
        advance = output.advance_to_footprint
    else:
        advance = output.advance_to_footprint or _profile_has_minimum(enriched, output)

    # Persist sustainability extras into buyer_profile
    if output.sustainability_goal and not bp.get("sustainability_goal"):
        bp["sustainability_goal"] = output.sustainability_goal
    if output.emission_sources:
        bp.setdefault("emission_sources", [])
        for src in output.emission_sources:
            if src not in bp["emission_sources"]:
                bp["emission_sources"].append(src)

    return {
        **profile_updates,
        "response_text": output.response_text,
        "next_step": "footprint_estimate" if advance else None,
        "buyer_profile": bp,
        "suggested_responses": output.suggested_responses,
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
        "suggested_responses": output.suggested_responses,
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

    updates["suggested_responses"] = output.suggested_responses
    return updates


async def node_preference_elicitation(state: WizardState) -> Dict[str, Any]:
    """Step 2: Capture project type preferences conversationally."""
    bp = state.get("buyer_profile") or {}
    saved_types = bp.get("preferred_project_types") or []
    existing_prefs = state.get("extracted_preferences")
    existing_types = (existing_prefs.project_types if existing_prefs else []) or saved_types

    latest_msg = (state.get("latest_user_message") or "").lower().strip()

    # Robust detection: does the user's message mention a specific project type?
    _type_signals = {
        "energy_efficiency": ["energy efficiency", "energy saving", "insulation", "efficient"],
        "renewable": ["renewable", "solar", "wind"],
        "afforestation": ["forest", "tree", "afforestation", "planting trees", "reforestation"],
        "cookstoves": ["cookstove", "clean cooking", "stove"],
        "methane_capture": ["methane", "landfill"],
        "agriculture": ["agriculture", "farming", "soil carbon", "regenerative"],
        "fuel_switching": ["fuel switching", "cleaner fuel"],
    }
    user_mentioned_types = [
        t for t, kws in _type_signals.items()
        if any(kw in latest_msg for kw in kws)
    ]

    # Also detect if user is confirming/accepting (to advance with existing)
    _confirm_words = {"yes", "ok", "okay", "sure", "yeah", "yep", "those", "same", "confirm",
                      "sounds good", "let's go", "search", "find", "proceed"}
    user_confirming = bool(_confirm_words & set(latest_msg.split())) or \
        any(p in latest_msg for p in ["sounds good", "let's go", "go ahead", "search for"])

    if user_mentioned_types:
        # User expressed a clear preference NOW — always honour it
        mentioned_str = ", ".join(user_mentioned_types)
        instructions = (
            f"The buyer just expressed interest in: {mentioned_str}. "
            "CRITICAL: Use THEIR stated preference. Do NOT substitute saved/previous preferences. "
            f"Set project_types to {user_mentioned_types}. "
            "Acknowledge their choice warmly (1-2 sentences — why this is a great choice for their context). "
            "Then say you'll search for matching projects and set advance_to_search=True."
        )
    elif existing_types and user_confirming:
        # User confirmed saved preferences
        instructions = (
            f"The buyer confirmed their previous preferences: {', '.join(existing_types)}. "
            "Set project_types to these and set advance_to_search=True. "
            "Say you'll search for matching projects now."
        )
    elif existing_types:
        instructions = (
            f"The buyer previously saved preferences for: {', '.join(existing_types)}. "
            "Mention these briefly and ask if they're still interested, or if they'd like "
            "to explore different types this time. "
            "Also present other options: afforestation, renewable energy, "
            "clean cookstoves, methane capture, energy efficiency. "
            "Relate options to their sector/emission sources from context. "
            "Do NOT auto-advance — wait for their response."
        )
    else:
        instructions = (
            "Present the project types with friendly descriptions: "
            "* Afforestation — planting and restoring forests to absorb CO2 "
            "* Renewable Energy — funding wind and solar that replace fossil fuels "
            "* Clean Cookstoves — reducing indoor air pollution in rural communities "
            "* Methane Capture — preventing methane from landfills and agriculture "
            "* Energy Efficiency — improving buildings and processes to waste less energy "
            "Relate options to their sector/emission sources from context if possible. "
            "Ask which appeals to them most. "
            "Do NOT set advance_to_search=True yet — wait for their response."
        )

    agent = create_wizard_agent("preference_elicitation")
    result = await agent.run(_prompt_for_step(state, instructions), deps=_build_deps(state))
    output: PreferenceOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    # If user explicitly mentioned types, those take absolute priority
    if user_mentioned_types:
        primary_types = user_mentioned_types
    elif output.project_types:
        primary_types = output.project_types
    else:
        primary_types = existing_types

    all_types = list(dict.fromkeys(primary_types))
    all_regions = list(dict.fromkeys(output.regions + (existing_prefs.regions if existing_prefs else [])))
    logger.info("Preference merge: user_detected=%s output=%s existing=%s → final=%s",
                user_mentioned_types, output.project_types, existing_types, all_types)

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

    updates["suggested_responses"] = output.suggested_responses
    return updates


async def node_listing_search(state: WizardState) -> Dict[str, Any]:
    """Step 3a: Search listings; route to recommendation, handoff, or waitlist."""
    prefs = state.get("extracted_preferences")
    bp = state.get("buyer_profile") or {}
    max_price = (prefs.max_price_eur if prefs else None) or bp.get("budget_per_tonne_max_eur") or 50

    all_pref_types = (prefs.project_types if prefs else []) or bp.get("preferred_project_types") or []
    project_types_str = ", ".join(all_pref_types) if all_pref_types else "any"

    fp = state.get("footprint_estimate") or {}
    target_tonnes = fp.get("midpoint")

    primary_type = all_pref_types[0] if all_pref_types else "any"

    instructions = (
        "Call tool_search_listings to find matching carbon credit projects. "
        f"The buyer's preferred project type is: {primary_type}. "
        f"IMPORTANT: Search for '{primary_type}' specifically — this is what the buyer asked for. "
        f"Use project_type='{primary_type}' and max_price={max_price}. "
        f"{'The buyer wants to offset about ' + str(target_tonnes) + ' tonnes.' if target_tonnes else ''} "
        "Present up to 3 matching listings. For each listing include: "
        "1. Project name and country "
        "2. Price per tonne in EUR "
        "3. Total estimated cost for their footprint "
        f"4. A 'why this fits you' sentence connecting the project to their interest in {primary_type} "
        "After presenting, ask which interests them or if they'd like different options. "
        "Do NOT auto-select a listing — wait for the buyer to choose. "
        "Do NOT set advance_to_order=True or selected_listing_id unless the buyer explicitly picks one. "
        "ALWAYS generate 3-4 suggested_responses — e.g. 'I like the first one', "
        "'Tell me more about option 2', 'Show me different projects', 'What's the best value?' "
        "If NO listings found, ask: 'Would you like our agent to monitor the market "
        "and automatically purchase matching credits when they become available?'"
    )

    agent = create_wizard_agent("listing_search")
    result = await agent.run(_prompt_for_step(state, instructions), deps=_build_deps(state))
    output: RecommendationOutput = result.output

    updates: Dict[str, Any] = {
        "response_text": output.response_text,
        "next_step": None,
    }

    if output.selected_listing_id and output.advance_to_order:
        updates["next_step"] = "order_creation"
        updates["recommended_listings"] = [{"id": output.selected_listing_id}]
    elif not output.listings_found:
        updates["next_step"] = "autobuy_waitlist"
    elif output.buyer_wants_autobuy_waitlist:
        updates["next_step"] = "autobuy_waitlist"
        updates["autobuy_opt_in"] = True
    elif output.buyer_declined_autobuy:
        updates["waitlist_declined"] = True
        updates["conversation_complete"] = True
        updates["next_step"] = "autobuy_waitlist"
    elif output.listings_found:
        # Listings were shown — move to recommendation step for the user to pick
        updates["next_step"] = "recommendation"

    updates["suggested_responses"] = output.suggested_responses
    return updates


async def node_recommendation(state: WizardState) -> Dict[str, Any]:
    """Step 3b: Handle buyer selection, broadening, or no-match."""
    search_broadened = state.get("search_broadened", False)
    latest_msg = (state.get("latest_user_message") or "").lower().strip()

    if search_broadened:
        instructions = (
            "The search has already been broadened once. "
            "Help the buyer decide: do they want one of the listings shown, or would they prefer "
            "to have our autonomous agent monitor and buy automatically? "
            "If buyer picks a listing — set selected_listing_id and advance_to_order=True. "
            "If buyer says yes to monitoring — set buyer_wants_autobuy_waitlist=True. "
            "If buyer says no thanks — set buyer_declined_autobuy=True. "
            "ALWAYS generate 3-4 suggested_responses."
        )
    else:
        instructions = (
            "The buyer is responding to the listings shown. Read their latest message carefully. "
            "If they name or reference a specific listing (by name, number, or description) — "
            "  set selected_listing_id to the EXACT ID from search results and advance_to_order=True. "
            "If they say 'first one', 'option 1', 'the solar one', etc. — match it to the correct listing ID. "
            "If they ask for more details — call tool_get_listing_detail and share details. "
            "If they want different options — set buyer_wants_broader_search=True. "
            "If they decline all — set buyer_declined_all=True. "
            "If they ask a follow-up question, answer it helpfully and invite them to pick. "
            "CRITICAL: ALWAYS generate 3-4 suggested_responses. Examples: "
            "'I'll go with option 1', 'Tell me more about the second one', "
            "'Show me different projects', 'What makes this one verified?'"
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

    updates["suggested_responses"] = output.suggested_responses
    return updates


async def node_order_creation(state: WizardState) -> Dict[str, Any]:
    """
    Step 4: Create draft order (wizard path) OR trigger buyer agent (handoff path).

    If the listing was found via wizard flow → create draft order and confirm.
    The actual buyer agent will be triggered by the runner after this node
    when order_confirmed=True.
    """
    has_draft = bool(state.get("draft_order_id"))
    if has_draft:
        instructions = (
            "A draft order already exists (shown in context). "
            "The buyer is responding to the order summary. "
            "If they confirm (yes, proceed, pay, go ahead, do it, let's do it) — "
            "set order_confirmed=True. "
            "If they want to change quantity or go back — explain what's possible. "
            "ALWAYS generate 3-4 suggested_responses like: "
            "'Yes, proceed to payment', 'Can I change the quantity?', "
            "'Go back to other options', 'How does payment work?'"
        )
    else:
        instructions = (
            "Create the draft order using tool_create_order_draft. "
            "Use the first recommended listing ID from context and the buyer's target tonnage "
            "(from footprint midpoint if they didn't specify a different quantity). "
            "Present a clear, friendly summary: "
            "• Project name and what it does (1 sentence) "
            "• Quantity in tonnes "
            "• Price per tonne in EUR "
            "• Total cost in EUR "
            "End with a warm: 'Ready to make your impact? Just confirm and we'll proceed to payment.' "
            "Do NOT set order_confirmed=True yet — wait for the buyer to explicitly agree. "
            "ALWAYS generate 3-4 suggested_responses like: "
            "'Yes, let's do it!', 'Can I adjust the quantity?', "
            "'Go back to other options', 'How does payment work?'"
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
        updates["next_step"] = "complete"
        updates["handoff_to_buyer_agent"] = True

    updates["suggested_responses"] = output.suggested_responses
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

    updates["suggested_responses"] = output.suggested_responses
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
