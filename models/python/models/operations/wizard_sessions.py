from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from models.entities.couchbase.wizard_sessions import (
    WizardSession, WizardSessionData, ConversationMessage, ExtractedPreferences,
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
    session_id: str, step: str,
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
) -> Optional[WizardSession]:
    """
    Persist graph-level context (footprint, listings, draft order) so the
    session can be fully resumed after a browser close.
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
    session.data.last_active_at = datetime.now(timezone.utc)
    return await WizardSession.update(session)
