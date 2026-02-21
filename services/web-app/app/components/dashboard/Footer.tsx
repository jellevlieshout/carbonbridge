import React from 'react';

export function Footer() {
    return (
        <div className="w-full flex flex-col mt-24">
            {/* Membership Tiers */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
                <div className="bg-white border border-mist p-8 rounded-[2rem] shadow-sm">
                    <h3 className="font-sans font-bold text-slate text-xl mb-4">Starter</h3>
                    <p className="font-sans text-slate/70 text-sm leading-relaxed mb-6">
                        Perfect for small businesses beginning their Net Zero journey. Includes basic footprint estimation and manual offset purchases.
                    </p>
                    <button className="text-slate font-medium text-sm border-b border-slate pb-1 hover:text-canopy hover:border-canopy transition-colors cursor-pointer">Upgrade to Starter</button>
                </div>

                <div className="bg-canopy border border-canopy/20 p-8 rounded-[2rem] shadow-sm relative overflow-hidden">
                    <div className="absolute top-6 right-6 bg-ember text-linen text-[10px] uppercase font-bold tracking-wider px-3 py-1 rounded-full">Active Plan</div>
                    <h3 className="font-sans font-bold text-linen text-xl mb-4">Professional</h3>
                    <p className="font-sans text-linen/70 text-sm leading-relaxed mb-6">
                        Everything you need for full-scale carbon management. Unlocks the autonomous purchasing agent, advanced reporting, and real-time market scanner.
                    </p>
                    <span className="text-linen/50 font-medium text-sm">Current Selection</span>
                </div>

                <div className="bg-white border border-mist p-8 rounded-[2rem] shadow-sm">
                    <h3 className="font-sans font-bold text-slate text-xl mb-4">Enterprise</h3>
                    <p className="font-sans text-slate/70 text-sm leading-relaxed mb-6">
                        For complex multi-national supply chains. Features custom API integrations, dedicated account management, and volume discounts.
                    </p>
                    <button className="text-slate font-medium text-sm border-b border-slate pb-1 hover:text-canopy hover:border-canopy transition-colors cursor-pointer">Contact Sales</button>
                </div>
            </div>

            {/* Deep Footer */}
            <footer className="w-full bg-slate text-linen rounded-t-[3rem] p-12 lg:p-16 flex flex-col md:flex-row justify-between gap-12 border-t-[8px] border-canopy relative overflow-hidden">
                {/* Noise Texture */}
                <div
                    className="absolute inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay z-0"
                    style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")" }}
                />

                <div className="relative z-10 flex flex-col gap-8 max-w-sm">
                    <div className="flex items-center gap-4 text-linen">
                        <div className="w-8 h-8 rounded-lg bg-linen/10 flex items-center justify-center shrink-0 font-semibold font-sans">CB</div>
                        <span className="text-xl font-semibold tracking-tight font-sans">CarbonBridge</span>
                    </div>
                    <p className="text-sm text-linen/60 leading-relaxed font-sans">
                        A voluntary carbon credit brokerage built for business owners, not day traders. Accessible environmental intelligence.
                    </p>
                    {/* Market Open Status */}
                    <div className="flex items-center gap-4 mt-4 opacity-80">
                        <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse ring-2 ring-emerald-400/30" />
                        <div className="flex flex-col">
                            <span className="text-[10px] text-linen/60 font-medium uppercase tracking-wider font-mono">Market Open</span>
                            <span className="font-mono text-sm text-linen tracking-tight">Reference: €14.20/t</span>
                        </div>
                    </div>
                </div>

                <div className="relative z-10 grid grid-cols-2 lg:grid-cols-3 gap-8 w-full md:w-auto text-sm">
                    <div className="flex flex-col gap-4">
                        <h4 className="font-serif italic text-lg text-linen/90 mb-2">Platform</h4>
                        <a href="#" className="font-sans text-linen/50 hover:text-ember transition-colors">Transaction Archive</a>
                        <a href="#" className="font-sans text-linen/50 hover:text-ember transition-colors">Carbon Accounting Export</a>
                        <a href="#" className="font-sans text-linen/50 hover:text-ember transition-colors">Methodology Glossary</a>
                    </div>

                    <div className="flex flex-col gap-4">
                        <h4 className="font-serif italic text-lg text-linen/90 mb-2">Trust</h4>
                        <a href="#" className="font-sans text-linen/50 hover:text-ember transition-colors">Registry Documents</a>
                        <a href="#" className="font-sans text-linen/50 hover:text-ember transition-colors">Verification Standards</a>
                        <a href="#" className="font-sans text-linen/50 hover:text-ember transition-colors">Support Center</a>
                    </div>
                </div>
            </footer>
        </div>
    );
}
