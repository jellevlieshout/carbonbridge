import React, { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useAgentRuns, useAgentRunDetail, useAgentTrigger, useAgentApprove, useAgentReject } from '../../modules/shared/queries/useAgentRuns';
import type { AgentRunSummary, TraceStep } from '@clients/api/agent';

gsap.registerPlugin(ScrollTrigger);

const NOISE_BG = "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")";

/* ── Transform trace steps into friendly stream messages ──────── */
type StreamTag = 'SCAN' | 'MATCH' | 'ALERT' | 'HOLD' | 'BUY' | 'PAY' | 'DONE';

interface StreamMessage {
    tag: StreamTag;
    text: string;
    detail?: string;
    time: string;
}

/** Extract listing cards from trace steps for the shuffler */
interface ListingCard {
    id: string;
    name: string;
    price: string;
    standard: string;
    vintage: string;
    score: number | null;
    color: string;
    border: string;
}

const CARD_STYLES = [
    { color: 'bg-sage/10', border: 'border-sage/20' },
    { color: 'bg-canopy/5', border: 'border-canopy/10' },
    { color: 'bg-ember/5', border: 'border-ember/20' },
];

function extractListingCards(steps: TraceStep[]): ListingCard[] {
    const cards: ListingCard[] = [];
    for (const step of steps) {
        if (!step.output || typeof step.output !== 'object') continue;
        const out = step.output;
        // "Selected best match" and "Gemini analysis complete" contain listing info
        if (out.project_name && out.price_per_tonne_eur) {
            const style = CARD_STYLES[cards.length % CARD_STYLES.length];
            cards.push({
                id: out.listing_id || `card-${cards.length}`,
                name: out.project_name,
                price: `€${Number(out.price_per_tonne_eur).toFixed(2)}`,
                standard: out.standard || 'VCS',
                vintage: out.vintage || '2024',
                score: out.score ?? null,
                ...style,
            });
        }
    }
    return cards;
}

