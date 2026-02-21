import { get, post } from './client';

export interface ScoreBreakdown {
    listing_id: string | null;
    project_type_match: number;
    price_score: number;
    vintage_score: number;
    co_benefit_score: number;
    verification_score: number;
    quantity_fit: number;
    total: number;
}

export interface TraceStep {
    step_index: number;
    step_type: 'tool_call' | 'reasoning' | 'decision' | 'output';
    label: string;
    input: any;
    output: any;
    duration_ms: number | null;
    listings_considered: string[];
    score_breakdown: ScoreBreakdown | null;
}

export interface AgentRunSummary {
    id: string;
    agent_type: 'autonomous_buyer' | 'seller_advisory';
    status: 'running' | 'completed' | 'failed' | 'awaiting_approval';
    trigger_reason: string;
    action_taken: string | null;
    triggered_at: string | null;
    completed_at: string | null;
    final_selection_id: string | null;
    order_id: string | null;
    error_message: string | null;
    selection_rationale: string | null;
}

export interface AgentRunDetail extends AgentRunSummary {
    trace_steps: TraceStep[];
    listings_shortlisted: string[];
}

export interface TriggerResponse {
    run_id: string;
    status: string;
    message: string;
}

export async function agentTrigger(): Promise<TriggerResponse> {
    return await post('/agent/trigger');
}

export async function agentTriggerAdvisory(): Promise<TriggerResponse> {
    return await post('/agent/trigger-advisory');
}

export async function agentRunsList(agentType?: string): Promise<AgentRunSummary[]> {
    const params = agentType ? `?agent_type=${agentType}` : '';
    return await get(`/agent/runs${params}`);
}

export async function agentRunGet(runId: string): Promise<AgentRunDetail> {
    return await get(`/agent/runs/${runId}`);
}

export async function agentRunApprove(runId: string): Promise<AgentRunDetail> {
    return await post(`/agent/runs/${runId}/approve`);
}

export async function agentRunReject(runId: string): Promise<AgentRunDetail> {
    return await post(`/agent/runs/${runId}/reject`);
}
