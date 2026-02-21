"""Admin endpoints for OffsetsDB sync management (dev/hackathon tool)."""

from fastapi import APIRouter, BackgroundTasks

from models.operations.sync_logs import sync_log_get_recent
from utils import log

logger = log.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/offsets-db/sync", status_code=202)
async def admin_trigger_sync(background_tasks: BackgroundTasks):
    """Trigger a full OffsetsDB sync in the background."""
    from offsets_db_sync import run_offsets_db_sync

    background_tasks.add_task(run_offsets_db_sync)
    return {"status": "accepted", "message": "OffsetsDB sync started in background"}


@router.get("/offsets-db/sync-log")
async def admin_get_sync_logs(limit: int = 20):
    """Return recent sync log entries."""
    logs = await sync_log_get_recent(limit=limit)
    return {
        "logs": [
            {
                "id": log_entry.id,
                "sync_type": log_entry.data.sync_type,
                "status": log_entry.data.status,
                "started_at": log_entry.data.started_at.isoformat() if log_entry.data.started_at else None,
                "completed_at": log_entry.data.completed_at.isoformat() if log_entry.data.completed_at else None,
                "rows_processed": log_entry.data.rows_processed,
                "rows_upserted": log_entry.data.rows_upserted,
                "rows_failed": log_entry.data.rows_failed,
                "duration_ms": log_entry.data.duration_ms,
                "error_message": log_entry.data.error_message,
            }
            for log_entry in logs
        ],
        "total": len(logs),
    }
