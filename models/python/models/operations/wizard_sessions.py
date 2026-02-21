from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from models.entities.couchbase.wizard_sessions import (
    WizardSession, WizardSessionData, ConversationMessage, ExtractedPreferences,
    WizardStep,
)


async def wizard_session_create(buyer_id: str) -> WizardSession:
    data = WizardSessionData(
        buyer_id=buyer_id,
        last_active_at=datetime.now(timezone.utc),
    )
    return await WizardSession.create(data, user_id=buyer_id)


async def wizard_session_get(session_id: str) -> Optional[WizardSession]:
    return await WizardSession.get(session_id)


async def wizard_session_get_active_for_buyer(buyer_id: str) -> Optional[WizardSession]:
    keyspace = WizardSession.get_keyspace()
    now = datetime.now(timezone.utc).isoformat()
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE buyer_id = $buyer_id "
        f"AND (expires_at IS NULL OR expires_at > $now) "
        f"ORDER BY last_active_at DESC LIMIT 1"
    )
    rows = await keyspace.query(query, buyer_id=buyer_id, now=now)
    for row in rows:
        data_dict = row.get("wizard_sessions")
        if data_dict:
            return WizardSession(id=row["id"], data=data_dict)
    return None


async def wizard_session_add_message(
    session_id: str, role: str, content: str,
) -> Optional[WizardSession]:
    session = await WizardSession.get(session_id)
    if not session:
        return None
    msg = ConversationMessage(
        role=role,
        content=content,
        timestamp=datetime.now(timezone.utc),
    )
    session.data.conversation_history.append(msg)
    session.data.last_active_at = datetime.now(timezone.utc)
    return await WizardSession.update(session)


async def wizard_session_update_step(
    session_id: str, step: WizardStep,
) -> Optional[WizardSession]:
    session = await WizardSession.get(session_id)
    if not session:
        return None
    session.data.current_step = step
    session.data.last_active_at = datetime.now(timezone.utc)
    return await WizardSession.update(session)


async def wizard_session_update_preferences(
    session_id: str, preferences: ExtractedPreferences,
) -> Optional[WizardSession]:
    session = await WizardSession.get(session_id)
    if not session:
        return None
    session.data.extracted_preferences = preferences
    session.data.last_active_at = datetime.now(timezone.utc)
    return await WizardSession.update(session)


async def wizard_session_save_context(
    session_id: str,
    footprint_context: Optional[Dict[str, Any]] = None,
    recommended_listing_ids: Optional[List[str]] = None,
    draft_order_id: Optional[str] = None,
    draft_order_total_eur: Optional[float] = None,
    search_broadened: Optional[bool] = None,
    autobuy_opt_in: Optional[bool] = None,
    autobuy_criteria_snapshot: Optional[Dict[str, Any]] = None,
    handoff_to_buyer_agent: Optional[bool] = None,
    buyer_agent_run_id: Optional[str] = None,
    buyer_agent_outcome: Optional[str] = None,
    waitlist_opted_in: Optional[bool] = None,
    waitlist_declined: Optional[bool] = None,
    conversation_complete: Optional[bool] = None,
) -> Optional[WizardSession]:
    """
    Persist graph-level context so the session can be fully resumed.
    Only non-None arguments are updated.
    """
    session = await WizardSession.get(session_id)
    if not session:
        return None
    if footprint_context is not None:
        session.data.footprint_context = footprint_context
    if recommended_listing_ids is not None:
        session.data.recommended_listing_ids = recommended_listing_ids
    if draft_order_id is not None:
        session.data.draft_order_id = draft_order_id
    if draft_order_total_eur is not None:
        session.data.draft_order_total_eur = draft_order_total_eur
    if search_broadened is not None:
        session.data.search_broadened = search_broadened
    if autobuy_opt_in is not None:
        session.data.autobuy_opt_in = autobuy_opt_in
    if autobuy_criteria_snapshot is not None:
        session.data.autobuy_criteria_snapshot = autobuy_criteria_snapshot
    if handoff_to_buyer_agent is not None:
        session.data.handoff_to_buyer_agent = handoff_to_buyer_agent
    if buyer_agent_run_id is not None:
        session.data.buyer_agent_run_id = buyer_agent_run_id
    if buyer_agent_outcome is not None:
        session.data.buyer_agent_outcome = buyer_agent_outcome
    if waitlist_opted_in is not None:
        session.data.waitlist_opted_in = waitlist_opted_in
    if waitlist_declined is not None:
        session.data.waitlist_declined = waitlist_declined
    if conversation_complete is not None:
        session.data.conversation_complete = conversation_complete
    session.data.last_active_at = datetime.now(timezone.utc)
    return await WizardSession.update(session)
