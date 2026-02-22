import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import gsap from 'gsap';
import { useListingsQuery } from '~/modules/shared/queries/useListings';
import type { Listing } from '@clients/api/listings';

const CARD_STYLES = [
    { color: 'bg-sage/10', border: 'border-sage/20' },
    { color: 'bg-canopy/5', border: 'border-canopy/10' },
    { color: 'bg-ember/5', border: 'border-ember/20' },
];

export function CreditShufflerTile() {
    const { data, isLoading } = useListingsQuery();
    const containerRef = useRef<HTMLDivElement>(null);
    const hasAnimated = useRef(false);

    const listings = useMemo(() => {
        const raw = data?.listings ?? [];
        const active = raw.filter(
            (l: Listing) => l.status === 'active' && (l.quantity_tonnes - l.quantity_reserved - l.quantity_sold) >= 1
        );
        return active.slice(0, 5).map((l: Listing, i: number) => ({
            id: l.id,
            name: l.project_name,
            price: `€${l.price_per_tonne_eur.toFixed(2)}`,
            standard: l.registry_name || 'VCS',
            vintage: l.vintage_year ? String(l.vintage_year) : '—',
            ...CARD_STYLES[i % CARD_STYLES.length],
        }));
    }, [data]);

    const [cards, setCards] = useState(listings);

    // Sync cards when listings data arrives and run entrance animation once
    useEffect(() => {
        if (listings.length > 0) {
            setCards(listings);
            // Run entrance animation only on first data load
            if (!hasAnimated.current) {
                hasAnimated.current = true;
                requestAnimationFrame(() => {
                    if (!containerRef.current) return;
                    const ctx = gsap.context(() => {
                        gsap.fromTo(".shuffler-card",
                            { y: -20, opacity: 0, scale: 0.95 },
                            { y: 0, opacity: 1, scale: 1, duration: 0.6, stagger: 0.1, ease: "back.out(1.5)" }
                        );
                    }, containerRef);
                    // Don't revert — let it persist
                });
            }
        }
    }, [listings]);

    // Card shuffle interval
    useEffect(() => {
        if (cards.length < 2) return;
        const shuffleInterval = setInterval(() => {
            setCards(prevCards => {
                const newCards = [...prevCards];
                const last = newCards.pop();
                if (last) newCards.unshift(last);
                return newCards;
            });
        }, 3000);

        return () => clearInterval(shuffleInterval);
    }, [cards.length]);

    // Animate on each shuffle (after initial)
    const prevCardsRef = useRef(cards);
    useEffect(() => {
        if (!cards.length || !hasAnimated.current) return;
        // Only animate if the order actually changed (shuffle), not initial load
        if (prevCardsRef.current === cards) return;
        prevCardsRef.current = cards;

        if (!containerRef.current) return;
        const ctx = gsap.context(() => {
            gsap.fromTo(".shuffler-card",
                { y: -20, opacity: 0, scale: 0.95 },
                { y: 0, opacity: 1, scale: 1, duration: 0.6, stagger: 0.1, ease: "back.out(1.5)" }
            );
        }, containerRef);
        return () => ctx.revert();
    }, [cards]);

    return (
        <div className="flex flex-col h-full w-full rounded-[1.25rem] bg-white border border-mist p-6 shadow-sm overflow-hidden relative">
            <div className="flex items-center justify-between mb-6 relative z-10">
                <h3 className="font-sans font-semibold text-slate tracking-tight">Market Scanner</h3>
                <span className="font-mono text-[10px] uppercase tracking-wider text-slate/50 bg-mist px-2 py-1 rounded-md">
                    {isLoading ? 'Loading' : cards.length > 0 ? 'Live feed' : 'No listings'}
                </span>
            </div>

            <div ref={containerRef} className="relative flex-1 flex flex-col items-center justify-center">
                {isLoading && (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-6 h-6 border-2 border-mist border-t-slate/40 rounded-full animate-spin" />
                    </div>
                )}

                {!isLoading && cards.length === 0 && (
                    <p className="font-mono text-xs text-slate/40 text-center">No active listings on the marketplace yet.</p>
                )}

                {cards.map((card, index) => {
                    const isTop = index === 0;
                    const yOffset = index * 12;
                    const scale = 1 - (index * 0.05);
                    const opacity = 1 - (index * 0.3);
                    const zIndex = 10 - index;

                    return (
                        <div
                            key={card.id}
                            className={`shuffler-card absolute w-full rounded-xl p-5 border shadow-sm transition-all duration-700 ease-spring ${isTop ? 'bg-linen border-mist' : `${card.color} ${card.border} backdrop-blur-md`}`}
                            style={{
                                transform: `translateY(${yOffset}px) scale(${scale})`,
                                opacity: opacity,
                                zIndex: zIndex
                            }}
                        >
                            <div className="flex justify-between items-start mb-2">
                                <span className="font-sans font-medium text-sm text-slate px-1">{card.name}</span>
                                <span className="font-mono text-lg font-semibold text-slate">{card.price}</span>
                            </div>
                            <div className="flex bg-white/50 w-fit rounded-full px-3 py-1 items-center gap-2 border border-black/5 mt-4">
                                <span className="font-mono text-[10px] uppercase font-semibold text-slate/70">{card.standard}</span>
                                <span className="w-1 h-1 rounded-full bg-slate/20" />
                                <span className="font-mono text-[10px] text-slate/60 shadow-sm">{card.vintage}</span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
