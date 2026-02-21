import React, { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import { BookOpen, Search } from 'lucide-react';
import type { Route } from "./+types/platform-glossary";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Methodology Glossary" },
        { name: "description", content: "A comprehensive glossary of carbon market terms, methodologies, and standards." },
    ];
}

type GlossaryCategory = 'Registry' | 'Standard' | 'Methodology' | 'Market' | 'Compliance' | 'Science';

const categoryColors: Record<GlossaryCategory, string> = {
    Registry: 'text-sky-600 bg-sky-50 border-sky-200',
    Standard: 'text-emerald-600 bg-emerald-50 border-emerald-200',
    Methodology: 'text-violet-600 bg-violet-50 border-violet-200',
    Market: 'text-amber-600 bg-amber-50 border-amber-200',
    Compliance: 'text-rose-600 bg-rose-50 border-rose-200',
    Science: 'text-teal-600 bg-teal-50 border-teal-200',
};

const glossaryTerms: { term: string; definition: string; category: GlossaryCategory }[] = [
    { term: 'Additionality', definition: 'The principle that a carbon offset project must result in emission reductions that would not have occurred without the incentive provided by carbon credit revenue.', category: 'Methodology' },
    { term: 'Baseline Scenario', definition: 'The projected emissions trajectory that would occur in the absence of a carbon offset project. Used to calculate the net emission reductions achieved.', category: 'Methodology' },
    { term: 'Carbon Credit', definition: 'A tradable certificate representing one metric tonne of CO₂ equivalent (tCO₂e) that has been reduced, avoided, or removed from the atmosphere.', category: 'Market' },
    { term: 'CDM', definition: 'Clean Development Mechanism — a UN-regulated market mechanism under the Kyoto Protocol allowing industrialized countries to invest in emission reduction projects in developing nations.', category: 'Standard' },
    { term: 'Co-benefits', definition: 'Positive social, economic, or environmental outcomes beyond greenhouse gas reductions, such as biodiversity conservation, job creation, or improved public health.', category: 'Methodology' },
    { term: 'CORSIA', definition: 'Carbon Offsetting and Reduction Scheme for International Aviation — ICAO\'s global market-based measure to stabilize CO₂ emissions from international aviation.', category: 'Compliance' },
    { term: 'Double Counting', definition: 'The risk that the same emission reduction is claimed by more than one party. Registries use unique serial numbers and retirement tracking to prevent this.', category: 'Registry' },
    { term: 'EU ETS', definition: 'European Union Emissions Trading System — the world\'s largest compliance carbon market, covering power generation, industry, and aviation sectors.', category: 'Compliance' },
    { term: 'Gold Standard', definition: 'A certification standard for carbon offset projects founded by WWF. Emphasizes sustainable development co-benefits and stringent verification.', category: 'Registry' },
    { term: 'GHG Protocol', definition: 'The most widely used international accounting standard for measuring and managing greenhouse gas emissions across Scope 1, 2, and 3 categories.', category: 'Standard' },
    { term: 'Leakage', definition: 'When emission reductions in one area lead to increased emissions elsewhere. Methodologies must account for and deduct estimated leakage from credit issuance.', category: 'Methodology' },
    { term: 'MRV', definition: 'Measurement, Reporting, and Verification — the framework of protocols ensuring that emission reductions are accurately quantified, documented, and independently audited.', category: 'Standard' },
    { term: 'Nature-Based Solutions', definition: 'Projects that protect, restore, or sustainably manage natural ecosystems to address climate change — including REDD+, afforestation, and blue carbon initiatives.', category: 'Science' },
    { term: 'Permanence', definition: 'The requirement that carbon sequestration achieved by a project is long-lasting. Forest projects typically require 30–100 year permanence commitments with buffer pools.', category: 'Methodology' },
    { term: 'REDD+', definition: 'Reducing Emissions from Deforestation and Forest Degradation — a framework for compensating developing countries for reducing emissions from deforestation.', category: 'Science' },
    { term: 'Retirement', definition: 'The permanent removal of a carbon credit from circulation, representing a final claim on the associated emission reduction. Retired credits cannot be resold or transferred.', category: 'Market' },
    { term: 'Scope 3', definition: 'Indirect emissions occurring in a company\'s value chain, including purchased goods, transportation, employee commuting, and end-of-life treatment of products.', category: 'Compliance' },
    { term: 'VCS', definition: 'Verified Carbon Standard — managed by Verra, the world\'s largest voluntary carbon offset program by volume. Issues Verified Carbon Units (VCUs).', category: 'Registry' },
    { term: 'Vintage', definition: 'The year in which the emission reduction or removal took place. Buyers often prefer recent vintages as they represent more current environmental impact.', category: 'Market' },
    { term: 'Voluntary Carbon Market', definition: 'The market where companies and individuals voluntarily purchase carbon credits to offset emissions, distinct from compliance markets mandated by regulation.', category: 'Market' },
];

