from typing import List, Optional
from datetime import datetime, timezone
from models.entities.couchbase.registry_verifications import RegistryVerification, RegistryVerificationData


async def verification_create(listing_id: str, raw_response: dict, is_valid: bool, **kwargs) -> RegistryVerification:
    data = RegistryVerificationData(
        listing_id=listing_id,
        queried_at=datetime.now(timezone.utc),
        raw_response=raw_response,
        is_valid=is_valid,
        **kwargs,
    )
    return await RegistryVerification.create(data)


async def verification_get(verification_id: str) -> Optional[RegistryVerification]:
    return await RegistryVerification.get(verification_id)


async def verification_get_by_listing(listing_id: str) -> List[RegistryVerification]:
    keyspace = RegistryVerification.get_keyspace()
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE listing_id = $listing_id ORDER BY queried_at DESC"
    )
    rows = await keyspace.query(query, listing_id=listing_id)
    return [
        RegistryVerification(id=row["id"], data=row.get("registry_verifications"))
        for row in rows if row.get("registry_verifications")
    ]


async def verification_get_latest_for_listing(listing_id: str) -> Optional[RegistryVerification]:
    results = await verification_get_by_listing(listing_id)
    return results[0] if results else None
