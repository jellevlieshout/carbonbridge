import React, { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';

const agentMessages = [
    "Agent monitoring 3 new Woodland Carbon Code listings...",
    "Price alert triggered: Kenyan cookstove credits down 4.2%...",
    "Portfolio balanced across 3 registries.",
    "Scanning Gold Standard issuances from Q3 2023..."
];

export function HeroPanel() {
    const containerRef = useRef<HTMLDivElement>(null);
    const [messageIndex, setMessageIndex] = useState(0);
    const [displayedText, setDisplayedText] = useState("");

    useEffect(() => {
        // GSAP staggered reveal
        const ctx = gsap.context(() => {
            gsap.fromTo(
                ".hero-stagger",
                { y: 30, opacity: 0 },
                { y: 0, opacity: 1, stagger: 0.12, duration: 0.8, ease: "power3.out", delay: 0.1 }
            );
        }, containerRef);
        return () => ctx.revert();
    }, []);

    useEffect(() => {
        // Typewriter effect
        const fullText = agentMessages[messageIndex];
        let charIndex = 0;

        // reset
        setDisplayedText("");

        const typeInterval = setInterval(() => {
            if (charIndex < fullText.length) {
                setDisplayedText(prev => prev + fullText[charIndex]);
                charIndex++;
            } else {
                clearInterval(typeInterval);
                setTimeout(() => {
                    setMessageIndex((prev) => (prev + 1) % agentMessages.length);
                }, 3000);
            }
        }, 40);

        return () => {
            clearInterval(typeInterval);
        };
    }, [messageIndex]);

    return (
        <div
            ref={containerRef}
            className="relative w-full rounded-[2rem] bg-canopy text-linen p-10 overflow-hidden flex flex-col md:flex-row gap-8 justify-between shadow-sm"
        >
            {/* Noise Texture */}
            <div
                className="absolute inset-0 pointer-events-none opacity-[0.04] mix-blend-overlay z-0"
                style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")" }}
            />
            {/* Radial Mesh Gradient subtle overlay */}
            <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_80%_0%,rgba(61,107,82,0.4)_0%,transparent_50%)] pointer-events-none" />

            {/* Left Column: Carbon Position */}
            <div className="relative z-10 flex flex-col gap-6 w-full md:w-1/2">
                <h2 className="hero-stagger text-[4rem] leading-[1.05] tracking-tight font-serif italic text-linen">
                    −142 tCO₂e
                    <span className="block text-4xl mt-2 not-italic font-sans font-medium opacity-90 tracking-normal">offset this year</span>
                </h2>

                <div className="flex flex-wrap gap-3 mt-4">
                    <div className="hero-stagger font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                        <span className="opacity-60">Credits Held</span>
                        <span className="font-medium text-linen">38 active</span>
                    </div>
                    <div className="hero-stagger font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                        <span className="opacity-60">Avg. Price Paid</span>
                        <span className="font-medium text-linen">€14.20 / tCO₂e</span>
                    </div>
                    <div className="hero-stagger font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                        <span className="opacity-60">Portfolio Vintage</span>
                        <span className="font-medium text-linen">2022 to 2024</span>
                    </div>
                </div>
            </div>

            {/* Right Column: Agent Feed */}
            <div className="relative z-10 hero-stagger w-full md:w-1/3 flex flex-col justify-end bg-slate/20 rounded-2xl p-6 border border-linen/5 backdrop-blur-sm">
                <div className="flex items-center gap-2 mb-4">
                    <div className="w-2 h-2 rounded-full bg-ember animate-pulse ring-2 ring-ember/30" />
                    <span className="text-xs font-sans font-medium text-linen/70 uppercase tracking-wider">Agent Active</span>
                </div>
                <div className="font-mono text-sm leading-relaxed text-linen/90 min-h-[4.5rem]">
                    {displayedText}
                    <span className="inline-block w-2 h-4 bg-ember align-middle ml-1 animate-pulse" />
                </div>
            </div>
        </div>
    );
}
