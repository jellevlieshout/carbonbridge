"""
OffsetsDB sync pipeline.

Downloads the latest OffsetsDB CSV from CarbonPlan's S3 bucket,
parses it, and upserts projects + market insights into Couchbase.
"""

import io
import time
import zipfile
from datetime import datetime, timezone

import httpx
import pandas as pd

from models.entities.couchbase.offsets_db_projects import OffsetsDBProjectData
from models.entities.couchbase.market_insights import MarketInsightsData
from models.operations.offsets_db_projects import offsets_db_project_upsert
from models.operations.market_insights import market_insights_upsert
from models.operations.sync_logs import sync_log_create, sync_log_complete, sync_log_fail
from utils import log

logger = log.get_logger(__name__)

OFFSETS_DB_ZIP_URL = (
    "https://carbonplan-offsets-db.s3.us-west-2.amazonaws.com/"
    "production/latest/offsets-db.csv.zip"
)

VALID_REGISTRIES = {"ACR", "ART", "CAR", "GLD", "VCS"}

CATEGORY_MAP: dict[str, str] = {
    "forest": "Forest",
    "forests": "Forest",
    "forestry": "Forest",
    "afforestation": "Forest",
    "redd": "Forest",
    "redd+": "Forest",
    "renewable energy": "Renewable Energy",
    "renewable": "Renewable Energy",
    "solar": "Renewable Energy",
    "wind": "Renewable Energy",
    "hydro": "Renewable Energy",
    "ghg management": "GHG Management",
    "waste": "GHG Management",
    "landfill": "GHG Management",
    "methane": "GHG Management",
    "energy efficiency": "Energy Efficiency",
    "fuel switching": "Fuel Switching",
    "agriculture": "Agriculture",
}


