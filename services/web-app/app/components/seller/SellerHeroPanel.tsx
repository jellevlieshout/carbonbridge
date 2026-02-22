import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { Leaf, TrendingUp, Package, ShieldCheck, BadgeCheck } from 'lucide-react';
import type { Listing } from '@clients/api/listings';

interface SellerHeroProps {
    listings: Listing[];
}

export function SellerHeroPanel({ listings }: SellerHeroProps) {
    const containerRef = useRef<HTMLDivElement>(null);

    const totalListed = listings.reduce((sum, l) => sum + l.quantity_tonnes, 0);
    const totalSold = listings.reduce((sum, l) => sum + l.quantity_sold, 0);
    const totalRevenue = listings.reduce(
        (sum, l) => sum + l.quantity_sold * l.price_per_tonne_eur, 0,
    );
    const activeCount = listings.filter(l => l.status === 'active').length;

    useEffect(() => {
        const ctx = gsap.context(() => {
            gsap.fromTo(
                '.seller-hero-stagger',
                { y: 30, opacity: 0 },
                { y: 0, opacity: 1, stagger: 0.12, duration: 0.8, ease: 'power3.out', delay: 0.1 },
            );
        }, containerRef);
        return () => ctx.revert();
    }, []);

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
            {/* Radial gradient */}
            <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_80%_0%,rgba(61,107,82,0.4)_0%,transparent_50%)] pointer-events-none" />

            {/* Left Column */}
            <div className="relative z-10 flex flex-col gap-6 w-full md:w-1/2">
                <h2 className="seller-hero-stagger text-[4rem] leading-[1.05] tracking-tight font-serif italic text-linen">
                    {totalSold.toLocaleString()} tCO₂e
                    <span className="block text-4xl mt-2 not-italic font-sans font-medium opacity-90 tracking-normal">sold across your portfolio</span>
                </h2>

                <div className="flex flex-wrap gap-3 mt-4">
                    <div className="seller-hero-stagger font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                        <Package size={12} className="opacity-60" />
                        <span className="opacity-60">Total Listed</span>
                        <span className="font-medium text-linen">{totalListed.toLocaleString()}t</span>
                    </div>
                    <div className="seller-hero-stagger font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                        <TrendingUp size={12} className="opacity-60" />
                        <span className="opacity-60">Revenue</span>
                        <span className="font-medium text-linen">€{totalRevenue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</span>
                    </div>
                    <div className="seller-hero-stagger font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                        <Leaf size={12} className="opacity-60" />
                        <span className="opacity-60">Active Listings</span>
                        <span className="font-medium text-linen">{activeCount}</span>
                    </div>
                    <div className="seller-hero-stagger font-mono text-xs bg-emerald-400/20 px-4 py-2 rounded-full border border-emerald-400/30 flex items-center gap-2">
                        <ShieldCheck size={12} className="text-emerald-300" />
                        <span className="text-emerald-200">KYB Verified</span>
                    </div>
                    <div className="seller-hero-stagger font-mono text-xs bg-emerald-400/20 px-4 py-2 rounded-full border border-emerald-400/30 flex items-center gap-2">
                        <BadgeCheck size={12} className="text-emerald-300" />
                        <span className="text-emerald-200">AML Cleared</span>
                    </div>
                </div>
            </div>

            {/* Right Column: Portfolio summary */}
            <div className="relative z-10 seller-hero-stagger w-full md:w-1/3 flex flex-col justify-end bg-slate/20 rounded-2xl p-6 border border-linen/5 backdrop-blur-sm">
                <div className="flex items-center gap-2 mb-4">
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse ring-2 ring-emerald-400/30" />
                    <span className="text-xs font-sans font-medium text-linen/70 uppercase tracking-wider">Portfolio Health</span>
                </div>
                <div className="space-y-3">
                    <div className="flex justify-between items-center">
                        <span className="font-mono text-xs text-linen/60">Sell-through</span>
                        <span className="font-mono text-sm font-medium text-linen">
                            {totalListed > 0 ? Math.round((totalSold / totalListed) * 100) : 0}%
                        </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-linen/10 overflow-hidden">
                        <div
                            className="h-full rounded-full bg-emerald-400 transition-all duration-1000"
                            style={{ width: `${totalListed > 0 ? (totalSold / totalListed) * 100 : 0}%` }}
                        />
                    </div>
                    <div className="flex justify-between items-center mt-2">
                        <span className="font-mono text-xs text-linen/60">Avg. Price</span>
                        <span className="font-mono text-sm font-medium text-linen">
                            €{listings.length > 0
                                ? (listings.reduce((s, l) => s + l.price_per_tonne_eur, 0) / listings.length).toFixed(2)
                                : '0.00'
                            }
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
