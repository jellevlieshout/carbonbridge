import React, { useEffect, useRef, useState, useCallback } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Building2, ScanEye, BrainCircuit, BarChart3, Lightbulb, CircleCheck, Clock, ChevronDown } from 'lucide-react';
import { useAgentRuns, useAgentRunDetail, useSellerAdvisoryTrigger } from '../../modules/shared/queries/useAgentRuns';
import type { AgentRunSummary, TraceStep } from '@clients/api/agent';

gsap.registerPlugin(ScrollTrigger);

const NOISE_BG = "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")";

/* ── Transform trace steps into friendly stream cards ──────── */
type StreamIcon = 'building' | 'scan' | 'brain' | 'chart' | 'lightbulb' | 'done' | 'clock';
type StreamTone = 'neutral' | 'success' | 'info' | 'recommendation' | 'hold';

interface StreamCard {
    icon: StreamIcon;
    tone: StreamTone;
    title: string;
    body?: string;
    detail?: string;
    time: string;
}

function traceToCard(step: TraceStep, triggeredAt: string | null): StreamCard {
    const base = triggeredAt ? new Date(triggeredAt) : new Date();
    const offset = step.duration_ms || 0;
    const t = new Date(base.getTime() + offset);
    const time = t.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const out = step.output && typeof step.output === 'object' ? step.output : {};

    switch (step.label) {
        case 'Agent run initialized':
            return { icon: 'scan', tone: 'neutral', title: 'Portfolio Scan', body: 'Reviewing your listings and market position', time };
        case 'Loaded seller profile':
            return { icon: 'building', tone: 'info', title: out.company || 'Profile Loaded', body: 'Scanning active listings for optimization', time };
        case 'Starting Gemini listing analysis':
            return { icon: 'brain', tone: 'info', title: 'AI Market Comparison', body: 'Benchmarking against OffsetsDB data', time };
        case 'Gemini analysis complete':
            return {
                icon: 'chart', tone: 'info', title: 'Market Position Assessed',
                body: out.market_position ? `Position: ${out.market_position}` : 'Analysis complete',
                detail: out.recommendation_count ? `${out.recommendation_count} optimization${out.recommendation_count > 1 ? 's' : ''} identified` : undefined,
                time,
            };
        case 'Advisory recommendations generated':
            if (Array.isArray(out.recommendations) && out.recommendations.length > 0) {
                return { icon: 'lightbulb', tone: 'recommendation', title: `${out.recommendations.length} Optimizations`, body: out.recommendations[0].summary || 'Actionable tips ready', time };
            }
            return { icon: 'lightbulb', tone: 'recommendation', title: 'Tips Generated', body: 'Listing optimization strategies ready', time };
        case 'Advisory complete':
            return {
                icon: 'done', tone: 'success', title: 'Advisory Finished',
                body: out.overall_assessment ? String(out.overall_assessment) : 'All recommendations delivered',
                time,
            };
        default:
            return { icon: 'clock', tone: 'neutral', title: step.label, time };
    }
}

const SELLER_ICON_MAP: Record<StreamIcon, React.ComponentType<{ size?: number; strokeWidth?: number; className?: string }>> = {
    building: Building2,
    scan: ScanEye,
    brain: BrainCircuit,
    chart: BarChart3,
    lightbulb: Lightbulb,
    done: CircleCheck,
    clock: Clock,
};

function toneStyling(tone: StreamTone) {
    switch (tone) {
        case 'success': return { iconBg: 'bg-emerald-500/15', iconText: 'text-emerald-400', border: 'border-emerald-500/10' };
        case 'info': return { iconBg: 'bg-sky-500/15', iconText: 'text-sky-400', border: 'border-sky-500/10' };
        case 'recommendation': return { iconBg: 'bg-amber-500/15', iconText: 'text-amber-300', border: 'border-amber-500/10' };
        case 'hold': return { iconBg: 'bg-ember/10', iconText: 'text-ember', border: 'border-ember/10' };
        case 'neutral':
        default: return { iconBg: 'bg-linen/8', iconText: 'text-linen/50', border: 'border-linen/5' };
    }
}

