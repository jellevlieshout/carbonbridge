from typing import Optional
from datetime import datetime
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData


class SyncLogData(BaseCouchbaseEntityData):
    sync_type: str = "offsets_db"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rows_processed: int = 0
    rows_upserted: int = 0
    rows_failed: int = 0
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    status: str = "running"


class SyncLog(BaseModelCouchbase[SyncLogData]):
    _collection_name = "sync_logs"
