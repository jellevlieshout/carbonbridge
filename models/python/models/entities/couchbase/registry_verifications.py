from typing import Optional
from datetime import datetime
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData


class RegistryVerificationData(BaseCouchbaseEntityData):
    listing_id: str
    queried_at: Optional[datetime] = None
    raw_response: Optional[dict] = None
    is_valid: bool = False
    serial_numbers_available: bool = False
    project_verified: bool = False
    error_message: Optional[str] = None


class RegistryVerification(BaseModelCouchbase[RegistryVerificationData]):
    _collection_name = "registry_verifications"
