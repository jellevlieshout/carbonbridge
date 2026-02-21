import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { Archive, ArrowUpRight, ArrowDownLeft, RefreshCw, Clock } from 'lucide-react';
import type { Route } from "./+types/platform-transactions";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Transaction Archive" },
        { name: "description", content: "Browse the full history of carbon credit transactions across the CarbonBridge platform." },
    ];
}

const transactions = [
    { id: 'TXN-2024-001847', type: 'purchase', project: 'Kasigau Corridor REDD+', registry: 'Verra VCS', tonnes: 120, pricePerTonne: 14.80, date: '2024-12-15', status: 'settled' },
    { id: 'TXN-2024-001832', type: 'purchase', project: 'Woodland Carbon Code — Glen Affric', registry: 'UK WCC', tonnes: 45, pricePerTonne: 22.50, date: '2024-12-12', status: 'settled' },
    { id: 'TXN-2024-001819', type: 'retirement', project: 'Guatemala Clean Cookstoves', registry: 'Gold Standard', tonnes: 200, pricePerTonne: 8.40, date: '2024-12-08', status: 'settled' },
    { id: 'TXN-2024-001801', type: 'purchase', project: 'Brazilian Cerrado Conservation', registry: 'Verra VCS', tonnes: 75, pricePerTonne: 11.20, date: '2024-11-29', status: 'settled' },
    { id: 'TXN-2024-001793', type: 'transfer', project: 'Kenyan Biogas Programme', registry: 'Gold Standard', tonnes: 30, pricePerTonne: 16.90, date: '2024-11-22', status: 'settled' },
    { id: 'TXN-2024-001780', type: 'purchase', project: 'Pacific Northwest Improved Forest Mgmt', registry: 'ACR', tonnes: 500, pricePerTonne: 19.00, date: '2024-11-15', status: 'settled' },
    { id: 'TXN-2024-001764', type: 'retirement', project: 'Indian Wind Power Bundle', registry: 'Verra VCS', tonnes: 1000, pricePerTonne: 5.60, date: '2024-11-01', status: 'settled' },
    { id: 'TXN-2024-001750', type: 'purchase', project: 'Rimba Raya Biodiversity Reserve', registry: 'Verra VCS', tonnes: 250, pricePerTonne: 13.40, date: '2024-10-20', status: 'pending' },
];

const typeConfig = {
    purchase: { icon: ArrowDownLeft, label: 'Purchase', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
    retirement: { icon: Archive, label: 'Retirement', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
    transfer: { icon: RefreshCw, label: 'Transfer', color: 'text-sky-400 bg-sky-500/10 border-sky-500/20' },
};

export default function PlatformTransactionsPage() {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const ctx = gsap.context(() => {
            gsap.fromTo(".page-stagger", { y: 30, opacity: 0 }, { y: 0, opacity: 1, stagger: 0.12, duration: 0.8, ease: "power3.out", delay: 0.1 });
        }, containerRef);
        return () => ctx.revert();
    }, []);

    const totalVolume = transactions.reduce((sum, t) => sum + t.tonnes, 0);
    const totalValue = transactions.reduce((sum, t) => sum + (t.tonnes * t.pricePerTonne), 0);

    return (
        <div ref={containerRef} className="flex flex-col gap-10 w-full animate-in fade-in duration-700">
            {/* Hero */}
            <div className="page-stagger relative w-full rounded-[2rem] bg-canopy text-linen p-10 overflow-hidden shadow-sm">
                <div className="absolute inset-0 pointer-events-none opacity-[0.04] mix-blend-overlay z-0" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")" }} />
                <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_80%_0%,rgba(61,107,82,0.4)_0%,transparent_50%)] pointer-events-none" />

                <div className="relative z-10 flex flex-col md:flex-row justify-between items-start gap-8">
                    <div className="flex flex-col gap-4">
                        <h1 className="text-[3rem] leading-tight tracking-tight font-serif italic text-linen">Transaction Archive</h1>
                        <p className="text-linen/70 font-sans text-lg max-w-xl">
                            A complete, auditable record of every credit movement on the CarbonBridge platform — purchases, retirements, and transfers.
                        </p>
                    </div>
                    <div className="flex gap-4">
                        <div className="font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                            <span className="opacity-60">Volume</span>
                            <span className="font-medium text-linen">{totalVolume.toLocaleString()} tCO₂e</span>
                        </div>
                        <div className="font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                            <span className="opacity-60">Value</span>
                            <span className="font-medium text-linen">€{totalValue.toLocaleString()}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Transaction List */}
            <div className="page-stagger flex flex-col gap-3">
                {transactions.map((txn) => {
                    const config = typeConfig[txn.type as keyof typeof typeConfig];
                    const TypeIcon = config.icon;
                    return (
                        <div key={txn.id} className="bg-white border border-mist rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow flex items-center gap-6">
                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${config.color}`}>
                                <TypeIcon size={18} />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-3 mb-1">
                                    <span className="font-mono text-xs text-slate/50">{txn.id}</span>
                                    <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border ${config.color}`}>{config.label}</span>
                                    {txn.status === 'pending' && (
                                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 border border-amber-200 flex items-center gap-1">
                                            <Clock size={10} /> Pending
                                        </span>
                                    )}
                                </div>
                                <p className="font-medium text-slate truncate">{txn.project}</p>
                                <p className="text-xs text-slate/50 font-sans mt-0.5">{txn.registry} • {txn.date}</p>
                            </div>
                            <div className="text-right shrink-0">
                                <p className="font-mono text-sm font-medium text-slate">{txn.tonnes.toLocaleString()} t</p>
                                <p className="font-mono text-xs text-slate/50">€{txn.pricePerTonne.toFixed(2)}/t</p>
                            </div>
                            <div className="text-right shrink-0 min-w-[100px]">
                                <p className="font-mono text-sm font-semibold text-canopy">€{(txn.tonnes * txn.pricePerTonne).toLocaleString()}</p>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
