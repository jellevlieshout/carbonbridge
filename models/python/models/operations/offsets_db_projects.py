from typing import Any, Dict, List, Optional
from models.entities.couchbase.offsets_db_projects import OffsetsDBProject, OffsetsDBProjectData


async def offsets_db_project_upsert(project_id: str, data: OffsetsDBProjectData) -> OffsetsDBProject:
    return await OffsetsDBProject.create_or_update(key=project_id, data=data)


async def offsets_db_project_get(project_id: str) -> Optional[OffsetsDBProject]:
    return await OffsetsDBProject.get(project_id)


async def offsets_db_project_search(
    registry: Optional[str] = None,
    category: Optional[str] = None,
    country: Optional[str] = None,
    market_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[OffsetsDBProject]:
    keyspace = OffsetsDBProject.get_keyspace()
    conditions = []
    params: Dict[str, Any] = {}

    if registry:
        conditions.append("registry = $registry")
        params["registry"] = registry
    if category:
        conditions.append("category = $category")
        params["category"] = category
    if country:
        conditions.append("country = $country")
        params["country"] = country
    if market_type:
        conditions.append("market_type = $market_type")
        params["market_type"] = market_type

    where = " AND ".join(conditions) if conditions else "1=1"
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE {where} "
        f"ORDER BY total_credits_issued DESC "
        f"LIMIT {limit} OFFSET {offset}"
    )
    rows = await keyspace.query(query, **params)
    return [
        OffsetsDBProject(id=row["id"], data=row.get("offsets_db_projects"))
        for row in rows if row.get("offsets_db_projects")
    ]


async def offsets_db_project_get_market_context(
    project_type: Optional[str] = None,
    category: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 20,
) -> List[OffsetsDBProject]:
    """Fetch comparable projects for agent market context."""
    keyspace = OffsetsDBProject.get_keyspace()
    conditions = []
    params: Dict[str, Any] = {}

    if project_type:
        conditions.append("project_type = $project_type")
        params["project_type"] = project_type
    if category:
        conditions.append("category = $category")
        params["category"] = category
    if country:
        conditions.append("country = $country")
        params["country"] = country

    where = " AND ".join(conditions) if conditions else "1=1"
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE {where} "
        f"ORDER BY total_credits_issued DESC "
        f"LIMIT {limit}"
    )
    rows = await keyspace.query(query, **params)
    return [
        OffsetsDBProject(id=row["id"], data=row.get("offsets_db_projects"))
        for row in rows if row.get("offsets_db_projects")
    ]
