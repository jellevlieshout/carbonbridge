import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { Shield, ExternalLink, Globe, FileCheck } from 'lucide-react';
import type { Route } from "./+types/trust-registry";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Registry Documents" },
        { name: "description", content: "Explore the carbon credit registries and documentation standards supported by CarbonBridge." },
    ];
}

const registries = [
    {
        name: 'Verra (VCS)',
        fullName: 'Verified Carbon Standard',
        description: 'The world\'s most widely used voluntary carbon offset program. Verra\'s VCS Program issues Verified Carbon Units (VCUs) across forestry, energy, transport, and industrial sectors. Over 1,800 certified projects in 80+ countries.',
        stats: { projects: '1,800+', credits: '1B+ VCUs', countries: '80+' },
        color: 'border-sky-200 bg-sky-50',
        iconColor: 'text-sky-600',
        documents: ['VCS Standard v4.5', 'Program Guide', 'Methodology Requirements', 'Registration & Issuance Process'],
    },
    {
        name: 'Gold Standard',
        fullName: 'Gold Standard for the Global Goals',
        description: 'Founded by WWF, Gold Standard certifies projects that deliver the highest levels of environmental integrity and sustainable development co-benefits. Particularly strong in clean energy and cookstove projects across Africa and Asia.',
        stats: { projects: '2,700+', credits: '300M+', countries: '90+' },
        color: 'border-amber-200 bg-amber-50',
        iconColor: 'text-amber-600',
        documents: ['Gold Standard Principles & Requirements', 'Activity Requirements', 'Safeguarding Principles', 'SDG Impact Tool'],
    },
    {
        name: 'ACR',
        fullName: 'American Carbon Registry',
        description: 'A nonprofit enterprise of Winrock International, ACR is a leading carbon offset registry for voluntary and pre-compliance markets. Strong focus on North American forestry, soil carbon, and ozone-depleting substance destruction.',
        stats: { projects: '500+', credits: '200M+', countries: '15+' },
        color: 'border-emerald-200 bg-emerald-50',
        iconColor: 'text-emerald-600',
        documents: ['ACR Standard v8.0', 'Validation & Verification Requirements', 'Registry Terms of Use', 'Buffer Pool Guidelines'],
    },
    {
        name: 'CAR',
        fullName: 'Climate Action Reserve',
        description: 'A North American registry focused on ensuring environmental integrity, transparency, and financial value in carbon markets. Known for rigorous, sector-specific protocols for forestry, livestock, and landfill gas projects.',
        stats: { projects: '450+', credits: '180M+', countries: '3' },
        color: 'border-violet-200 bg-violet-50',
        iconColor: 'text-violet-600',
        documents: ['Reserve Offset Program Manual', 'Verification Program Manual', 'Forest Protocol v5.0', 'Risk of Reversal Rating Report'],
    },
    {
        name: 'ART',
        fullName: 'Architecture for REDD+ Transactions',
        description: 'A standard specifically designed for large-scale jurisdictional REDD+ programs. Issues TREES credits (The REDD+ Environmental Excellence Standard) at national and subnational scale, enabling sovereign-level carbon accounting.',
        stats: { projects: '20+', credits: 'Emerging', countries: '15+' },
        color: 'border-teal-200 bg-teal-50',
        iconColor: 'text-teal-600',
        documents: ['TREES Standard v2.0', 'TREES Registration Document', 'Validation & Verification Requirements', 'Crediting Level Assessment'],
    },
];

export default function TrustRegistryPage() {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const ctx = gsap.context(() => {
            gsap.fromTo(".page-stagger", { y: 30, opacity: 0 }, { y: 0, opacity: 1, stagger: 0.12, duration: 0.8, ease: "power3.out", delay: 0.1 });
        }, containerRef);
        return () => ctx.revert();
    }, []);

    return (
        <div ref={containerRef} className="flex flex-col gap-10 w-full animate-in fade-in duration-700">
            {/* Hero */}
            <div className="page-stagger relative w-full rounded-[2rem] bg-canopy text-linen p-10 overflow-hidden shadow-sm">
                <div className="absolute inset-0 pointer-events-none opacity-[0.04] mix-blend-overlay z-0" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")" }} />
                <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_80%_0%,rgba(61,107,82,0.4)_0%,transparent_50%)] pointer-events-none" />

                <div className="relative z-10 flex flex-col gap-4">
                    <h1 className="text-[3rem] leading-tight tracking-tight font-serif italic text-linen">Registry Documents</h1>
                    <p className="text-linen/70 font-sans text-lg max-w-2xl">
                        CarbonBridge sources credits exclusively from globally recognized carbon registries. Explore the standards and documentation that underpin every credit on our platform.
                    </p>
                </div>
            </div>

            {/* Registry Cards */}
            <div className="page-stagger flex flex-col gap-6">
                {registries.map((registry) => (
                    <div key={registry.name} className={`bg-white border border-mist rounded-2xl shadow-sm overflow-hidden hover:shadow-md transition-shadow`}>
                        <div className="p-8 flex flex-col lg:flex-row gap-8">
                            {/* Left: Info */}
                            <div className="flex-1">
                                <div className="flex items-center gap-4 mb-4">
                                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${registry.color}`}>
                                        <Shield size={24} className={registry.iconColor} />
                                    </div>
                                    <div>
                                        <h3 className="font-sans font-bold text-slate text-xl">{registry.name}</h3>
                                        <p className="text-xs text-slate/50 font-sans">{registry.fullName}</p>
                                    </div>
                                </div>
                                <p className="font-sans text-sm text-slate/70 leading-relaxed mb-6">{registry.description}</p>
                                <div className="flex flex-wrap gap-3">
                                    <div className="font-mono text-xs bg-mist/50 px-3 py-1.5 rounded-lg flex items-center gap-2">
                                        <Globe size={12} className="text-slate/40" />
                                        <span className="text-slate/60">{registry.stats.countries} countries</span>
                                    </div>
                                    <div className="font-mono text-xs bg-mist/50 px-3 py-1.5 rounded-lg flex items-center gap-2">
                                        <FileCheck size={12} className="text-slate/40" />
                                        <span className="text-slate/60">{registry.stats.projects} projects</span>
                                    </div>
                                    <div className="font-mono text-xs bg-mist/50 px-3 py-1.5 rounded-lg flex items-center gap-2">
                                        <span className="text-slate/60">{registry.stats.credits} issued</span>
                                    </div>
                                </div>
                            </div>

                            {/* Right: Documents */}
                            <div className="lg:w-72 shrink-0 flex flex-col gap-2">
                                <h4 className="text-xs uppercase font-bold tracking-wider text-slate/40 mb-2">Key Documents</h4>
                                {registry.documents.map((doc) => (
                                    <button key={doc} className="flex items-center gap-3 px-4 py-3 rounded-xl bg-mist/30 hover:bg-canopy/5 hover:text-canopy text-slate/70 text-sm font-sans transition-colors text-left cursor-pointer group">
                                        <FileCheck size={14} className="shrink-0 opacity-40 group-hover:opacity-100 transition-opacity" />
                                        <span className="flex-1">{doc}</span>
                                        <ExternalLink size={12} className="shrink-0 opacity-0 group-hover:opacity-60 transition-opacity" />
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
