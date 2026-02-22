import React, { useEffect, useState, useMemo } from 'react';
import { useAgentRuns, useAgentRunDetail } from '~/modules/shared/queries/useAgentRuns';
import type { TraceStep } from '@clients/api/agent';

type StreamTag = 'SCAN' | 'ALERT' | 'MATCH' | 'HOLD';

type StreamLog = {
    id: string;
    time: string;
    tag: StreamTag;
    text: string;
};

function stepToTag(step: TraceStep): StreamTag {
    const out = step.output && typeof step.output === 'object' ? step.output : {};
    switch (step.label) {
        case 'Agent run initialized':
        case 'Loaded buyer profile and criteria':
        case 'Starting Gemini listing analysis':
            return 'SCAN';
        case 'Budget check passed':
        case 'Selected best match':
        case 'Gemini analysis complete':
            if (out.action === 'skip') return 'HOLD';
            if (out.action === 'propose') return 'ALERT';
            return 'MATCH';
        case 'Monthly budget exhausted':
        case 'Agent decided to skip':
            return 'HOLD';
        case 'Proposed for buyer approval (above auto-approve threshold)':
            return 'ALERT';
        case 'Created order and executed payment':
            return 'MATCH';
        default:
            return 'SCAN';
    }
}

function stepToText(step: TraceStep): string {
    const out = step.output && typeof step.output === 'object' ? step.output : {};
    switch (step.label) {
        case 'Agent run initialized':
            return 'Autonomous agent triggered. Initializing...';
        case 'Loaded buyer profile and criteria':
            return `Profile loaded. Budget: €${Number(out.monthly_budget_eur || 0).toLocaleString()}/month.`;
        case 'Budget check passed':
            return `Budget verified — €${Number(out.remaining_eur || 0).toLocaleString()} available.`;
        case 'Monthly budget exhausted':
            return 'Budget exhausted. Pausing until next cycle.';
        case 'Starting Gemini listing analysis':
            return 'Cross-referencing listings via Gemini AI...';
        case 'Gemini analysis complete':
            if (out.action === 'skip') return 'No listings meet quality threshold.';
            if (out.action === 'propose') return `Match found — €${Number(out.total_cost_eur || 0).toFixed(2)}. Awaiting approval.`;
            return `Analysis complete. Best: ${out.quantity_tonnes || '?'}t at €${Number(out.total_cost_eur || 0).toFixed(2)}.`;
        case 'Selected best match':
            return `Selected: ${out.project_name || 'Listing'} — ${out.quantity_tonnes || '?'}t.`;
        case 'Agent decided to skip':
            return out.rationale ? String(out.rationale).slice(0, 100) : 'No suitable listings found.';
        case 'Created order and executed payment':
            return `Order executed — ${out.quantity_tonnes || '?'}t for €${Number(out.total_eur || 0).toFixed(2)}.`;
        case 'Agent run completed successfully':
            return out.rationale ? String(out.rationale).slice(0, 100) : 'Run completed.';
        default:
            return step.label;
    }
}

const getTagColor = (tag: string) => {
    switch (tag) {
        case 'SCAN': return 'text-slate/60 bg-slate/10';
        case 'ALERT': return 'text-amber-700 bg-amber-100';
        case 'MATCH': return 'text-emerald-700 bg-emerald-100';
        case 'HOLD': return 'text-ember bg-ember/10';
        default: return 'text-slate bg-slate/10';
    }
};

