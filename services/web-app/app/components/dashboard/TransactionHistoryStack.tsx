import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const transactions = [
    { id: 1, title: 'Woodland Credits Purchase', volume: '40t', date: 'Oct 2023', type: 'forestry' },
    { id: 2, title: 'Industrial Offset Batch', volume: '110t', date: 'Jan 2024', type: 'industrial' },
    { id: 3, title: 'Cookstove Project Contribution', volume: '30t', date: 'Mar 2024', type: 'cookstove' },
];

export function TransactionHistoryStack() {
    const containerRef = useRef<HTMLDivElement>(null);
    const cardsRef = useRef<(HTMLDivElement | null)[]>([]);

    useEffect(() => {
        const ctx = gsap.context(() => {
            // Stacking effect
            cardsRef.current.forEach((card, i) => {
                if (!card || i === 0) return; // Skip first card

                ScrollTrigger.create({
                    trigger: card,
                    start: "top 20%",
                    end: "top 5%",
                    scrub: true,
                    animation: gsap.to(cardsRef.current[i - 1], {
                        scale: 0.92,
                        filter: "blur(12px)", // slightly less than 16px for better visual mix
                        opacity: 0.5,
                        transformOrigin: "top center",
                        y: 20
                    })
                });
            });
        }, containerRef);

        return () => ctx.revert();
    }, []);

    return (
        <div ref={containerRef} className="w-full mt-24 mb-32 relative flex flex-col items-center">
            <div className="w-full flex justify-between items-end mb-12">
                <h2 className="font-serif italic text-4xl text-slate text-center w-full">Transaction Archive</h2>
            </div>

            <div className="w-full relative max-w-4xl mx-auto space-y-[40vh]">
                {transactions.map((tx, idx) => (
                    <div
                        key={tx.id}
                        ref={(el) => {
                            if (el) cardsRef.current[idx] = el;
                        }}
                        className="w-full h-[60vh] min-h-[400px] sticky top-[15vh] rounded-[2rem] bg-white border border-mist shadow-lg overflow-hidden flex flex-col md:flex-row origin-top"
                    >
                        {/* Visual Animation Half */}
                        <div className="w-full md:w-1/2 bg-linen rounded-l-[2rem] relative overflow-hidden flex flex-col items-center justify-center p-10">

                            {/* Type-specific SVG (mock animations) */}
                            {tx.type === 'forestry' && (
                                <div className="w-64 h-64 border-[1px] border-canopy/20 rounded-full flex items-center justify-center animate-spin" style={{ animationDuration: '30s' }}>
                                    <div className="w-48 h-48 border-[1.5px] border-canopy/40 rounded-full flex items-center justify-center animate-spin" style={{ animationDirection: 'reverse', animationDuration: '20s' }}>
                                        <div className="w-32 h-32 border-[2px] border-canopy/60 rounded-full animate-pulse object-center" />
                                    </div>
                                </div>
                            )}

                            {tx.type === 'industrial' && (
                                <div className="grid grid-cols-6 gap-2 w-full h-full p-8 opacity-40">
                                    {Array.from({ length: 36 }).map((_, i) => (
                                        <div key={i} className="bg-slate/30 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.1}s` }} />
                                    ))}
                                </div>
                            )}

                            {tx.type === 'cookstove' && (
                                <div className="w-full h-full flex items-center justify-center relative">
                                    <div className="w-32 h-32 bg-ember/20 rounded-full animate-ping absolute" />
                                    <div className="w-16 h-16 bg-ember/60 rounded-full animate-pulse relative z-10" />
                                    {/* Minimal dot grid */}
                                    <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_center,rgba(0,0,0,0.1)_1px,transparent_1px)]" style={{ backgroundSize: '24px 24px' }} />
                                </div>
                            )}
                        </div>

                        {/* Data Half */}
                        <div className="w-full md:w-1/2 p-12 flex flex-col justify-between relative bg-white">
                            <div className="absolute top-0 right-0 p-8">
                                <span className="font-mono text-sm px-4 py-2 bg-mist rounded-full text-slate/70">{tx.date}</span>
                            </div>

                            <div className="mt-16">
                                <h3 className="font-sans font-bold text-3xl text-slate leading-tight">{tx.title}</h3>
                                <div className="mt-8 pt-8 border-t border-mist/60 grid grid-cols-2 gap-8">
                                    <div>
                                        <span className="block font-mono text-xs text-slate/50 uppercase mb-2">Volume</span>
                                        <span className="font-serif italic text-4xl text-canopy">{tx.volume}</span>
                                    </div>
                                    <div>
                                        <span className="block font-mono text-xs text-slate/50 uppercase mb-2">Standard</span>
                                        <span className="font-sans text-xl font-medium text-slate">Verified Carbon Standard</span>
                                    </div>
                                </div>
                            </div>

                            <button className="magnetic-btn w-fit px-8 py-4 rounded-full bg-slate text-linen mt-8 border-none overflow-hidden group">
                                <div className="magnetic-bg bg-ember" />
                                <span className="relative z-10 font-medium">View Certificate</span>
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
