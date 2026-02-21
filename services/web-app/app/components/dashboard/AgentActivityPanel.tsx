import React, { useState } from 'react';
import { useAgentRuns, useAgentRunDetail, useAgentTrigger, useAgentApprove, useAgentReject } from '../../modules/shared/queries/useAgentRuns';
import type { AgentRunSummary, TraceStep } from '@clients/api/agent';

function StatusBadge({ status }: { status: string }) {
    const styles: Record<string, string> = {
        running: 'bg-ember/20 text-ember border-ember/30',
        completed: 'bg-emerald-100 text-emerald-700 border-emerald-200',
        failed: 'bg-red-100 text-red-700 border-red-200',
        awaiting_approval: 'bg-amber-100 text-amber-700 border-amber-200',
    };
    return (
        <span className={`text-[10px] font-mono font-semibold uppercase tracking-wider px-2 py-1 rounded-full border ${styles[status] || 'bg-slate/10 text-slate border-slate/20'}`}>
            {status === 'awaiting_approval' ? 'needs approval' : status}
        </span>
    );
}

function StepIcon({ type }: { type: string }) {
    const icons: Record<string, string> = {
        tool_call: '{}',
        reasoning: '?',
        decision: '!',
        output: '>',
    };
    const colors: Record<string, string> = {
        tool_call: 'bg-canopy/10 text-canopy',
        reasoning: 'bg-slate/10 text-slate',
        decision: 'bg-ember/10 text-ember',
        output: 'bg-emerald-100 text-emerald-700',
    };
    return (
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center font-mono text-xs font-bold shrink-0 ${colors[type] || 'bg-slate/10 text-slate'}`}>
            {icons[type] || '·'}
        </div>
    );
}

function TraceTimeline({ steps }: { steps: TraceStep[] }) {
    if (!steps.length) {
        return <p className="font-mono text-xs text-slate/40 py-4">No trace steps yet...</p>;
    }
    return (
        <div className="flex flex-col gap-1">
            {steps.map((step, i) => (
                <div key={i} className="flex items-start gap-3 group">
                    <div className="flex flex-col items-center">
                        <StepIcon type={step.step_type} />
                        {i < steps.length - 1 && <div className="w-px h-full min-h-[16px] bg-slate/10" />}
                    </div>
                    <div className="flex-1 pb-3">
                        <div className="flex items-center gap-2">
                            <span className="font-sans text-sm font-medium text-slate">{step.label}</span>
                            {step.duration_ms != null && (
                                <span className="font-mono text-[10px] text-slate/40">{step.duration_ms}ms</span>
                            )}
                        </div>
                        {step.output && typeof step.output === 'object' && (
                            <StepOutput output={step.output} type={step.step_type} />
                        )}
                        {step.output && typeof step.output === 'string' && (
                            <p className="font-mono text-xs text-slate/60 mt-1 leading-relaxed">{step.output}</p>
                        )}
                        {step.score_breakdown && (
                            <div className="mt-1 flex flex-wrap gap-2">
                                <span className="font-mono text-[10px] bg-canopy/5 text-canopy px-1.5 py-0.5 rounded">
                                    score: {step.score_breakdown.total.toFixed(2)}
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}

function StepOutput({ output, type }: { output: Record<string, any>; type: string }) {
    if (type === 'decision' && output.action) {
        return (
            <div className="mt-1.5 bg-white/60 rounded-lg p-3 border border-slate/5">
                <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs font-semibold text-ember">{output.action}</span>
                    {output.listing_id && (
                        <span className="font-mono text-[10px] text-slate/50">listing: {output.listing_id}</span>
                    )}
                </div>
                {output.rationale && (
                    <p className="font-serif italic text-sm text-canopy/80 leading-relaxed">{output.rationale}</p>
                )}
                {output.total_cost_eur != null && (
                    <span className="font-mono text-xs text-slate/60 mt-1 block">
                        {output.quantity_tonnes}t at {output.total_cost_eur.toFixed(2)}
                    </span>
                )}
            </div>
        );
    }

    const keys = Object.keys(output).slice(0, 4);
    if (!keys.length) return null;

    return (
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
            {keys.map(k => (
                <span key={k} className="font-mono text-[10px] text-slate/50">
                    {k}: {typeof output[k] === 'object' ? JSON.stringify(output[k]).slice(0, 60) : String(output[k]).slice(0, 60)}
                </span>
            ))}
        </div>
    );
}

function RunCard({
    run,
    isSelected,
    onSelect,
}: {
    run: AgentRunSummary;
    isSelected: boolean;
    onSelect: () => void;
}) {
    const time = run.triggered_at
        ? new Date(run.triggered_at).toLocaleString('en-GB', {
              day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
          })
        : 'Pending...';

    return (
        <button
            onClick={onSelect}
            className={`w-full text-left p-4 rounded-xl border transition-all duration-200 ${
                isSelected
                    ? 'bg-white border-canopy/30 shadow-sm'
                    : 'bg-white/40 border-transparent hover:bg-white/70'
            }`}
        >
            <div className="flex items-center justify-between mb-1.5">
                <span className="font-mono text-xs text-slate/50">{time}</span>
                <StatusBadge status={run.status} />
            </div>
            {run.action_taken && (
                <span className="font-sans text-sm font-medium text-slate capitalize">{run.action_taken}</span>
            )}
            {run.error_message && (
                <p className="font-mono text-xs text-red-500 mt-1 truncate">{run.error_message}</p>
            )}
        </button>
    );
}

export function AgentActivityPanel() {
    const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

    const { data: runs, isLoading: runsLoading, error: runsError } = useAgentRuns();
    const { data: runDetail } = useAgentRunDetail(selectedRunId);
    const triggerMutation = useAgentTrigger();
    const approveMutation = useAgentApprove();
    const rejectMutation = useAgentReject();

    const handleTrigger = () => {
        triggerMutation.mutate(undefined, {
            onError: (err: any) => {
                console.error('Agent trigger failed:', err);
            },
        });
    };

    return (
        <div className="w-full mt-12 bg-mist rounded-[2rem] border-l-[8px] border-l-canopy overflow-hidden shadow-sm flex flex-col transition-colors duration-500">
            {/* Header */}
            <div className="px-10 pt-10 pb-6 flex items-center justify-between">
                <div>
                    <h3 className="font-serif italic text-3xl text-canopy">Autonomous Agent</h3>
                    <p className="font-sans text-sm text-slate/60 mt-1">
                        Your AI purchasing agent scores listings and executes trades on your behalf.
                    </p>
                </div>
                <button
                    onClick={handleTrigger}
                    disabled={triggerMutation.isPending}
                    className="px-6 py-3 bg-canopy text-linen font-sans font-medium rounded-xl hover:bg-canopy/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    {triggerMutation.isPending ? (
                        <>
                            <span className="w-3 h-3 border-2 border-linen/30 border-t-linen rounded-full animate-spin" />
                            Running...
                        </>
                    ) : (
                        'Run Agent Now'
                    )}
                </button>
            </div>

            <div className="px-10 pb-10 flex flex-col lg:flex-row gap-6">
                {/* Left: Run History */}
                <div className="lg:w-1/3 flex flex-col gap-2 max-h-[28rem] overflow-y-auto pr-1">
                    <span className="font-sans font-semibold text-xs text-slate/40 uppercase tracking-wider mb-2">
                        Run History
                    </span>

                    {runsLoading && (
                        <div className="flex items-center gap-2 py-8 justify-center">
                            <span className="w-3 h-3 border-2 border-slate/20 border-t-slate rounded-full animate-spin" />
                            <span className="font-mono text-xs text-slate/40">Loading runs...</span>
                        </div>
                    )}

                    {runsError && (
                        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                            <p className="font-mono text-xs text-red-600">Failed to load agent runs</p>
                        </div>
                    )}

                    {runs && runs.length === 0 && (
                        <div className="bg-white/40 rounded-xl p-6 text-center">
                            <p className="font-sans text-sm text-slate/40">No runs yet</p>
                            <p className="font-mono text-xs text-slate/30 mt-1">
                                Click "Run Agent Now" to start
                            </p>
                        </div>
                    )}

                    {runs?.map((run) => (
                        <RunCard
                            key={run.id}
                            run={run}
                            isSelected={selectedRunId === run.id}
                            onSelect={() => setSelectedRunId(run.id)}
                        />
                    ))}
                </div>

                {/* Right: Run Detail */}
                <div className="flex-1 bg-white/50 rounded-2xl border border-white/60 p-6 min-h-[20rem]">
                    {!selectedRunId ? (
                        <div className="flex items-center justify-center h-full">
                            <p className="font-serif italic text-lg text-slate/30">
                                Select a run to see its trace
                            </p>
                        </div>
                    ) : !runDetail ? (
                        <div className="flex items-center justify-center h-full gap-2">
                            <span className="w-3 h-3 border-2 border-slate/20 border-t-slate rounded-full animate-spin" />
                            <span className="font-mono text-xs text-slate/40">Loading trace...</span>
                        </div>
                    ) : (
                        <div className="flex flex-col h-full">
                            {/* Run header */}
                            <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate/10">
                                <div className="flex items-center gap-3">
                                    <StatusBadge status={runDetail.status} />
                                    {runDetail.status === 'running' && (
                                        <div className="flex items-center gap-1.5">
                                            <div className="w-1.5 h-1.5 rounded-full bg-ember animate-ping" />
                                            <span className="font-mono text-[10px] text-ember">Live</span>
                                        </div>
                                    )}
                                </div>
                                <span className="font-mono text-[10px] text-slate/30">{runDetail.id.slice(0, 12)}...</span>
                            </div>

                            {/* Selection rationale */}
                            {runDetail.selection_rationale && (
                                <div className="mb-4 bg-canopy/5 rounded-lg p-3 border border-canopy/10">
                                    <p className="font-serif italic text-sm text-canopy leading-relaxed">
                                        "{runDetail.selection_rationale}"
                                    </p>
                                </div>
                            )}

                            {/* Trace steps */}
                            <div className="flex-1 overflow-y-auto max-h-[18rem] pr-1">
                                <TraceTimeline steps={runDetail.trace_steps} />
                            </div>

                            {/* Approve / Reject buttons */}
                            {runDetail.status === 'awaiting_approval' && (
                                <div className="mt-4 pt-4 border-t border-slate/10 flex gap-3">
                                    <button
                                        onClick={() => approveMutation.mutate(runDetail.id)}
                                        disabled={approveMutation.isPending}
                                        className="flex-1 py-3 bg-canopy text-linen font-sans font-medium rounded-xl hover:bg-canopy/90 transition-colors disabled:opacity-50"
                                    >
                                        {approveMutation.isPending ? 'Approving...' : 'Approve Purchase'}
                                    </button>
                                    <button
                                        onClick={() => rejectMutation.mutate(runDetail.id)}
                                        disabled={rejectMutation.isPending}
                                        className="flex-1 py-3 bg-white text-slate font-sans font-medium rounded-xl border border-slate/20 hover:bg-slate/5 transition-colors disabled:opacity-50"
                                    >
                                        {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
                                    </button>
                                </div>
                            )}

                            {/* Order link */}
                            {runDetail.order_id && (
                                <div className="mt-3 flex items-center gap-2">
                                    <span className="font-mono text-[10px] text-slate/40">Order:</span>
                                    <span className="font-mono text-xs text-canopy">{runDetail.order_id}</span>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
