from typing import Any, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData


class ScoreBreakdown(BaseModel):
    project_type_match: float = 0.0
    price_score: float = 0.0
    vintage_score: float = 0.0
    co_benefit_score: float = 0.0
    total: float = 0.0


class TraceStep(BaseModel):
    step_index: int
    step_type: Literal["tool_call", "reasoning", "decision", "output"]
    label: str
    input: Any = None
    output: Any = None
    duration_ms: Optional[int] = None
    listings_considered: List[str] = []
    score_breakdown: Optional[ScoreBreakdown] = None


class AgentRunData(BaseCouchbaseEntityData):
    agent_type: Literal["autonomous_buyer", "seller_advisory"]
    owner_id: str
    triggered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    trigger_reason: Literal["scheduled", "manual", "threshold_exceeded"] = "manual"
    status: Literal["running", "completed", "failed", "awaiting_approval"] = "running"
    trace_steps: List[TraceStep] = []
    listings_shortlisted: List[str] = []
    final_selection_id: Optional[str] = None
    selection_rationale: Optional[str] = None
    action_taken: Optional[Literal["purchased", "proposed", "skipped", "failed"]] = None
    order_id: Optional[str] = None
    error_message: Optional[str] = None


class AgentRun(BaseModelCouchbase[AgentRunData]):
    _collection_name = "agent_runs"