export default function PlatformGlossaryPage() {
    const containerRef = useRef<HTMLDivElement>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeCategory, setActiveCategory] = useState<GlossaryCategory | 'All'>('All');

    useEffect(() => {
        const ctx = gsap.context(() => {
            gsap.fromTo(".page-stagger", { y: 30, opacity: 0 }, { y: 0, opacity: 1, stagger: 0.12, duration: 0.8, ease: "power3.out", delay: 0.1 });
        }, containerRef);
        return () => ctx.revert();
    }, []);

    const categories: ('All' | GlossaryCategory)[] = ['All', 'Registry', 'Standard', 'Methodology', 'Market', 'Compliance', 'Science'];

    const filteredTerms = glossaryTerms
        .filter(t => activeCategory === 'All' || t.category === activeCategory)
        .filter(t => !searchQuery || t.term.toLowerCase().includes(searchQuery.toLowerCase()) || t.definition.toLowerCase().includes(searchQuery.toLowerCase()))
        .sort((a, b) => a.term.localeCompare(b.term));

    return (
        <div ref={containerRef} className="flex flex-col gap-10 w-full animate-in fade-in duration-700">
            {/* Hero */}
            <div className="page-stagger relative w-full rounded-[2rem] bg-canopy text-linen p-10 overflow-hidden shadow-sm">
                <div className="absolute inset-0 pointer-events-none opacity-[0.04] mix-blend-overlay z-0" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")" }} />
                <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_80%_0%,rgba(61,107,82,0.4)_0%,transparent_50%)] pointer-events-none" />

                <div className="relative z-10 flex flex-col md:flex-row justify-between items-start gap-8">
                    <div className="flex flex-col gap-4">
                        <h1 className="text-[3rem] leading-tight tracking-tight font-serif italic text-linen">Methodology Glossary</h1>
                        <p className="text-linen/70 font-sans text-lg max-w-xl">
                            A curated reference of carbon market terminology — from additionality to vintages.
                        </p>
                    </div>
                    <div className="font-mono text-xs bg-linen/10 px-4 py-2 rounded-full border border-linen/10 flex items-center gap-2">
                        <BookOpen size={14} className="opacity-60" />
                        <span className="font-medium text-linen">{glossaryTerms.length} terms</span>
                    </div>
                </div>
            </div>

            {/* Search + Filters */}
            <div className="page-stagger flex flex-col gap-4">
                <div className="relative max-w-md">
                    <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate/40" />
                    <input
                        type="text"
                        placeholder="Search terms..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-11 pr-4 py-3 rounded-xl border border-mist bg-white text-slate font-sans text-sm focus:outline-none focus:ring-2 focus:ring-canopy/30 focus:border-canopy transition-colors"
                    />
                </div>
                <div className="flex flex-wrap gap-2">
                    {categories.map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setActiveCategory(cat)}
                            className={`px-4 py-2 rounded-full font-sans text-xs font-medium border transition-colors cursor-pointer ${activeCategory === cat
                                ? 'bg-canopy text-linen border-canopy'
                                : 'bg-white text-slate/60 border-mist hover:border-canopy hover:text-canopy'
                                }`}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
            </div>

            {/* Term Grid */}
            <div className="page-stagger grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredTerms.map((item) => (
                    <div key={item.term} className="bg-white border border-mist rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex items-start justify-between gap-4 mb-3">
                            <h3 className="font-serif italic text-xl text-slate">{item.term}</h3>
                            <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border shrink-0 ${categoryColors[item.category]}`}>
                                {item.category}
                            </span>
                        </div>
                        <p className="font-sans text-sm text-slate/70 leading-relaxed">{item.definition}</p>
                    </div>
                ))}
                {filteredTerms.length === 0 && (
                    <div className="col-span-2 text-center py-12 text-slate/40 font-sans">
                        No terms match your search.
                    </div>
                )}
            </div>
        </div>
    );
}