function traceToStream(step: TraceStep, triggeredAt: string | null): StreamMessage {
    // Compute a time offset from trigger
    const base = triggeredAt ? new Date(triggeredAt) : new Date();
    const offset = step.duration_ms || 0;
    const t = new Date(base.getTime() + offset);
    const time = t.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const out = step.output && typeof step.output === 'object' ? step.output : {};

    switch (step.label) {
        case 'Agent run initialized':
            return { tag: 'SCAN', text: 'Autonomous agent triggered. Initializing market scan...', time };
        case 'Loaded buyer profile and criteria':
            return {
                tag: 'SCAN',
                text: `Profile loaded. Budget: €${Number(out.monthly_budget_eur || 0).toLocaleString()}/month.`,
                detail: out.preferred_project_types?.length
                    ? `Criteria: ${out.preferred_project_types.join(', ')} projects · max €${Number(out.max_price_eur || 0).toFixed(0)}/t · vintage ≥${out.min_vintage_year || '—'}`
                    : undefined,
                time,
            };
        case 'Budget check passed':
            return { tag: 'MATCH', text: `Budget verified — €${Number(out.remaining_eur || 0).toLocaleString()} available this cycle.`, time };
        case 'Monthly budget exhausted':
            return { tag: 'HOLD', text: `Budget exhausted. €${Number(out.remaining_eur || 0).toFixed(0)} remaining. Pausing until next cycle.`, time };
        case 'Starting Gemini listing analysis':
            return { tag: 'SCAN', text: 'Cross-referencing listings against buyer criteria via Gemini AI...', detail: `Model: ${out.model || 'gemini-3-flash-preview'}`, time };
        case 'Gemini analysis complete':
            if (out.action === 'skip') return {
                tag: 'HOLD',
                text: 'Analysis complete. No listings meet quality threshold this cycle.',
                detail: out.rationale ? String(out.rationale).slice(0, 180) : undefined,
                time,
            };
            if (out.action === 'propose') return {
                tag: 'ALERT',
                text: `Match found — €${Number(out.total_cost_eur || 0).toFixed(2)} for ${out.quantity_tonnes || '?'}t. Awaiting approval.`,
                detail: out.rationale ? String(out.rationale).slice(0, 180) : undefined,
                time,
            };
            return {
                tag: 'MATCH',
                text: `Analysis complete. Best match: ${out.quantity_tonnes || '?'}t at €${Number(out.total_cost_eur || 0).toFixed(2)}.`,
                detail: out.rationale ? String(out.rationale).slice(0, 180) : undefined,
                time,
            };
        case 'Selected best match':
            return {
                tag: 'MATCH',
                text: `Selected: ${out.project_name || 'Listing'} — ${out.quantity_tonnes || '?'}t at €${Number(out.price_per_tonne_eur || 0).toFixed(2)}/tCO₂e.`,
                detail: out.score ? `Matching score: ${Number(out.score).toFixed(2)}` : undefined,
                time,
            };
        case 'Agent decided to skip':
            return { tag: 'HOLD', text: out.rationale ? String(out.rationale).slice(0, 160) : 'No suitable listings found. Will retry next cycle.', time };
        case 'Proposed for buyer approval (above auto-approve threshold)':
            return {
                tag: 'ALERT',
                text: `€${Number(out.total_cost_eur || 0).toFixed(2)} exceeds auto-approve limit (€${Number(out.auto_approve_under_eur || 0).toFixed(0)}). Awaiting your decision.`,
                detail: out.rationale ? String(out.rationale).slice(0, 180) : undefined,
                time,
            };
        case 'Created order and executed payment':
            return {
                tag: 'PAY',
                text: `Order executed — ${out.quantity_tonnes || '?'}t purchased for €${Number(out.total_eur || 0).toFixed(2)}.`,
                detail: out.payment_mode === 'stripe'
                    ? `Stripe payment confirmed · ${out.payment_intent_id}`
                    : out.payment_mode === 'mock'
                    ? 'Mock payment (Stripe not configured)'
                    : undefined,
                time,
            };
        case 'Agent run completed successfully':
            return {
                tag: 'DONE',
                text: out.rationale ? String(out.rationale).slice(0, 160) : 'Agent run completed successfully.',
                detail: [
                    ...(out.key_strengths?.length ? [`Strengths: ${out.key_strengths.join(', ')}`] : []),
                    ...(out.risks?.length ? [`Risks: ${out.risks.join(', ')}`] : []),
                ].join(' · ') || undefined,
                time,
            };
        default:
            return { tag: 'SCAN', text: step.label, time };
    }
}

function getTagStyle(tag: StreamTag): string {
    switch (tag) {
        case 'SCAN': return 'text-linen/50 bg-linen/8';
        case 'MATCH': return 'text-emerald-300 bg-emerald-500/15';
        case 'ALERT': return 'text-amber-300 bg-amber-500/15';
        case 'HOLD': return 'text-ember bg-ember/10';
        case 'BUY': return 'text-emerald-300 bg-emerald-500/20';
        case 'PAY': return 'text-violet-300 bg-violet-500/15';
        case 'DONE': return 'text-sage bg-sage/15';
        default: return 'text-linen/40 bg-linen/5';
    }
}

