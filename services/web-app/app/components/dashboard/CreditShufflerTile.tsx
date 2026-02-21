import React, { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';

const listings = [
    { id: 1, name: "Borneo Peatland Restoration", price: "€16.80", standard: "VCS", vintage: "2023", color: "bg-sage/10", border: "border-sage/20" },
    { id: 2, name: "Scottish Upland Afforestation", price: "€12.40", standard: "WCC", vintage: "2022", color: "bg-canopy/5", border: "border-canopy/10" },
    { id: 3, name: "Ugandan Improved Cookstoves", price: "€9.10", standard: "Gold Standard", vintage: "2023", color: "bg-ember/5", border: "border-ember/20" },
];

export function CreditShufflerTile() {
    const [cards, setCards] = useState(listings);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const shuffleInterval = setInterval(() => {
            setCards(prevCards => {
                const newCards = [...prevCards];
                const last = newCards.pop();
                if (last) newCards.unshift(last);
                return newCards;
            });
        }, 3000);

        return () => clearInterval(shuffleInterval);
    }, []);

    useEffect(() => {
        // Animate the shuffle visually via GSAP layout shifts where possible
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
                <span className="font-mono text-[10px] uppercase tracking-wider text-slate/50 bg-mist px-2 py-1 rounded-md">Live feed</span>
            </div>

            <div ref={containerRef} className="relative flex-1 flex flex-col items-center justify-center">
                {cards.map((card, index) => {
                    // Calculate offset stack positions
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
