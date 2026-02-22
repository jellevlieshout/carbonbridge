import React, { useState, useEffect } from "react";
import { useListings } from "~/modules/shared/queries/useListings";
import { useAuctions } from "~/modules/shared/queries/useAuctions";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "~/modules/shared/ui/card";
import { Badge } from "~/modules/shared/ui/badge";
import { Button } from "~/modules/shared/ui/button";
import { MapPin, Leaf, CalendarIcon, Gavel, Timer, Users, Zap, Bot } from "lucide-react";
import { CheckoutModal } from "~/components/buyer/CheckoutModal";
import { AuctionDetailModal } from "~/components/buyer/AuctionDetailModal";
import type { Route } from "./+types/marketplace";
import type { Auction } from "@clients/api/auctions";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Marketplace" },
        { name: "description", content: "Browse and purchase high-quality, verified carbon credits." },
    ];
}

// ---------------------------------------------------------------------------
// Compact countdown for auction cards
// ---------------------------------------------------------------------------

function CardCountdown({ endsAt }: { endsAt: string }) {
    const [remaining, setRemaining] = useState(0);

    useEffect(() => {
        const tick = () => setRemaining(Math.max(0, new Date(endsAt).getTime() - Date.now()));
        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, [endsAt]);

    const h = Math.floor(remaining / 3_600_000);
    const m = Math.floor((remaining % 3_600_000) / 60_000);
    const s = Math.floor((remaining % 60_000) / 1000);
    const isUrgent = remaining > 0 && remaining < 5 * 60 * 1000;

    return (
        <span className={`font-mono text-sm tabular-nums ${isUrgent ? 'text-red-600 font-semibold' : 'text-muted-foreground'}`}>
            {h > 0 && `${h}h `}{String(m).padStart(2, '0')}m {String(s).padStart(2, '0')}s
        </span>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type MarketplaceTab = 'fixed' | 'auctions';

export default function MarketplacePage() {
    const [tab, setTab] = useState<MarketplaceTab>('fixed');
    const { data, isLoading, isError, error } = useListings();
    const { data: auctions, isLoading: auctionsLoading } = useAuctions();
    const listings = data?.listings || [];
    const activeAuctions = auctions || [];

    const [checkoutListing, setCheckoutListing] = React.useState<any | null>(null);
    const [selectedAuction, setSelectedAuction] = useState<Auction | null>(null);

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px]">
                <div className="w-8 h-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-4" />
                <p className="text-muted-foreground animate-pulse font-medium">Scanning marketplace...</p>
            </div>
        );
    }

    if (isError) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] border-2 border-dashed border-destructive/20 rounded-2xl bg-destructive/5 p-8 text-center">
                <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
                    <Leaf className="w-6 h-6 text-destructive rotate-180" />
                </div>
                <h3 className="text-lg font-semibold text-destructive mb-2">Connection Error</h3>
                <p className="text-muted-foreground max-w-md mx-auto mb-6">
                    {error instanceof Error ? error.message : "We're having trouble reaching the carbon registry. Please try again later."}
                </p>
                <Button variant="outline" onClick={() => window.location.reload()}>
                    Retry Connection
                </Button>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-8 w-full animate-in fade-in duration-700 max-w-7xl mx-auto py-8">
            <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-2">
                    <h1 className="text-4xl font-bold tracking-tight text-foreground">Carbon Marketplace</h1>
                    <p className="text-muted-foreground text-lg max-w-2xl">
                        Browse and purchase high-quality, verified carbon credits to offset your emissions.
                    </p>
                </div>

                {/* Tab toggle */}
                <div className="flex gap-1 bg-muted/50 rounded-lg p-1 w-fit">
                    <button
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                            tab === 'fixed'
                                ? 'bg-background shadow-sm text-foreground'
                                : 'text-muted-foreground hover:text-foreground'
                        }`}
                        onClick={() => setTab('fixed')}
                    >
                        Fixed Price
                    </button>
                    <button
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                            tab === 'auctions'
                                ? 'bg-background shadow-sm text-foreground'
                                : 'text-muted-foreground hover:text-foreground'
                        }`}
                        onClick={() => setTab('auctions')}
                    >
                        <Gavel className="w-3.5 h-3.5" />
                        Auctions
                        {activeAuctions.length > 0 && (
                            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-5 min-w-[20px] justify-center">
                                {activeAuctions.length}
                            </Badge>
                        )}
                    </button>
                </div>
            </div>

            {/* ───────── Fixed Price Tab ───────── */}
            {tab === 'fixed' && (
                <>
                    {listings.length === 0 ? (
                        <div className="flex flex-col items-center justify-center p-12 text-center border rounded-xl bg-card/50 text-muted-foreground">
                            <Leaf className="w-12 h-12 mb-4 opacity-20" />
                            <p className="text-lg font-medium">No listings available at the moment.</p>
                            <p className="text-sm">Please check back later.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {listings.map((listing) => {
                                const available = listing.quantity_tonnes - listing.quantity_reserved - listing.quantity_sold;

                                return (
                                    <Card key={listing.id} className="flex flex-col overflow-hidden hover:shadow-lg transition-all duration-300 border-border/40 group">
                                        <div className="h-48 bg-muted relative overflow-hidden flex items-center justify-center">
                                            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent z-10"></div>
                                            <Leaf className="w-16 h-16 text-primary/20 group-hover:scale-110 transition-transform duration-500" />
                                            <div className="absolute bottom-4 left-4 z-20 flex gap-2">
                                                <Badge variant="secondary" className="bg-background/80 backdrop-blur-sm shadow-sm flex items-center gap-1">
                                                    {listing.project_type.replace('_', ' ')}
                                                </Badge>
                                                <Badge variant="outline" className="bg-background/80 backdrop-blur-sm text-white border-white/20 shadow-sm flex items-center gap-1">
                                                    {listing.registry_name}
                                                </Badge>
                                            </div>
                                        </div>

                                        <CardHeader className="pb-3">
                                            <div className="flex justify-between items-start gap-4">
                                                <CardTitle className="text-xl leading-tight line-clamp-2">{listing.project_name}</CardTitle>
                                            </div>
                                            <CardDescription className="flex flex-col gap-1.5 mt-2">
                                                {listing.project_country && (
                                                    <span className="flex items-center gap-1.5 text-sm">
                                                        <MapPin className="w-3.5 h-3.5 text-muted-foreground" />
                                                        {listing.project_country}
                                                    </span>
                                                )}
                                                {listing.vintage_year && (
                                                    <span className="flex items-center gap-1.5 text-sm">
                                                        <CalendarIcon className="w-3.5 h-3.5 text-muted-foreground" />
                                                        Vintage {listing.vintage_year}
                                                    </span>
                                                )}
                                            </CardDescription>
                                        </CardHeader>

                                        <CardContent className="flex-grow">
                                            <p className="text-sm text-muted-foreground line-clamp-3 mb-4">
                                                {listing.description || "No description provided."}
                                            </p>

                                            {listing.co_benefits && listing.co_benefits.length > 0 && (
                                                <div className="flex flex-wrap gap-1 mt-auto">
                                                    {listing.co_benefits.map((benefit, i) => (
                                                        <Badge key={i} variant="outline" className="text-xs font-normal text-muted-foreground">
                                                            {benefit.replace('_', ' ')}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            )}
                                        </CardContent>

                                        <CardFooter className="border-t bg-muted/20 flex flex-col pt-4 gap-4 pb-5">
                                            <div className="flex justify-between w-full items-end">
                                                <div className="flex flex-col">
                                                    <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Price</span>
                                                    <span className="text-2xl font-bold text-foreground">€{listing.price_per_tonne_eur.toFixed(2)}<span className="text-sm font-normal text-muted-foreground">/t</span></span>
                                                </div>
                                                <div className="flex flex-col text-right">
                                                    <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Available</span>
                                                    <span className="text-base font-semibold text-foreground">{available} <span className="text-sm font-normal text-muted-foreground">tonnes</span></span>
                                                </div>
                                            </div>
                                            <Button
                                                className="w-full font-semibold shadow-sm"
                                                variant="default"
                                                disabled={available <= 0}
                                                onClick={() => setCheckoutListing(listing)}
                                            >
                                                {available > 0 ? 'Buy Credits' : 'Sold Out'}
                                            </Button>
                                        </CardFooter>
                                    </Card>
                                );
                            })}
                        </div>
                    )}
                </>
            )}

            {/* ───────── Auctions Tab ───────── */}
            {tab === 'auctions' && (
                <>
                    {auctionsLoading ? (
                        <div className="flex flex-col items-center justify-center min-h-[300px]">
                            <div className="w-8 h-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-4" />
                            <p className="text-muted-foreground animate-pulse font-medium">Loading auctions...</p>
                        </div>
                    ) : activeAuctions.length === 0 ? (
                        <div className="flex flex-col items-center justify-center p-12 text-center border rounded-xl bg-card/50 text-muted-foreground">
                            <Gavel className="w-12 h-12 mb-4 opacity-20" />
                            <p className="text-lg font-medium">No active auctions at the moment.</p>
                            <p className="text-sm">Check back soon or browse fixed-price listings.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {activeAuctions.map((auction) => {
                                const hasBids = auction.bid_count > 0;
                                const displayPrice = auction.current_high_bid_eur ?? auction.config.starting_price_per_tonne_eur;

                                return (
                                    <Card
                                        key={auction.id}
                                        className="flex flex-col overflow-hidden hover:shadow-lg transition-all duration-300 border-border/40 cursor-pointer group"
                                        onClick={() => setSelectedAuction(auction)}
                                    >
                                        <CardHeader className="pb-3">
                                            <div className="flex items-center gap-2 mb-2">
                                                <Badge className="bg-emerald-500 text-white text-[10px] px-2 py-0.5 border-0 gap-1">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse inline-block" />
                                                    Live
                                                </Badge>
                                                {auction.project_type && (
                                                    <Badge variant="secondary" className="text-[10px] capitalize">
                                                        {auction.project_type.replace(/_/g, ' ')}
                                                    </Badge>
                                                )}
                                                {auction.created_by === 'agent' && (
                                                    <Badge variant="outline" className="text-[10px] text-violet-600 border-violet-200 gap-0.5">
                                                        <Bot className="w-2.5 h-2.5" /> Agent
                                                    </Badge>
                                                )}
                                            </div>
                                            <CardTitle className="text-xl leading-tight line-clamp-2">
                                                {auction.project_name || 'Auction'}
                                            </CardTitle>
                                            <CardDescription className="flex flex-wrap items-center gap-3 mt-1.5">
                                                {auction.project_country && (
                                                    <span className="flex items-center gap-1 text-sm">
                                                        <MapPin className="w-3.5 h-3.5 text-muted-foreground" />
                                                        {auction.project_country}
                                                    </span>
                                                )}
                                                {auction.vintage_year && (
                                                    <span className="flex items-center gap-1 text-sm">
                                                        <CalendarIcon className="w-3.5 h-3.5 text-muted-foreground" />
                                                        {auction.vintage_year}
                                                    </span>
                                                )}
                                            </CardDescription>
                                        </CardHeader>

                                        <CardContent className="flex-grow">
                                            {auction.co_benefits && auction.co_benefits.length > 0 && (
                                                <div className="flex flex-wrap gap-1">
                                                    {auction.co_benefits.slice(0, 3).map((benefit, i) => (
                                                        <Badge key={i} variant="outline" className="text-[10px] font-normal text-muted-foreground capitalize">
                                                            {benefit.replace(/_/g, ' ')}
                                                        </Badge>
                                                    ))}
                                                    {auction.co_benefits.length > 3 && (
                                                        <Badge variant="outline" className="text-[10px] font-normal text-muted-foreground">
                                                            +{auction.co_benefits.length - 3}
                                                        </Badge>
                                                    )}
                                                </div>
                                            )}
                                        </CardContent>

                                        <CardFooter className="border-t bg-muted/20 flex flex-col pt-4 gap-3 pb-5">
                                            <div className="flex justify-between w-full items-end">
                                                <div className="flex flex-col">
                                                    <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                                                        {hasBids ? 'Current Bid' : 'Starting Price'}
                                                    </span>
                                                    <span className="text-2xl font-bold text-foreground">
                                                        €{displayPrice.toFixed(2)}
                                                        <span className="text-sm font-normal text-muted-foreground">/t</span>
                                                    </span>
                                                </div>
                                                <div className="flex flex-col items-end gap-1">
                                                    {auction.effective_ends_at && (
                                                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                                            <Timer className="w-3 h-3" />
                                                            <CardCountdown endsAt={auction.effective_ends_at} />
                                                        </span>
                                                    )}
                                                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                                        <Users className="w-3 h-3" />
                                                        {auction.bid_count} bid{auction.bid_count !== 1 ? 's' : ''}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="flex gap-2 w-full">
                                                <Button
                                                    className="flex-1 font-semibold shadow-sm gap-2"
                                                    variant="default"
                                                    onClick={(e) => { e.stopPropagation(); setSelectedAuction(auction); }}
                                                >
                                                    <Gavel className="w-4 h-4" />
                                                    Place Bid
                                                </Button>
                                                {auction.config.buy_now_price_per_tonne_eur && (
                                                    <Button
                                                        variant="outline"
                                                        className="shrink-0 border-violet-200 text-violet-700 hover:bg-violet-50 gap-1.5 text-sm"
                                                        onClick={(e) => { e.stopPropagation(); setSelectedAuction(auction); }}
                                                    >
                                                        <Zap className="w-3.5 h-3.5" />
                                                        €{auction.config.buy_now_price_per_tonne_eur.toFixed(0)}
                                                    </Button>
                                                )}
                                            </div>
                                        </CardFooter>
                                    </Card>
                                );
                            })}
                        </div>
                    )}
                </>
            )}

            {/* ───────── Modals ───────── */}
            {checkoutListing && (
                <CheckoutModal
                    isOpen={true}
                    onClose={() => setCheckoutListing(null)}
                    listingId={checkoutListing.id}
                    listingName={checkoutListing.project_name}
                    pricePerTonne={checkoutListing.price_per_tonne_eur}
                    availableTonnes={checkoutListing.quantity_tonnes - checkoutListing.quantity_reserved - checkoutListing.quantity_sold}
                />
            )}

            {selectedAuction && (
                <AuctionDetailModal
                    isOpen={true}
                    onClose={() => setSelectedAuction(null)}
                    auctionId={selectedAuction.id}
                />
            )}
        </div>
    );
}
