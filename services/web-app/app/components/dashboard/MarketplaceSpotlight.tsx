import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export function MarketplaceSpotlight() {
    const containerRef = useRef<HTMLDivElement>(null);
    const priceText = "€16.80";

    useEffect(() => {
        const ctx = gsap.context(() => {
            // Parallax effect on background
            gsap.to(".parallax-bg", {
                y: "20%",
                ease: "none",
                scrollTrigger: {
                    trigger: containerRef.current,
                    start: "top bottom",
                    end: "bottom top",
                    scrub: true,
                }
            });

            // Split text reveal simulation (since SplitText plugin requires premium)
            gsap.fromTo(
                ".price-char",
                { opacity: 0, y: 50 },
                {
                    opacity: 1,
                    y: 0,
                    duration: 0.8,
                    stagger: 0.1,
                    ease: "back.out(2)",
                    scrollTrigger: {
                        trigger: containerRef.current,
                        start: "top 70%",
                    }
                }
            );
        }, containerRef);
        return () => ctx.revert();
    }, []);

    return (
        <div
            ref={containerRef}
            className="relative w-full rounded-[2rem] bg-slate overflow-hidden flex flex-col md:flex-row shadow-sm mt-12 min-h-[400px]"
        >
            {/* Parallax Background */}
            <div
                className="parallax-bg absolute top-[-20%] left-0 w-full h-[140%] opacity-40 z-0 bg-cover bg-center mix-blend-luminosity"
                style={{ backgroundImage: "url('https://images.unsplash.com/photo-1511497584788-8cd4abc98129?q=80&w=2000&auto=format&fit=crop')" }}
            />
            {/* Noise overlay */}
            <div
                className="absolute inset-0 pointer-events-none opacity-20 mix-blend-overlay z-0"
                style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")" }}
            />

            <div className="relative z-10 p-12 w-full flex flex-col lg:flex-row gap-12 items-center justify-between">
                {/* Left Column: Editorial Large Text */}
                <div className="flex flex-col gap-4 lg:w-3/5">
                    <h2 className="text-linen font-sans font-bold text-3xl tracking-tight">
                        Borneo Peatland Restoration
                    </h2>
                    <div className="flex items-baseline gap-4 mt-4">
                        <span className="text-linen font-serif italic text-[7rem] leading-none tracking-tighter">
                            {priceText.split('').map((char, i) => (
                                <span key={i} className="price-char inline-block">{char}</span>
                            ))}
                        </span>
                        <span className="text-linen/60 font-mono text-xl">/ tCO₂e</span>
                    </div>
                </div>

                {/* Right Column: Structured At-a-glance */}
                <div className="lg:w-2/5 flex flex-col gap-6 pl-8 border-l-[3px] border-ember">
                    <div>
                        <span className="block font-mono text-xs text-linen/60 uppercase tracking-widest mb-1">Standard</span>
                        <span className="font-sans text-lg font-medium text-linen flex items-center gap-2">
                            Verified Carbon Standard
                            <div className="bg-emerald-500/20 text-emerald-300 text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider border border-emerald-500/30">Independent Verification</div>
                        </span>
                    </div>

                    <div>
                        <span className="block font-mono text-xs text-linen/60 uppercase tracking-widest mb-1">Location</span>
                        <span className="font-sans text-lg font-medium text-linen">Kalimantan, Indonesia</span>
                    </div>

                    <div>
                        <span className="block font-mono text-xs text-linen/60 uppercase tracking-widest mb-2">Co-Benefits</span>
                        <div className="flex gap-2">
                            <span className="bg-linen/10 text-linen text-xs px-3 py-1.5 rounded-full border border-linen/20">Biodiversity</span>
                            <span className="bg-linen/10 text-linen text-xs px-3 py-1.5 rounded-full border border-linen/20">Community Health</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
