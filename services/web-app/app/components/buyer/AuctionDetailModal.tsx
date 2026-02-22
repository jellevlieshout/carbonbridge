import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import {
    Gavel, Users, Timer, TrendingUp, Zap, Bot, User,
    MapPin, CalendarIcon, ShieldCheck, ArrowRight,
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '~/modules/shared/ui/dialog';
import { Badge } from '~/modules/shared/ui/badge';
import { Button } from '~/modules/shared/ui/button';
import { Input } from '~/modules/shared/ui/input';
import { Label } from '~/modules/shared/ui/label';
import { useAuction, useAuctionBids, usePlaceBid, useBuyNow } from '~/modules/shared/queries/useAuctions';
import type { Auction, Bid } from '@clients/api/auctions';

// ---------------------------------------------------------------------------
// Countdown hook
// ---------------------------------------------------------------------------

function useCountdown(targetDate: string | null) {
    const [remaining, setRemaining] = useState({ d: 0, h: 0, m: 0, s: 0, total: 0 });

    useEffect(() => {
        if (!targetDate) return;

        const tick = () => {
            const diff = Math.max(0, new Date(targetDate).getTime() - Date.now());
            const d = Math.floor(diff / 86_400_000);
            const h = Math.floor((diff % 86_400_000) / 3_600_000);
            const m = Math.floor((diff % 3_600_000) / 60_000);
            const s = Math.floor((diff % 60_000) / 1000);
            setRemaining({ d, h, m, s, total: diff });
        };

        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, [targetDate]);

    return remaining;
}

// ---------------------------------------------------------------------------
// Countdown display
// ---------------------------------------------------------------------------

function CountdownDisplay({ auction }: { auction: Auction }) {
    const remaining = useCountdown(auction.effective_ends_at);
    const isUrgent = remaining.total > 0 && remaining.total < 5 * 60 * 1000;

    if (auction.status !== 'active') return null;

    return (
        <div className="flex items-center gap-2">
            <Timer className={`w-4 h-4 ${isUrgent ? 'text-red-500 animate-pulse' : 'text-muted-foreground'}`} />
            <span className={`font-mono text-lg font-semibold tabular-nums ${isUrgent ? 'text-red-600' : 'text-foreground'}`}>
                {remaining.d > 0 && `${remaining.d}d `}
                {String(remaining.h).padStart(2, '0')}:{String(remaining.m).padStart(2, '0')}:{String(remaining.s).padStart(2, '0')}
            </span>
            {auction.extensions_count > 0 && (
                <Badge variant="outline" className="text-[9px] py-0">+{auction.extensions_count} ext</Badge>
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Bid history list
// ---------------------------------------------------------------------------

function BidHistory({ bids, isLoading }: { bids: Bid[]; isLoading: boolean }) {
    if (isLoading) {
        return (
            <div className="space-y-2">
                {[0, 1, 2].map(i => (
                    <div key={i} className="h-12 bg-muted/30 rounded-lg animate-pulse" style={{ opacity: 1 - i * 0.3 }} />
                ))}
            </div>
        );
    }

    if (!bids.length) {
        return (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <Gavel className="w-8 h-8 mb-2 opacity-20" />
                <p className="text-sm font-medium">No bids yet</p>
                <p className="text-xs opacity-60">Be the first to bid</p>
            </div>
        );
    }

    return (
        <div className="space-y-1.5 max-h-[200px] overflow-y-auto pr-1">
            {bids.map((bid, i) => {
                const isTop = i === 0;
                const statusBg = bid.status === 'won' ? 'bg-emerald-50 border-emerald-200'
                    : bid.status === 'buy_now' ? 'bg-violet-50 border-violet-200'
                    : bid.status === 'active' && isTop ? 'bg-amber-50 border-amber-200'
                    : 'bg-muted/20 border-border/30';

                return (
                    <div key={bid.id} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border text-sm ${statusBg}`}>
                        <div className="flex items-center gap-1.5 shrink-0">
                            {bid.placed_by === 'agent' ? (
                                <Bot className="w-3.5 h-3.5 text-violet-500" />
                            ) : (
                                <User className="w-3.5 h-3.5 text-muted-foreground" />
                            )}
                        </div>
                        <span className={`font-mono font-semibold ${isTop ? 'text-foreground' : 'text-muted-foreground'}`}>
                            €{bid.amount_per_tonne_eur.toFixed(2)}/t
                        </span>
                        <span className="text-[11px] text-muted-foreground flex-1 text-right">
                            {bid.placed_at ? new Date(bid.placed_at).toLocaleString('en-GB', {
                                day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                            }) : ''}
                        </span>
                        {bid.is_buy_now && <Badge variant="secondary" className="text-[9px] bg-violet-100 text-violet-700 py-0">Buy Now</Badge>}
                        {bid.status === 'won' && <Badge variant="secondary" className="text-[9px] bg-emerald-100 text-emerald-700 py-0">Won</Badge>}
                        {isTop && bid.status === 'active' && <Badge variant="secondary" className="text-[9px] bg-amber-100 text-amber-700 py-0">Leading</Badge>}
                    </div>
                );
            })}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

interface AuctionDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    auctionId: string;
}

export function AuctionDetailModal({ isOpen, onClose, auctionId }: AuctionDetailModalProps) {
    const { data: auction, isLoading } = useAuction(isOpen ? auctionId : null);
    const { data: bids, isLoading: bidsLoading } = useAuctionBids(isOpen ? auctionId : null);

    const [bidAmount, setBidAmount] = useState('');
    const placeBidMutation = usePlaceBid();
    const buyNowMutation = useBuyNow();

    // Reset bid input when modal opens
    useEffect(() => {
        if (isOpen) setBidAmount('');
    }, [isOpen]);

    // SSE in last 5 minutes
    useEffect(() => {
        if (!auction || auction.status !== 'active' || !auction.effective_ends_at) return;
        const remaining = new Date(auction.effective_ends_at).getTime() - Date.now();
        if (remaining > 5 * 60 * 1000 || remaining <= 0) return;

        const apiBase = import.meta.env.VITE_API_URL || '';
        const es = new EventSource(`${apiBase}/auctions/${auction.id}/stream`);
        es.onerror = () => es.close();
        return () => es.close();
    }, [auction?.id, auction?.status, auction?.effective_ends_at]);

    if (isLoading || !auction) {
        return (
            <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
                <DialogContent className="sm:max-w-[540px]">
                    <div className="flex items-center justify-center py-12">
                        <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                    </div>
                </DialogContent>
            </Dialog>
        );
    }

    const isActive = auction.status === 'active';
    const minBid = (auction.current_high_bid_eur ?? auction.config.starting_price_per_tonne_eur)
        + (auction.current_high_bid_eur ? auction.config.min_bid_increment_eur : 0);
    const bidValue = parseFloat(bidAmount);
    const isValidBid = !isNaN(bidValue) && bidValue >= minBid;
    const totalCost = isValidBid ? bidValue * auction.quantity_tonnes : 0;
    const sortedBids = bids ? [...bids].sort((a, b) => b.amount_per_tonne_eur - a.amount_per_tonne_eur) : [];

    const handlePlaceBid = () => {
        if (!isValidBid) return;
        placeBidMutation.mutate(
            { auctionId: auction.id, amount: bidValue },
            {
                onSuccess: () => {
                    toast.success(`Bid of €${bidValue.toFixed(2)}/t placed`);
                    setBidAmount('');
                },
                onError: (err: any) => toast.error(err.message || 'Failed to place bid'),
            },
        );
    };

    const handleBuyNow = () => {
        buyNowMutation.mutate(auction.id, {
            onSuccess: () => {
                toast.success('Buy-now executed!');
                onClose();
            },
            onError: (err: any) => toast.error(err.message || 'Buy-now failed'),
        });
    };

    const statusConfig: Record<string, { label: string; color: string }> = {
        active: { label: 'Live', color: 'bg-emerald-500 text-white' },
        scheduled: { label: 'Scheduled', color: 'bg-sky-100 text-sky-700' },
        ended: { label: 'Ended', color: 'bg-gray-100 text-gray-600' },
        settled: { label: 'Settled', color: 'bg-emerald-100 text-emerald-700' },
        failed: { label: 'Failed', color: 'bg-red-100 text-red-700' },
        cancelled: { label: 'Cancelled', color: 'bg-gray-100 text-gray-600' },
        bought_now: { label: 'Sold', color: 'bg-violet-100 text-violet-700' },
    };
    const st = statusConfig[auction.status] || { label: auction.status, color: 'bg-gray-100 text-gray-600' };

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <DialogContent className="sm:max-w-[540px] max-h-[90vh] overflow-y-auto p-0 gap-0">
                {/* Header section */}
                <div className="px-6 pt-6 pb-4">
                    <DialogHeader>
                        <div className="flex items-center gap-2.5 mb-1">
                            <Badge className={`text-[10px] font-semibold px-2 py-0.5 border-0 ${st.color}`}>
                                {isActive && <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse mr-1 inline-block" />}
                                {st.label}
                            </Badge>
                            {auction.created_by === 'agent' && (
                                <Badge variant="outline" className="text-[10px] text-violet-600 border-violet-200 gap-0.5">
                                    <Bot className="w-2.5 h-2.5" /> Agent
                                </Badge>
                            )}
                        </div>
                        <DialogTitle className="text-xl font-bold">{auction.project_name || 'Auction'}</DialogTitle>
                        <DialogDescription asChild>
                            <div className="flex items-center gap-3 mt-1.5 text-muted-foreground">
                                {auction.project_type && (
                                    <span className="text-xs capitalize">{auction.project_type.replace(/_/g, ' ')}</span>
                                )}
                                {auction.project_country && (
                                    <span className="flex items-center gap-1 text-xs">
                                        <MapPin className="w-3 h-3" /> {auction.project_country}
                                    </span>
                                )}
                                {auction.vintage_year && (
                                    <span className="flex items-center gap-1 text-xs">
                                        <CalendarIcon className="w-3 h-3" /> {auction.vintage_year}
                                    </span>
                                )}
                                {auction.verification_status === 'verified' && (
                                    <span className="flex items-center gap-1 text-xs text-emerald-600">
                                        <ShieldCheck className="w-3 h-3" /> Verified
                                    </span>
                                )}
                            </div>
                        </DialogDescription>
                    </DialogHeader>
                </div>

                {/* Current bid + countdown panel */}
                <div className="mx-6 rounded-xl bg-muted/40 border p-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium mb-1">
                                {auction.current_high_bid_eur ? 'Current Bid' : 'Starting Price'}
                            </p>
                            <p className="text-3xl font-bold tracking-tight text-foreground">
                                €{(auction.current_high_bid_eur ?? auction.config.starting_price_per_tonne_eur).toFixed(2)}
                                <span className="text-sm font-normal text-muted-foreground ml-0.5">/t</span>
                            </p>
                        </div>
                        <div className="text-right">
                            {isActive ? (
                                <div>
                                    <p className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium mb-1">Time Left</p>
                                    <CountdownDisplay auction={auction} />
                                </div>
                            ) : (
                                <div>
                                    <p className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium mb-1">Status</p>
                                    <p className="text-sm font-medium">{st.label}</p>
                                </div>
                            )}
                        </div>
                    </div>
                    <div className="flex items-center gap-4 mt-3 pt-3 border-t text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                            <Users className="w-3.5 h-3.5" /> {auction.bid_count} bid{auction.bid_count !== 1 ? 's' : ''}
                        </span>
                        <span>{auction.quantity_tonnes.toLocaleString()} tonnes</span>
                        {auction.config.buy_now_price_per_tonne_eur && (
                            <span className="flex items-center gap-1 text-violet-600 font-medium ml-auto">
                                <Zap className="w-3.5 h-3.5" />
                                Buy Now €{auction.config.buy_now_price_per_tonne_eur.toFixed(2)}/t
                            </span>
                        )}
                    </div>
                </div>

                {/* Place bid section */}
                {isActive && (
                    <div className="mx-6 mt-4 space-y-3">
                        <div>
                            <Label className="text-xs text-muted-foreground font-medium">
                                Your Bid <span className="text-muted-foreground/60">(min €{minBid.toFixed(2)}/t)</span>
                            </Label>
                            <div className="flex gap-2 mt-1.5">
                                <div className="relative flex-1">
                                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm font-medium">€</span>
                                    <Input
                                        type="number"
                                        step="0.01"
                                        min={minBid}
                                        value={bidAmount}
                                        onChange={(e) => setBidAmount(e.target.value)}
                                        placeholder={minBid.toFixed(2)}
                                        className="pl-8 font-mono"
                                    />
                                </div>
                                <Button
                                    disabled={!isValidBid || placeBidMutation.isPending}
                                    onClick={handlePlaceBid}
                                    className="shrink-0 gap-2"
                                >
                                    {placeBidMutation.isPending ? (
                                        <>
                                            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                            Placing...
                                        </>
                                    ) : (
                                        <>
                                            <Gavel className="w-4 h-4" /> Place Bid
                                        </>
                                    )}
                                </Button>
                            </div>
                            {isValidBid && (
                                <p className="text-[11px] text-muted-foreground mt-1.5 flex items-center gap-1">
                                    Total: <span className="font-semibold text-foreground">
                                        €{totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </span>
                                    <ArrowRight className="w-3 h-3" />
                                    {auction.quantity_tonnes.toLocaleString()} tonnes
                                </p>
                            )}
                        </div>

                        {auction.config.buy_now_price_per_tonne_eur && (
                            <>
                                <div className="relative flex items-center gap-3">
                                    <div className="flex-1 h-px bg-border" />
                                    <span className="text-xs text-muted-foreground">or</span>
                                    <div className="flex-1 h-px bg-border" />
                                </div>
                                <Button
                                    variant="outline"
                                    className="w-full border-violet-200 text-violet-700 hover:bg-violet-50 gap-2"
                                    disabled={buyNowMutation.isPending}
                                    onClick={handleBuyNow}
                                >
                                    {buyNowMutation.isPending ? (
                                        <>
                                            <span className="w-4 h-4 border-2 border-violet-300 border-t-violet-600 rounded-full animate-spin" />
                                            Processing...
                                        </>
                                    ) : (
                                        <>
                                            <Zap className="w-4 h-4" />
                                            Buy Now at €{auction.config.buy_now_price_per_tonne_eur.toFixed(2)}/t
                                        </>
                                    )}
                                </Button>
                            </>
                        )}
                    </div>
                )}

                {/* Not active message */}
                {!isActive && (
                    <div className="mx-6 mt-4 py-4 text-center text-sm text-muted-foreground bg-muted/30 rounded-lg">
                        This auction is no longer accepting bids.
                    </div>
                )}

                {/* Bid history */}
                <div className="mx-6 mt-4 pt-4 border-t">
                    <div className="flex items-center justify-between mb-3">
                        <h4 className="text-sm font-semibold flex items-center gap-1.5">
                            <TrendingUp className="w-4 h-4 text-muted-foreground" /> Bid History
                        </h4>
                        <span className="text-[11px] text-muted-foreground font-mono">{sortedBids.length} total</span>
                    </div>
                    <BidHistory bids={sortedBids} isLoading={bidsLoading} />
                </div>

                {/* Auction details */}
                <div className="mx-6 mt-4 mb-6 pt-4 border-t">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Auction Details</h4>
                    <div className="grid grid-cols-2 gap-2">
                        <div className="flex items-center justify-between bg-muted/30 rounded-lg px-3 py-2">
                            <span className="text-xs text-muted-foreground">Starting</span>
                            <span className="text-sm font-mono font-medium">€{auction.config.starting_price_per_tonne_eur.toFixed(2)}/t</span>
                        </div>
                        <div className="flex items-center justify-between bg-muted/30 rounded-lg px-3 py-2">
                            <span className="text-xs text-muted-foreground">Increment</span>
                            <span className="text-sm font-mono font-medium">€{auction.config.min_bid_increment_eur.toFixed(2)}</span>
                        </div>
                        <div className="flex items-center justify-between bg-muted/30 rounded-lg px-3 py-2">
                            <span className="text-xs text-muted-foreground">Anti-snipe</span>
                            <span className="text-sm font-mono font-medium">{auction.config.auto_extend_minutes} min</span>
                        </div>
                        <div className="flex items-center justify-between bg-muted/30 rounded-lg px-3 py-2">
                            <span className="text-xs text-muted-foreground">Quantity</span>
                            <span className="text-sm font-mono font-medium">{auction.quantity_tonnes.toLocaleString()}t</span>
                        </div>
                    </div>

                    {/* Co-benefits */}
                    {auction.co_benefits && auction.co_benefits.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                            {auction.co_benefits.map((benefit, i) => (
                                <Badge key={i} variant="outline" className="text-[10px] font-normal text-muted-foreground capitalize">
                                    {benefit.replace(/_/g, ' ')}
                                </Badge>
                            ))}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