/* ── Expandable text for long AI responses ─────────────────────── */
function ExpandableText({ text, className, threshold = 200 }: { text: string; className?: string; threshold?: number }) {
    const [expanded, setExpanded] = useState(false);
    const isLong = text.length > threshold;

    return (
        <div className={className}>
            <p className={`leading-relaxed ${!expanded && isLong ? 'line-clamp-3' : ''}`}>
                {text}
            </p>
            {isLong && (
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="flex items-center gap-1 mt-1.5 font-sans text-[10px] font-medium text-linen/40 hover:text-linen/60 transition-colors cursor-pointer"
                >
                    <ChevronDown size={10} className={`transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`} />
                    {expanded ? 'Show less' : 'Read more'}
                </button>
            )}
        </div>
    );
}

/* ── Extract recommendations from trace steps ─────────────────── */
interface Recommendation {
    listing_id: string;
    type: string;
    summary: string;
    details: string;
    suggested_price_eur: number | null;
}

function extractRecommendations(steps: TraceStep[]): Recommendation[] {
    for (const step of steps) {
        if (step.label === 'Advisory recommendations generated' && step.output?.recommendations) {
            return step.output.recommendations;
        }
    }
    return [];
}

function getRecTypeStyle(type: string): { bg: string; text: string; label: string } {
    switch (type) {
        case 'price_adjustment': return { bg: 'bg-amber-500/15', text: 'text-amber-300', label: 'Price' };
        case 'highlight_co_benefits': return { bg: 'bg-emerald-500/15', text: 'text-emerald-300', label: 'Co-Benefits' };
        case 'vintage_note': return { bg: 'bg-sky-500/15', text: 'text-sky-300', label: 'Vintage' };
        case 'competitive_strength': return { bg: 'bg-sage/15', text: 'text-sage', label: 'Strength' };
        default: return { bg: 'bg-linen/10', text: 'text-linen/60', label: 'Tip' };
    }
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
            className={`shrink-0 flex items-center gap-2 px-4 py-2 rounded-full border transition-all duration-300 cursor-pointer ${
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
export function SellerAdvisoryPanel() {
    const containerRef = useRef<HTMLDivElement>(null);
    const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

    const { data: runs, isLoading: runsLoading } = useAgentRuns('seller_advisory');
    const { data: runDetail } = useAgentRunDetail(selectedRunId);
    const triggerMutation = useSellerAdvisoryTrigger();

    const isRunning = runDetail?.status === 'running';
    const feedRef = useRef<HTMLDivElement>(null);
    const prevCardCountRef = useRef<number>(0);
    const animatedRunIdRef = useRef<string | null>(null);

    // Auto-select first run
    useEffect(() => {
        if (runs?.length && !selectedRunId) setSelectedRunId(runs[0].id);
    }, [runs, selectedRunId]);

    // GSAP entrance
    useEffect(() => {
        if (!containerRef.current) return;
        const ctx = gsap.context(() => {
            gsap.fromTo(
                ".advisory-stagger",
                { y: 30, opacity: 0 },
                {
                    y: 0, opacity: 1, stagger: 0.12, duration: 0.8, ease: "power3.out",
                    scrollTrigger: { trigger: containerRef.current, start: "top 85%" },
                }
            );
        }, containerRef);
        return () => ctx.revert();
    }, []);

    // GSAP stagger animation for stream cards
    const animateStreamCards = useCallback((animateAll = false) => {
        if (!feedRef.current) return;
        const cards = feedRef.current.querySelectorAll('.seller-stream-card');
        if (!cards.length) return;

        if (animateAll) {
            gsap.fromTo(Array.from(cards),
                { y: 24, opacity: 0, scale: 0.97 },
                {
                    y: 0, opacity: 1, scale: 1,
                    duration: 0.5, stagger: 0.08,
                    ease: "back.out(1.4)",
                    clearProps: "transform,opacity",
                }
            );
        } else {
            const newCards = Array.from(cards).slice(0, cards.length - prevCardCountRef.current);
            if (newCards.length === 0) {
                gsap.set(Array.from(cards), { opacity: 1 });
                return;
            }

            gsap.fromTo(newCards,
                { y: 24, opacity: 0, scale: 0.97 },
                {
                    y: 0, opacity: 1, scale: 1,
                    duration: 0.5, stagger: 0.08,
                    ease: "back.out(1.4)",
                    clearProps: "transform,opacity",
                }
            );
        }
    }, []);

    // Derive data
    const streamCards: StreamCard[] = runDetail?.trace_steps
        ? [...runDetail.trace_steps].map(s => traceToCard(s, runDetail.triggered_at)).reverse()
        : [];
    const recommendations = runDetail?.trace_steps ? extractRecommendations(runDetail.trace_steps) : [];

    // Reset animation state when switching runs
    useEffect(() => {
        if (selectedRunId && selectedRunId !== animatedRunIdRef.current) {
            prevCardCountRef.current = 0;
            animatedRunIdRef.current = selectedRunId;
        }
    }, [selectedRunId]);

    // Trigger animation when card count changes or run switches
    useEffect(() => {
        if (streamCards.length > 0) {
            const isNewRun = prevCardCountRef.current === 0;
            requestAnimationFrame(() => animateStreamCards(isNewRun));
        }
        prevCardCountRef.current = streamCards.length;
    }, [streamCards.length, animateStreamCards]);

    const handleTrigger = () => {
        triggerMutation.mutate(undefined, {
            onError: (err: any) => console.error('Seller advisory trigger failed:', err),
        });
    };

    return (
        <div ref={containerRef} className="relative w-full rounded-[2rem] bg-canopy text-linen overflow-hidden shadow-sm">
            {/* Noise + gradient */}
            <div className="absolute inset-0 pointer-events-none opacity-[0.04] mix-blend-overlay z-0" style={{ backgroundImage: NOISE_BG }} />
            <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_20%_100%,rgba(61,107,82,0.4)_0%,transparent_50%)] pointer-events-none" />

            <div className="relative z-10 p-10">
                {/* ── Header ─────────────────────────────────────── */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
                    <h2 className="advisory-stagger text-[3rem] leading-[1.1] tracking-tight font-serif italic text-linen">
                        Market Advisory
                        <span className="block text-xl mt-1 not-italic font-sans font-medium text-linen/60 tracking-normal">
                            AI-powered listing optimization
                        </span>
                    </h2>
                    <button
                        onClick={handleTrigger}
                        disabled={triggerMutation.isPending}
                        className="advisory-stagger shrink-0 px-6 py-3 bg-linen text-canopy font-sans font-medium rounded-xl hover:bg-linen/90 transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm cursor-pointer"
                    >
                        {triggerMutation.isPending ? (
                            <>
                                <span className="w-3.5 h-3.5 border-2 border-canopy/30 border-t-canopy rounded-full animate-spin" />
                                Analyzing...
                            </>
                        ) : 'Run Advisory'}
                    </button>
                </div>

                {/* ── Run pills ──────────────────────────────────── */}
                {runs && runs.length > 0 && (
                    <div className="advisory-stagger flex items-center gap-2 overflow-x-auto pb-2 mb-8 scrollbar-thin">
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
                    <div className="advisory-stagger flex flex-col md:flex-row gap-8">
                        <div className="flex-1">
                            <p className="font-serif italic text-2xl text-linen/25 leading-relaxed">
                                No advisory runs yet. Click "Run Advisory" to get AI-powered recommendations for your listings.
                            </p>
                        </div>
                        <div className="w-full md:w-1/3 bg-slate/20 rounded-2xl p-6 border border-linen/5 backdrop-blur-sm">
                            <div className="flex items-center gap-2 mb-4">
                                <div className="w-2 h-2 rounded-full bg-linen/20" />
                                <span className="text-xs font-sans font-medium text-linen/30 uppercase tracking-wider">Advisory Idle</span>
                            </div>
                            <div className="font-mono text-sm text-linen/20 min-h-[3rem]">
                                Ready to analyze your portfolio...
                                <span className="inline-block w-2 h-4 bg-linen/20 align-middle ml-1 animate-pulse" />
                            </div>
                        </div>
                    </div>
                )}

                {/* Active run */}
                {runDetail && (
                    <div className="advisory-stagger flex flex-col lg:flex-row gap-8">

                        {/* ── Left: Stream feed ──────────────────────── */}
                        <div className="flex-1 bg-slate/30 rounded-2xl border border-linen/5 backdrop-blur-sm overflow-hidden flex flex-col">
                            {/* Feed header */}
                            <div className="flex items-center justify-between px-6 py-4 border-b border-linen/5">
                                <h3 className="font-sans font-semibold text-sm tracking-tight text-linen/90">Advisory Stream</h3>
                                {isRunning ? (
                                    <div className="flex items-center gap-2 bg-ember/20 px-2.5 py-1 rounded-full border border-ember/30">
                                        <div className="w-1.5 h-1.5 rounded-full bg-ember animate-ping" />
                                        <span className="font-mono text-[10px] uppercase font-semibold text-ember tracking-wider">Analyzing</span>
                                    </div>
                                ) : runDetail.status === 'completed' ? (
                                    <div className="flex items-center gap-2 bg-emerald-500/15 px-2.5 py-1 rounded-full border border-emerald-500/20">
                                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                                        <span className="font-mono text-[10px] uppercase font-semibold text-emerald-300 tracking-wider">Complete</span>
                                    </div>
                                ) : runDetail.status === 'failed' ? (
                                    <div className="flex items-center gap-2 bg-red-500/15 px-2.5 py-1 rounded-full border border-red-500/20">
                                        <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
                                        <span className="font-mono text-[10px] uppercase font-semibold text-red-300 tracking-wider">Error</span>
                                    </div>
                                ) : null}
                            </div>

                            {/* Feed body */}
                            <div className="flex-1 px-5 py-5 overflow-y-auto max-h-[380px]">
                                {/* Thinking spinner while running */}
                                {isRunning && streamCards.length === 0 && (
                                    <div className="flex flex-col items-center justify-center py-12 gap-5">
                                        <div className="relative w-20 h-20">
                                            <div className="absolute inset-0 border border-linen/10 rounded-full animate-spin" style={{ animationDuration: '12s' }} />
                                            <div className="absolute inset-3 border border-linen/15 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '8s' }} />
                                            <div className="absolute inset-6 border-[1.5px] border-sky-400/30 rounded-full animate-pulse" />
                                            <div className="absolute inset-0 flex items-center justify-center">
                                                <div className="w-3 h-3 rounded-full bg-sky-400/60 animate-ping" />
                                            </div>
                                        </div>
                                        <span className="font-mono text-xs text-linen/25">Analyzing market data...</span>
                                    </div>
                                )}

                                {/* Stream cards */}
                                {streamCards.length > 0 && (
                                    <div ref={feedRef} className="flex flex-col gap-3">
                                        {streamCards.map((card, i) => {
                                            const styles = toneStyling(card.tone);
                                            const Icon = SELLER_ICON_MAP[card.icon];
                                            return (
                                                <div
                                                    key={`${card.time}-${i}`}
                                                    className={`seller-stream-card flex gap-3 p-3.5 rounded-xl border backdrop-blur-sm bg-linen/[0.03] ${styles.border}`}
                                                >
                                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${styles.iconBg}`}>
                                                        <Icon size={15} strokeWidth={2} className={styles.iconText} />
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center justify-between gap-2 mb-0.5">
                                                            <span className="font-sans font-medium text-sm text-linen/90 truncate">{card.title}</span>
                                                            <span className="font-mono text-[10px] text-linen/25 shrink-0">{card.time}</span>
                                                        </div>
                                                        {card.body && (
                                                            <ExpandableText text={card.body} className="font-sans text-xs text-linen/55" />
                                                        )}
                                                        {card.detail && (
                                                            <ExpandableText text={card.detail} className="font-mono text-[10px] text-linen/30 mt-1.5" />
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}

                                        {isRunning && (
                                            <div className="flex items-center gap-2 pt-2 px-3">
                                                <div className="flex items-center gap-1">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-sky-400/50 animate-bounce" style={{ animationDelay: '0ms', animationDuration: '1.4s' }} />
                                                    <div className="w-1.5 h-1.5 rounded-full bg-sky-400/50 animate-bounce" style={{ animationDelay: '200ms', animationDuration: '1.4s' }} />
                                                    <div className="w-1.5 h-1.5 rounded-full bg-sky-400/50 animate-bounce" style={{ animationDelay: '400ms', animationDuration: '1.4s' }} />
                                                </div>
                                                <span className="font-mono text-[10px] text-linen/20">Analyzing...</span>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* No run selected */}
                                {!isRunning && streamCards.length === 0 && (
                                    <div className="flex items-center justify-center py-12">
                                        <div className="font-mono text-sm text-linen/15 text-center">
                                            Ready for analysis...
                                            <span className="inline-block w-2 h-4 bg-linen/15 align-middle ml-1 animate-pulse" />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* ── Right: Recommendations + Status ─────────── */}
                        <div className="w-full lg:w-[380px] shrink-0 flex flex-col gap-5">
                            {/* Recommendations cards */}
                            {recommendations.length > 0 ? (
                                <div className="bg-white/[0.06] rounded-2xl p-5 border border-linen/5 backdrop-blur-sm">
                                    <div className="flex items-center justify-between mb-5">
                                        <h3 className="font-sans font-semibold text-sm text-linen/90 tracking-tight">Recommendations</h3>
                                        <span className="font-mono text-[10px] uppercase tracking-wider text-linen/30 bg-linen/5 px-2 py-1 rounded-md">
                                            {recommendations.length} tips
                                        </span>
                                    </div>
                                    <div className="flex flex-col gap-3 max-h-[300px] overflow-y-auto">
                                        {recommendations.map((rec, i) => {
                                            const style = getRecTypeStyle(rec.type);
                                            return (
                                                <div
                                                    key={`${rec.listing_id}-${i}`}
                                                    className="rounded-xl p-4 border border-linen/5 bg-linen/[0.03] backdrop-blur-sm"
                                                >
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-[4px] uppercase ${style.bg} ${style.text}`}>
                                                            {style.label}
                                                        </span>
                                                        {rec.suggested_price_eur && (
                                                            <span className="font-mono text-[10px] text-emerald-300/60 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                                                                €{rec.suggested_price_eur.toFixed(2)}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="font-sans text-xs text-linen/80 leading-relaxed">{rec.summary}</p>
                                                    <ExpandableText text={rec.details} className="font-mono text-[10px] text-linen/40 mt-2" threshold={150} />
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            ) : (
                                /* Placeholder while scanning */
                                <div className="bg-white/[0.06] rounded-2xl p-5 border border-linen/5 backdrop-blur-sm">
                                    <div className="flex items-center justify-between mb-5">
                                        <h3 className="font-sans font-semibold text-sm text-linen/90 tracking-tight">Recommendations</h3>
                                        <span className="font-mono text-[10px] uppercase tracking-wider text-linen/30 bg-linen/5 px-2 py-1 rounded-md">
                                            {isRunning ? 'Scanning' : 'Pending'}
                                        </span>
                                    </div>
                                    <div className="flex flex-col gap-3">
                                        {[0, 1, 2].map(i => (
                                            <div
                                                key={i}
                                                className="rounded-xl p-4 border border-linen/5 bg-linen/[0.02]"
                                                style={{ opacity: 0.5 - (i * 0.15) }}
                                            >
                                                <div className="h-3 w-16 bg-linen/8 rounded mb-3 animate-pulse" />
                                                <div className="h-2.5 w-full bg-linen/5 rounded animate-pulse mb-2" />
                                                <div className="h-2.5 w-3/4 bg-linen/3 rounded animate-pulse" />
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Advisory status card */}
                            <div className="bg-slate/20 rounded-2xl p-6 border border-linen/5 backdrop-blur-sm">
                                <div className="flex items-center gap-2 mb-4">
                                    <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-sky-400 animate-pulse ring-2 ring-sky-400/30' : 'bg-linen/20'}`} />
                                    <span className="text-xs font-sans font-medium text-linen/70 uppercase tracking-wider">
                                        {isRunning ? 'Analyzing' : 'Advisory Status'}
                                    </span>
                                </div>
                                <div className="font-mono text-sm leading-relaxed text-linen/90 min-h-[3.5rem]">
                                    {isRunning ? (
                                        <>
                                            Comparing your listings against market benchmarks...
                                            <span className="inline-block w-2 h-4 bg-sky-400 align-middle ml-1 animate-pulse" />
                                        </>
                                    ) : runDetail.selection_rationale ? (
                                        <ExpandableText text={runDetail.selection_rationale} className="font-mono text-sm text-linen/90" threshold={160} />
                                    ) : runDetail.status === 'failed' ? (
                                        <span className="text-red-300/60">Advisory run encountered an error.</span>
                                    ) : (
                                        <>
                                            Ready for next analysis...
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
                                        <span className="opacity-60">Listings Analyzed</span>
                                        <span className="font-medium text-linen">{runDetail.listings_shortlisted.length}</span>
                                    </div>
                                )}
                                {runDetail.action_taken && (
                                    <div className="font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                                        <span className="opacity-60">Result</span>
                                        <span className="font-medium text-linen capitalize">{runDetail.action_taken.replace('_', ' ')}</span>
                                    </div>
                                )}
                            </div>

                            {/* Error */}
                            {runDetail.status === 'failed' && runDetail.error_message && (
                                <div className="bg-red-500/10 rounded-xl px-4 py-3 border border-red-500/15">
                                    <p className="font-mono text-[11px] text-red-300/70 leading-relaxed">{runDetail.error_message.slice(0, 200)}</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