def _normalize_category(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower()
    for pattern, category in CATEGORY_MAP.items():
        if pattern in key:
            return category
    return "Other"


def _normalize_registry(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower().replace("-", " ").replace("_", " ")
    # Map known names / aliases to short codes
    if key in ("verra", "vcs"):
        return "VCS"
    if key in ("gold standard", "gld", "gs"):
        return "GLD"
    if key in ("american carbon registry", "acr"):
        return "ACR"
    if key in ("art trees", "art"):
        return "ART"
    if key in ("climate action reserve", "car"):
        return "CAR"
    upper = raw.strip().upper()
    if upper in VALID_REGISTRIES:
        return upper
    return None


def _safe_float(val) -> float:
    try:
        return float(val) if pd.notna(val) else 0.0
    except (ValueError, TypeError):
        return 0.0


def _row_to_project_data(row: pd.Series) -> OffsetsDBProjectData | None:
    """Map a CSV row to an OffsetsDBProjectData instance. Returns None if invalid."""
    project_id = str(row.get("project_id", "")).strip()
    if not project_id:
        return None

    registry = _normalize_registry(row.get("registry"))
    if registry is None:
        return None

    return OffsetsDBProjectData(
        offsets_db_project_id=project_id,
        registry=registry,
        name=str(row.get("name", "")).strip() or None,
        category=_normalize_category(row.get("category")),
        project_type=str(row.get("project_type", "")).strip() or None,
        country=str(row.get("country", "")).strip() or None,
        protocol=str(row.get("protocol", "")).strip() or None,
        total_credits_issued=_safe_float(row.get("issued")),
        total_credits_retired=_safe_float(row.get("retired")),
        status=str(row.get("status", "")).strip() or None,
        offsets_db_url=f"https://offsets-db.carbonplan.org/project/{project_id}",
        raw_data=row.to_dict(),
        synced_at=datetime.now(timezone.utc),
    )


def _compute_market_insights(df: pd.DataFrame) -> MarketInsightsData:
    """Aggregate market insights from the full DataFrame."""
    credits_by_registry: dict[str, float] = {}
    credits_by_category: dict[str, float] = {}
    credits_by_country: dict[str, float] = {}

    for _, row in df.iterrows():
        issued = _safe_float(row.get("issued"))
        registry = _normalize_registry(row.get("registry"))
        category = _normalize_category(row.get("category"))
        country = str(row.get("country", "")).strip() or "Unknown"

        if registry:
            credits_by_registry[registry] = credits_by_registry.get(registry, 0) + issued
        if category:
            credits_by_category[category] = credits_by_category.get(category, 0) + issued
        credits_by_country[country] = credits_by_country.get(country, 0) + issued

    # Keep top 30 countries by issued volume
    top_countries = dict(
        sorted(credits_by_country.items(), key=lambda x: x[1], reverse=True)[:30]
    )

    # Coverage = fraction of projects with retired > 0
    coverage_by_category: dict[str, float] = {}
    for _, row in df.iterrows():
        category = _normalize_category(row.get("category"))
        if not category:
            continue
        if category not in coverage_by_category:
            coverage_by_category[category] = 0.0
    if len(df) > 0:
        for category in coverage_by_category:
            cat_df = df[df.apply(
                lambda r: _normalize_category(r.get("category")) == category, axis=1
            )]
            if len(cat_df) > 0:
                retired_count = cat_df[cat_df["retired"].apply(_safe_float) > 0].shape[0]
                coverage_by_category[category] = round(retired_count / len(cat_df), 4)

    return MarketInsightsData(
        credits_by_registry=credits_by_registry,
        credits_by_category=credits_by_category,
        credits_by_country=top_countries,
        coverage_by_category=coverage_by_category,
        computed_at=datetime.now(timezone.utc),
    )


async def run_offsets_db_sync() -> dict:
    """
    Download, parse, and upsert the full OffsetsDB dataset.
    Returns a summary dict with counts.
    """
    sync_log = await sync_log_create("offsets_db")
    start = time.monotonic()

    rows_processed = 0
    rows_upserted = 0
    rows_failed = 0

    try:
        # Download the zip
        logger.info(f"Downloading OffsetsDB from {OFFSETS_DB_ZIP_URL}")
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(OFFSETS_DB_ZIP_URL)
            resp.raise_for_status()

        # Extract projects CSV from zip (not credits.csv)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
            if not csv_names:
                raise ValueError("No CSV file found in zip archive")
            # Prefer projects.csv over credits.csv
            target = next((n for n in csv_names if "projects" in n.lower()), csv_names[0])
            csv_bytes = zf.read(target)

        logger.info(f"Parsing CSV ({len(csv_bytes):,} bytes)")
        df = pd.read_csv(io.BytesIO(csv_bytes), low_memory=False)
        rows_processed = len(df)
        logger.info(f"Loaded {rows_processed:,} rows from OffsetsDB")

        # Upsert projects
        for _, row in df.iterrows():
            try:
                data = _row_to_project_data(row)
                if data is None:
                    rows_failed += 1
                    continue
                await offsets_db_project_upsert(data.offsets_db_project_id, data)
                rows_upserted += 1
            except Exception as e:
                rows_failed += 1
                if rows_failed <= 5:
                    logger.warning(f"Failed to upsert row: {e}")

            if rows_upserted % 500 == 0 and rows_upserted > 0:
                logger.info(f"Progress: {rows_upserted:,} upserted, {rows_failed:,} failed")

        # Recompute market insights
        logger.info("Computing market insights from OffsetsDB data")
        insights = _compute_market_insights(df)
        await market_insights_upsert(insights)

        duration_ms = int((time.monotonic() - start) * 1000)
        await sync_log_complete(
            sync_log.id,
            rows_processed=rows_processed,
            rows_upserted=rows_upserted,
            rows_failed=rows_failed,
            duration_ms=duration_ms,
        )

        summary = {
            "status": "completed",
            "rows_processed": rows_processed,
            "rows_upserted": rows_upserted,
            "rows_failed": rows_failed,
            "duration_ms": duration_ms,
            "sync_log_id": sync_log.id,
        }
        logger.info(f"OffsetsDB sync completed: {summary}")
        return summary

    except Exception as e:
        logger.error(f"OffsetsDB sync failed: {e}", exc_info=True)
        await sync_log_fail(sync_log.id, str(e))
        return {
            "status": "failed",
            "error": str(e),
            "rows_processed": rows_processed,
            "rows_upserted": rows_upserted,
            "rows_failed": rows_failed,
            "sync_log_id": sync_log.id,
        }
