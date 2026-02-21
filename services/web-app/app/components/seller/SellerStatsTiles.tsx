import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { TrendingUp, Pause, FileEdit, ShieldCheck } from 'lucide-react';
import type { Listing } from '@clients/api/listings';

interface SellerStatsTilesProps {
    listings: Listing[];
}

export function SellerStatsTiles({ listings }: SellerStatsTilesProps) {
    const containerRef = useRef<HTMLDivElement>(null);

    const activeCount = listings.filter(l => l.status === 'active').length;
    const pausedCount = listings.filter(l => l.status === 'paused').length;
    const draftCount = listings.filter(l => l.status === 'draft').length;
    const verifiedCount = listings.filter(l => l.verification_status === 'verified').length;

    const totalReserved = listings.reduce((s, l) => s + l.quantity_reserved, 0);

    useEffect(() => {
        const ctx = gsap.context(() => {
            gsap.fromTo(
                '.stat-tile',
                { y: 20, opacity: 0, scale: 0.95 },
                { y: 0, opacity: 1, scale: 1, stagger: 0.1, duration: 0.6, ease: 'back.out(1.5)', delay: 0.3 },
            );
        }, containerRef);
        return () => ctx.revert();
    }, []);

    const tiles = [
        {
            label: 'Active',
            value: activeCount,
            sub: `${totalReserved.toLocaleString()}t reserved`,
            icon: TrendingUp,
            iconBg: 'bg-emerald-500/10',
            iconColor: 'text-emerald-600',
            accent: 'border-emerald-500/20',
        },
        {
            label: 'Paused',
            value: pausedCount,
            sub: 'awaiting action',
            icon: Pause,
            iconBg: 'bg-amber-500/10',
            iconColor: 'text-amber-600',
            accent: 'border-amber-500/20',
        },
        {
            label: 'Draft',
            value: draftCount,
            sub: 'unpublished',
            icon: FileEdit,
            iconBg: 'bg-slate/5',
            iconColor: 'text-slate/50',
            accent: 'border-slate/10',
        },
        {
            label: 'Verified',
            value: verifiedCount,
            sub: `of ${listings.length} total`,
            icon: ShieldCheck,
            iconBg: 'bg-canopy/10',
            iconColor: 'text-canopy',
            accent: 'border-canopy/20',
        },
    ];

    return (
        <div ref={containerRef} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {tiles.map((tile) => (
                <div
                    key={tile.label}
                    className={`stat-tile flex flex-col gap-4 bg-white rounded-[1.25rem] border border-mist ${tile.accent} p-6 shadow-sm hover:shadow-md transition-shadow`}
                >
                    <div className="flex items-center justify-between">
                        <div className={`w-10 h-10 rounded-xl ${tile.iconBg} flex items-center justify-center`}>
                            <tile.icon size={18} className={tile.iconColor} strokeWidth={1.5} />
                        </div>
                        <span className="font-serif italic text-3xl text-slate">{tile.value}</span>
                    </div>
                    <div>
                        <span className="font-sans font-semibold text-sm text-slate">{tile.label}</span>
                        <span className="block font-mono text-[10px] text-slate/40 uppercase tracking-widest mt-1">{tile.sub}</span>
                    </div>
                </div>
            ))}
        </div>
    );
}
