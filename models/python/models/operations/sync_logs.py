from typing import List, Optional
from datetime import datetime, timezone
from models.entities.couchbase.sync_logs import SyncLog, SyncLogData


async def sync_log_create(sync_type: str = "offsets_db") -> SyncLog:
    data = SyncLogData(
        sync_type=sync_type,
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    return await SyncLog.create(data)


async def sync_log_complete(
    log_id: str,
    rows_processed: int,
    rows_upserted: int,
    rows_failed: int,
    duration_ms: int,
) -> Optional[SyncLog]:
    log = await SyncLog.get(log_id)
    if not log:
        return None
    log.data.status = "completed"
    log.data.completed_at = datetime.now(timezone.utc)
    log.data.rows_processed = rows_processed
    log.data.rows_upserted = rows_upserted
    log.data.rows_failed = rows_failed
    log.data.duration_ms = duration_ms
    return await SyncLog.update(log)


async def sync_log_fail(log_id: str, error_message: str) -> Optional[SyncLog]:
    log = await SyncLog.get(log_id)
    if not log:
        return None
    log.data.status = "failed"
    log.data.completed_at = datetime.now(timezone.utc)
    log.data.error_message = error_message
    return await SyncLog.update(log)


async def sync_log_get_recent(limit: int = 20) -> List[SyncLog]:
    keyspace = SyncLog.get_keyspace()
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"ORDER BY started_at DESC LIMIT {limit}"
    )
    rows = await keyspace.query(query)
    return [
        SyncLog(id=row["id"], data=row.get("sync_logs"))
        for row in rows if row.get("sync_logs")
    ]
