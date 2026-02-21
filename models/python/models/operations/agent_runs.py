from typing import List, Optional
from models.entities.couchbase.agent_runs import AgentRun, AgentRunData, TraceStep


async def agent_run_create(data: AgentRunData) -> AgentRun:
    return await AgentRun.create(data, user_id=data.owner_id)


async def agent_run_get(run_id: str) -> Optional[AgentRun]:
    return await AgentRun.get(run_id)


async def agent_run_update(run: AgentRun) -> AgentRun:
    return await AgentRun.update(run)


async def agent_run_append_step(run_id: str, step: TraceStep) -> Optional[AgentRun]:
    run = await AgentRun.get(run_id)
    if not run:
        return None
    run.data.trace_steps.append(step)
    return await AgentRun.update(run)


async def agent_run_complete(run_id: str, action_taken: str, **kwargs) -> Optional[AgentRun]:
    from datetime import datetime, timezone
    run = await AgentRun.get(run_id)
    if not run:
        return None
    run.data.status = "completed"
    run.data.completed_at = datetime.now(timezone.utc)
    run.data.action_taken = action_taken
    for key, value in kwargs.items():
        if hasattr(run.data, key):
            setattr(run.data, key, value)
    return await AgentRun.update(run)


async def agent_run_fail(run_id: str, error_message: str) -> Optional[AgentRun]:
    from datetime import datetime, timezone
    run = await AgentRun.get(run_id)
    if not run:
        return None
    run.data.status = "failed"
    run.data.completed_at = datetime.now(timezone.utc)
    run.data.action_taken = "failed"
    run.data.error_message = error_message
    return await AgentRun.update(run)


async def agent_run_get_by_owner(
    owner_id: str,
    agent_type: Optional[str] = None,
    limit: int = 50,
) -> List[AgentRun]:
    keyspace = AgentRun.get_keyspace()
    conditions = ["owner_id = $owner_id"]
    params = {"owner_id": owner_id}

    if agent_type:
        conditions.append("agent_type = $agent_type")
        params["agent_type"] = agent_type

    where = " AND ".join(conditions)
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE {where} ORDER BY triggered_at DESC LIMIT {limit}"
    )
    rows = await keyspace.query(query, **params)
    return [
        AgentRun(id=row["id"], data=row.get("agent_runs"))
        for row in rows if row.get("agent_runs")
    ]