export function AgentStreamTile() {
    const { data: runs } = useAgentRuns();
    const latestRunId = runs?.[0]?.id ?? null;
    const { data: runDetail } = useAgentRunDetail(latestRunId);

    const isRunning = runDetail?.status === 'running';

    // Build the full set of logs from trace steps (most recent first)
    const allLogs: StreamLog[] = useMemo(() => {
        if (!runDetail?.trace_steps?.length) return [];
        const triggeredAt = runDetail.triggered_at ? new Date(runDetail.triggered_at) : new Date();
        return [...runDetail.trace_steps]
            .reverse()
            .slice(0, 5)
            .map((step) => {
                const offset = step.duration_ms || 0;
                const t = new Date(triggeredAt.getTime() + offset);
                const time = t.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                return {
                    id: `${runDetail.id}-${step.step_index}`,
                    time,
                    tag: stepToTag(step),
                    text: stepToText(step),
                };
            });
    }, [runDetail]);

    // Progressively reveal logs with a staggered interval for entrance animation
    const [visibleCount, setVisibleCount] = useState(0);

    useEffect(() => {
        if (allLogs.length === 0) {
            setVisibleCount(0);
            return;
        }
        // Start with first 2 visible immediately, then drip in the rest
        setVisibleCount(2);
        let count = 2;
        const interval = setInterval(() => {
            count++;
            if (count >= allLogs.length) {
                setVisibleCount(allLogs.length);
                clearInterval(interval);
                return;
            }
            setVisibleCount(count);
        }, 3000);
        return () => clearInterval(interval);
    }, [allLogs.length, latestRunId]);

    const logs = allLogs.slice(0, visibleCount);

    return (
        <div className="flex flex-col h-full w-full rounded-[1.25rem] bg-slate text-linen p-6 shadow-sm overflow-hidden relative">
            {/* Noise Texture */}
            <div
                className="absolute inset-0 pointer-events-none opacity-[0.05] mix-blend-overlay z-0"
                style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")" }}
            />

            <div className="flex items-center justify-between mb-4 relative z-10 border-b border-linen/10 pb-4">
                <h3 className="font-sans font-semibold tracking-tight">Agent Stream</h3>
                {isRunning ? (
                    <div className="flex items-center gap-2 bg-ember/20 px-2 py-1 rounded-[1rem] border border-ember/30">
                        <div className="w-1.5 h-1.5 rounded-full bg-ember animate-ping" />
                        <span className="font-mono text-[10px] uppercase font-semibold text-ember tracking-wider">Live</span>
                    </div>
                ) : logs.length > 0 ? (
                    <div className="flex items-center gap-2 bg-linen/10 px-2 py-1 rounded-[1rem] border border-linen/10">
                        <div className="w-1.5 h-1.5 rounded-full bg-linen/30" />
                        <span className="font-mono text-[10px] uppercase font-semibold text-linen/40 tracking-wider">Latest</span>
                    </div>
                ) : (
                    <div className="flex items-center gap-2 bg-linen/5 px-2 py-1 rounded-[1rem] border border-linen/10">
                        <div className="w-1.5 h-1.5 rounded-full bg-linen/20" />
                        <span className="font-mono text-[10px] uppercase font-semibold text-linen/30 tracking-wider">Idle</span>
                    </div>
                )}
            </div>

            <div className="relative z-10 flex-1 overflow-hidden flex flex-col justify-start mask-image-bottom">
                {allLogs.length === 0 && (
                    <div className="flex-1 flex items-center justify-center">
                        <p className="font-mono text-xs text-linen/25 text-center">
                            No agent activity yet.
                            <span className="inline-block w-2 h-4 bg-linen/15 align-middle ml-1 animate-pulse" />
                        </p>
                    </div>
                )}

                {logs.length > 0 && (
                    <div className="flex flex-col gap-3">
                        {logs.map((log, i) => (
                            <div
                                key={log.id}
                                className="flex flex-col text-sm font-mono animate-in slide-in-from-top-2 fade-in duration-500 ease-out"
                                style={{ opacity: Math.max(0.2, 1 - (i * 0.25)) }}
                            >
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="text-[10px] text-linen/40">{log.time}</span>
                                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-[4px] uppercase ${getTagColor(log.tag)}`}>
                                        {log.tag}
                                    </span>
                                </div>
                                <p className="text-xs leading-relaxed text-linen/80">{log.text}</p>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