/* ── Listing Card Shuffler (embedded) ──────────────────────────── */
function ListingShuffler({ cards }: { cards: ListingCard[] }) {
    const [order, setOrder] = useState(cards);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => { setOrder(cards); }, [cards]);

    useEffect(() => {
        if (order.length < 2) return;
        const interval = setInterval(() => {
            setOrder(prev => {
                const next = [...prev];
                const last = next.pop();
                if (last) next.unshift(last);
                return next;
            });
        }, 3000);
        return () => clearInterval(interval);
    }, [order.length]);

    useEffect(() => {
        if (!containerRef.current || !order.length) return;
        const ctx = gsap.context(() => {
            gsap.fromTo(".agent-shuffler-card",
                { y: -15, opacity: 0, scale: 0.96 },
                { y: 0, opacity: 1, scale: 1, duration: 0.6, stagger: 0.08, ease: "back.out(1.5)" }
            );
        }, containerRef);
        return () => ctx.revert();
    }, [order]);

    if (!order.length) return null;

    return (
        <div ref={containerRef} className="relative h-[160px]">
            {order.map((card, i) => {
                const yOffset = i * 10;
                const scale = 1 - (i * 0.04);
                const opacity = 1 - (i * 0.25);
                return (
                    <div
                        key={card.id}
                        className={`agent-shuffler-card absolute w-full rounded-xl p-4 border shadow-sm transition-all duration-700 ease-spring ${
                            i === 0 ? 'bg-linen border-mist' : `${card.color} ${card.border} backdrop-blur-md`
                        }`}
                        style={{ transform: `translateY(${yOffset}px) scale(${scale})`, opacity, zIndex: 10 - i }}
                    >
                        <div className="flex justify-between items-start mb-2">
                            <span className="font-sans font-medium text-sm text-slate">{card.name}</span>
                            <span className="font-mono text-lg font-semibold text-slate">{card.price}</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="flex bg-white/50 w-fit rounded-full px-3 py-1 items-center gap-2 border border-black/5">
                                <span className="font-mono text-[10px] uppercase font-semibold text-slate/70">{card.standard}</span>
                                <span className="w-1 h-1 rounded-full bg-slate/20" />
                                <span className="font-mono text-[10px] text-slate/60">{card.vintage}</span>
                            </div>
                            {card.score !== null && (
                                <span className="font-mono text-[10px] text-emerald-700/60 bg-emerald-100/50 px-2 py-0.5 rounded-full">
                                    score: {card.score.toFixed(2)}
                                </span>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

/* ── Run selector pill ─────────────────────────────────────────── */
function RunPill({ run, isSelected, onSelect }: { run: AgentRunSummary; isSelected: boolean; onSelect: () => void }) {
    const time = run.triggered_at
        ? new Date(run.triggered_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
        : '...';
    const dot = run.status === 'running' ? 'bg-ember animate-ping'
        : run.status === 'completed' ? 'bg-emerald-400'
        : run.status === 'failed' ? 'bg-red-400'
        : 'bg-amber-400 animate-pulse';

    return (
        <button
            onClick={onSelect}
            className={`shrink-0 flex items-center gap-2 px-4 py-2 rounded-full border transition-all duration-300 ${
                isSelected
                    ? 'bg-linen/15 border-linen/20 text-linen'
                    : 'bg-linen/[0.03] border-linen/5 text-linen/35 hover:bg-linen/[0.07] hover:text-linen/55'
            }`}
        >
            <div className={`w-1.5 h-1.5 rounded-full ${dot}`} />
            <span className="font-mono text-[11px] whitespace-nowrap">{time}</span>
        </button>
    );
}

/* ── Main Panel ────────────────────────────────────────────────── */
export function AgentActivityPanel() {
    const containerRef = useRef<HTMLDivElement>(null);
    const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

    const { data: runs, isLoading: runsLoading } = useAgentRuns();
    const { data: runDetail } = useAgentRunDetail(selectedRunId);
    const triggerMutation = useAgentTrigger();
    const approveMutation = useAgentApprove();
    const rejectMutation = useAgentReject();

    const isRunning = runDetail?.status === 'running';

    // Auto-select first run
    useEffect(() => {
        if (runs?.length && !selectedRunId) setSelectedRunId(runs[0].id);
    }, [runs, selectedRunId]);

    // Auto-select newly triggered
    useEffect(() => {
        if (triggerMutation.data?.run_id) setSelectedRunId(triggerMutation.data.run_id);
    }, [triggerMutation.data]);

    // GSAP entrance
    useEffect(() => {
        if (!containerRef.current) return;
        const ctx = gsap.context(() => {
            gsap.fromTo(
                ".agent-stagger",
                { y: 30, opacity: 0 },
                {
                    y: 0, opacity: 1, stagger: 0.12, duration: 0.8, ease: "power3.out",
                    scrollTrigger: { trigger: containerRef.current, start: "top 85%" },
                }
            );
        }, containerRef);
        return () => ctx.revert();
    }, []);

    // Derive data
    const streamMessages: StreamMessage[] = runDetail?.trace_steps
        ? [...runDetail.trace_steps].map(s => traceToStream(s, runDetail.triggered_at)).reverse()
        : [];
    const listingCards = runDetail?.trace_steps ? extractListingCards(runDetail.trace_steps) : [];

    const handleTrigger = () => {
        triggerMutation.mutate(undefined, {
            onError: (err: any) => console.error('Agent trigger failed:', err),
        });
    };

    return (
        <div ref={containerRef} className="relative w-full rounded-[2rem] bg-canopy text-linen overflow-hidden shadow-sm">
            {/* Noise + gradient — identical to HeroPanel */}
            <div className="absolute inset-0 pointer-events-none opacity-[0.04] mix-blend-overlay z-0" style={{ backgroundImage: NOISE_BG }} />
            <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_80%_0%,rgba(61,107,82,0.4)_0%,transparent_50%)] pointer-events-none" />

            <div className="relative z-10 p-10">
                {/* ── Header ─────────────────────────────────────── */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
                    <h2 className="agent-stagger text-[3rem] leading-[1.1] tracking-tight font-serif italic text-linen">
                        Autonomous Agent
                        <span className="block text-xl mt-1 not-italic font-sans font-medium text-linen/60 tracking-normal">
                            AI-powered carbon credit acquisition
                        </span>
                    </h2>
                    <button
                        onClick={handleTrigger}
                        disabled={triggerMutation.isPending}
                        className="agent-stagger shrink-0 px-6 py-3 bg-linen text-canopy font-sans font-medium rounded-xl hover:bg-linen/90 transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm"
                    >
                        {triggerMutation.isPending ? (
                            <>
                                <span className="w-3.5 h-3.5 border-2 border-canopy/30 border-t-canopy rounded-full animate-spin" />
                                Running...
                            </>
                        ) : 'Run Agent Now'}
                    </button>
                </div>

                {/* ── Run pills ──────────────────────────────────── */}
                {runs && runs.length > 0 && (
                    <div className="agent-stagger flex items-center gap-2 overflow-x-auto pb-2 mb-8 scrollbar-thin">
                        {runs.map(run => (
                            <RunPill key={run.id} run={run} isSelected={selectedRunId === run.id} onSelect={() => setSelectedRunId(run.id)} />
                        ))}
                    </div>
                )}

                {/* ── Content ────────────────────────────────────── */}
                {/* Loading */}
                {runsLoading && (
                    <div className="flex items-center justify-center py-16 gap-3">
                        <span className="w-4 h-4 border-2 border-linen/15 border-t-linen/50 rounded-full animate-spin" />
                        <span className="font-mono text-xs text-linen/25">Loading...</span>
                    </div>
                )}

                {/* Empty state */}
                {!runsLoading && (!runs || runs.length === 0) && (
                    <div className="agent-stagger flex flex-col md:flex-row gap-8">
                        <div className="flex-1">
                            <p className="font-serif italic text-2xl text-linen/25 leading-relaxed">
                                No runs yet. Click "Run Agent Now" to scan the marketplace.
                            </p>
                        </div>
                        <div className="w-full md:w-1/3 bg-slate/20 rounded-2xl p-6 border border-linen/5 backdrop-blur-sm">
                            <div className="flex items-center gap-2 mb-4">
                                <div className="w-2 h-2 rounded-full bg-linen/20" />
                                <span className="text-xs font-sans font-medium text-linen/30 uppercase tracking-wider">Agent Idle</span>
                            </div>
                            <div className="font-mono text-sm text-linen/20 min-h-[3rem]">
                                Waiting for trigger...
                                <span className="inline-block w-2 h-4 bg-linen/20 align-middle ml-1 animate-pulse" />
                            </div>
                        </div>
                    </div>
                )}

                {/* Active run */}
                {runDetail && (
                    <div className="agent-stagger flex flex-col lg:flex-row gap-8">

                        {/* ── Left: Stream feed (AgentStreamTile style) ── */}
                        <div className="flex-1 bg-slate/30 rounded-2xl border border-linen/5 backdrop-blur-sm overflow-hidden flex flex-col">
                            {/* Feed header */}
                            <div className="flex items-center justify-between px-6 py-4 border-b border-linen/5">
                                <h3 className="font-sans font-semibold text-sm tracking-tight text-linen/90">Agent Stream</h3>
                                {isRunning ? (
                                    <div className="flex items-center gap-2 bg-ember/20 px-2.5 py-1 rounded-full border border-ember/30">
                                        <div className="w-1.5 h-1.5 rounded-full bg-ember animate-ping" />
                                        <span className="font-mono text-[10px] uppercase font-semibold text-ember tracking-wider">Live</span>
                                    </div>
                                ) : runDetail.status === 'completed' ? (
                                    <div className="flex items-center gap-2 bg-emerald-500/15 px-2.5 py-1 rounded-full border border-emerald-500/20">
                                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                                        <span className="font-mono text-[10px] uppercase font-semibold text-emerald-300 tracking-wider">Complete</span>
                                    </div>
                                ) : runDetail.status === 'awaiting_approval' ? (
                                    <div className="flex items-center gap-2 bg-amber-500/15 px-2.5 py-1 rounded-full border border-amber-500/20">
                                        <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                                        <span className="font-mono text-[10px] uppercase font-semibold text-amber-300 tracking-wider">Approval</span>
                                    </div>
                                ) : runDetail.status === 'failed' ? (
                                    <div className="flex items-center gap-2 bg-red-500/15 px-2.5 py-1 rounded-full border border-red-500/20">
                                        <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
                                        <span className="font-mono text-[10px] uppercase font-semibold text-red-300 tracking-wider">Error</span>
                                    </div>
                                ) : null}
                            </div>

                            {/* Feed body */}
                            <div className="flex-1 px-6 py-5 overflow-y-auto max-h-[380px]">
                                {/* Thinking spinner while running with no steps */}
                                {isRunning && streamMessages.length === 0 && (
                                    <div className="flex flex-col items-center justify-center py-12 gap-5">
                                        <div className="relative w-20 h-20">
                                            <div className="absolute inset-0 border border-linen/10 rounded-full animate-spin" style={{ animationDuration: '12s' }} />
                                            <div className="absolute inset-3 border border-linen/15 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '8s' }} />
                                            <div className="absolute inset-6 border-[1.5px] border-ember/30 rounded-full animate-pulse" />
                                            <div className="absolute inset-0 flex items-center justify-center">
                                                <div className="w-3 h-3 rounded-full bg-ember/60 animate-ping" />
                                            </div>
                                        </div>
                                        <span className="font-mono text-xs text-linen/25">Initializing agent...</span>
                                    </div>
                                )}

                                {/* Stream messages */}
                                {streamMessages.length > 0 && (
                                    <div className="flex flex-col gap-4">
                                        {streamMessages.map((msg, i) => (
                                            <div
                                                key={`${msg.time}-${i}`}
                                                className="flex flex-col text-sm font-mono animate-in slide-in-from-top-2 fade-in duration-500 ease-out"
                                                style={{ opacity: Math.max(0.25, 1 - (i * 0.12)) }}
                                            >
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="text-[10px] text-linen/30">{msg.time}</span>
                                                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-[4px] uppercase ${getTagStyle(msg.tag)}`}>
                                                        {msg.tag}
                                                    </span>
                                                </div>
                                                <p className="text-xs leading-relaxed text-linen/75">{msg.text}</p>
                                                {msg.detail && (
                                                    <p className="text-[11px] leading-relaxed text-linen/40 mt-1 pl-2 border-l border-linen/10">{msg.detail}</p>
                                                )}
                                            </div>
                                        ))}

                                        {isRunning && (
                                            <div className="flex items-center gap-2 pt-1">
                                                <div className="flex items-center gap-1">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-ember/50 animate-bounce" style={{ animationDelay: '0ms', animationDuration: '1.4s' }} />
                                                    <div className="w-1.5 h-1.5 rounded-full bg-ember/50 animate-bounce" style={{ animationDelay: '200ms', animationDuration: '1.4s' }} />
                                                    <div className="w-1.5 h-1.5 rounded-full bg-ember/50 animate-bounce" style={{ animationDelay: '400ms', animationDuration: '1.4s' }} />
                                                </div>
                                                <span className="font-mono text-[10px] text-linen/20">Processing...</span>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* No run selected */}
                                {!isRunning && streamMessages.length === 0 && (
                                    <div className="flex items-center justify-center py-12">
                                        <div className="font-mono text-sm text-linen/15 text-center">
                                            Waiting for next run...
                                            <span className="inline-block w-2 h-4 bg-linen/15 align-middle ml-1 animate-pulse" />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* ── Right: Market Scanner + Actions ─────────── */}
                        <div className="w-full lg:w-[340px] shrink-0 flex flex-col gap-5">
                            {/* Listing card shuffler (CreditShufflerTile style) */}
                            <div className="bg-white/[0.06] rounded-2xl p-5 border border-linen/5 backdrop-blur-sm">
                                <div className="flex items-center justify-between mb-5">
                                    <h3 className="font-sans font-semibold text-sm text-linen/90 tracking-tight">Market Scanner</h3>
                                    <span className="font-mono text-[10px] uppercase tracking-wider text-linen/30 bg-linen/5 px-2 py-1 rounded-md">
                                        {listingCards.length > 0 ? `${listingCards.length} found` : 'Scanning'}
                                    </span>
                                </div>

                                {listingCards.length > 0 ? (
                                    <ListingShuffler cards={listingCards} />
                                ) : (
                                    /* Placeholder cards while scanning */
                                    <div className="relative h-[140px]">
                                        {[0, 1, 2].map(i => (
                                            <div
                                                key={i}
                                                className="absolute w-full rounded-xl p-4 border border-linen/5 bg-linen/[0.03] backdrop-blur-sm"
                                                style={{
                                                    transform: `translateY(${i * 10}px) scale(${1 - i * 0.04})`,
                                                    opacity: 0.4 - (i * 0.12),
                                                    zIndex: 10 - i,
                                                }}
                                            >
                                                <div className="flex justify-between items-start mb-3">
                                                    <div className="h-3 w-32 bg-linen/8 rounded animate-pulse" />
                                                    <div className="h-4 w-14 bg-linen/8 rounded animate-pulse" />
                                                </div>
                                                <div className="h-2.5 w-20 bg-linen/5 rounded-full animate-pulse" />
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Agent status + rationale (HeroPanel feed style) */}
                            <div className="bg-slate/20 rounded-2xl p-6 border border-linen/5 backdrop-blur-sm">
                                <div className="flex items-center gap-2 mb-4">
                                    <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-ember animate-pulse ring-2 ring-ember/30' : 'bg-linen/20'}`} />
                                    <span className="text-xs font-sans font-medium text-linen/70 uppercase tracking-wider">
                                        {isRunning ? 'Agent Active' : 'Agent Idle'}
                                    </span>
                                </div>
                                <div className="font-mono text-sm leading-relaxed text-linen/90 min-h-[3.5rem]">
                                    {isRunning ? (
                                        <>
                                            Scanning marketplace for optimal credits...
                                            <span className="inline-block w-2 h-4 bg-ember align-middle ml-1 animate-pulse" />
                                        </>
                                    ) : runDetail.selection_rationale ? (
                                        runDetail.selection_rationale.slice(0, 160) + (runDetail.selection_rationale.length > 160 ? '...' : '')
                                    ) : runDetail.status === 'failed' ? (
                                        <span className="text-red-300/60">Run encountered an error.</span>
                                    ) : (
                                        <>
                                            Awaiting next scan cycle...
                                            <span className="inline-block w-2 h-4 bg-linen/20 align-middle ml-1 animate-pulse" />
                                        </>
                                    )}
                                </div>
                            </div>

                            {/* Stat pills */}
                            <div className="flex flex-wrap gap-2">
                                {runDetail.trace_steps && runDetail.trace_steps.length > 0 && (
                                    <div className="font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                                        <span className="opacity-60">Steps</span>
                                        <span className="font-medium text-linen">{runDetail.trace_steps.length}</span>
                                    </div>
                                )}
                                {runDetail.listings_shortlisted && runDetail.listings_shortlisted.length > 0 && (
                                    <div className="font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                                        <span className="opacity-60">Evaluated</span>
                                        <span className="font-medium text-linen">{runDetail.listings_shortlisted.length}</span>
                                    </div>
                                )}
                                {runDetail.action_taken && (
                                    <div className="font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                                        <span className="opacity-60">Result</span>
                                        <span className="font-medium text-linen capitalize">{runDetail.action_taken}</span>
                                    </div>
                                )}
                            </div>

                            {/* Order confirmation with payment info */}
                            {runDetail.order_id && (() => {
                                const payStep = runDetail.trace_steps?.find(s => s.label === 'Created order and executed payment');
                                const payOut = payStep?.output && typeof payStep.output === 'object' ? payStep.output : null;
                                const isStripe = payOut?.payment_mode === 'stripe';
                                return (
                                    <div className={`font-mono text-xs px-4 py-3 rounded-xl border flex flex-col gap-1.5 ${
                                        isStripe ? 'bg-violet-500/10 border-violet-500/15' : 'bg-emerald-500/10 border-emerald-500/15'
                                    }`}>
                                        <div className="flex items-center gap-2">
                                            <div className={`w-2 h-2 rounded-full ${isStripe ? 'bg-violet-400' : 'bg-emerald-400'}`} />
                                            <span className={isStripe ? 'text-violet-300/80' : 'text-emerald-300/80'}>
                                                Order placed {isStripe ? 'via Stripe' : 'successfully'}
                                            </span>
                                        </div>
                                        {isStripe && payOut?.payment_intent_id && (
                                            <span className="text-[10px] text-violet-300/40 pl-4 truncate">{payOut.payment_intent_id}</span>
                                        )}
                                    </div>
                                );
                            })()}

                            {/* Error */}
                            {runDetail.status === 'failed' && runDetail.error_message && (
                                <div className="bg-red-500/10 rounded-xl px-4 py-3 border border-red-500/15">
                                    <p className="font-mono text-[11px] text-red-300/70 leading-relaxed">{runDetail.error_message.slice(0, 200)}</p>
                                </div>
                            )}

                            {/* Approve/Reject */}
                            {runDetail.status === 'awaiting_approval' && (
                                <div className="flex flex-col gap-2">
                                    <button
                                        onClick={() => approveMutation.mutate(runDetail.id)}
                                        disabled={approveMutation.isPending}
                                        className="w-full py-3 bg-linen text-canopy font-sans font-medium rounded-xl hover:bg-linen/90 transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
                                    >
                                        {approveMutation.isPending ? (
                                            <><span className="w-3 h-3 border-2 border-canopy/30 border-t-canopy rounded-full animate-spin" />Approving...</>
                                        ) : 'Approve Purchase'}
                                    </button>
                                    <button
                                        onClick={() => rejectMutation.mutate(runDetail.id)}
                                        disabled={rejectMutation.isPending}
                                        className="w-full py-3 bg-transparent text-linen/50 font-sans font-medium rounded-xl border border-linen/10 hover:bg-linen/5 transition-colors disabled:opacity-40"
                                    >
                                        {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
