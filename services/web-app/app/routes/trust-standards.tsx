import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { BadgeCheck, Search as SearchIcon, ClipboardCheck, BarChart3, ShieldCheck, FileSearch, Users, Scale } from 'lucide-react';
import type { Route } from "./+types/trust-standards";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Verification Standards" },
        { name: "description", content: "Understand the verification standards and quality assurance processes behind every CarbonBridge credit." },
    ];
}

const verificationSteps = [
    {
        icon: SearchIcon,
        title: 'Project Design & Feasibility',
        description: 'Projects submit a Project Design Document (PDD) describing the methodology, baseline scenario, additionality demonstration, and monitoring plan.',
        standard: 'ISO 14064-2',
        duration: '3–6 months',
    },
    {
        icon: ClipboardCheck,
        title: 'Third-Party Validation',
        description: 'An accredited Validation/Verification Body (VVB) independently reviews the PDD, conducts site visits, and assesses conformity with the chosen methodology.',
        standard: 'ISO 14065 / IAF',
        duration: '2–4 months',
    },
    {
        icon: BarChart3,
        title: 'Monitoring & Data Collection',
        description: 'Project developers implement the monitoring plan, collecting emissions data at defined intervals. Satellite imagery, sensor networks, and field sampling may be used.',
        standard: 'MRV Framework',
        duration: 'Ongoing',
    },
    {
        icon: FileSearch,
        title: 'Verification & Audit',
        description: 'The VVB returns to verify actual emission reductions against the monitoring data. Includes data quality checks, materiality analysis, and uncertainty assessments.',
        standard: 'ISO 14064-3',
        duration: '1–3 months',
    },
    {
        icon: ShieldCheck,
        title: 'Registry Issuance',
        description: 'Upon successful verification, the registry issues serialized carbon credits. Each credit receives a unique ID, vintage year, and is recorded on the public registry ledger.',
        standard: 'VCS / Gold Standard',
        duration: '2–6 weeks',
    },
    {
        icon: Users,
        title: 'Market Listing & Due Diligence',
        description: 'CarbonBridge applies additional screening: project risk scoring, co-benefit assessment, permanence buffer analysis, and stakeholder consultation review.',
        standard: 'CarbonBridge Internal',
        duration: '1–2 weeks',
    },
];

const qualityPrinciples = [
    { title: 'Real', description: 'Emission reductions represent actual, measurable atmospheric impact — not hypothetical or projected savings.' },
    { title: 'Additional', description: 'The reduction would not have occurred without carbon credit revenue providing the necessary financial incentive.' },
    { title: 'Permanent', description: 'Sequestered carbon remains stored for the long term, with buffer pools and insurance protecting against reversals.' },
    { title: 'Independently Verified', description: 'All reductions are confirmed by accredited third-party auditors with no financial ties to the project.' },
    { title: 'Unique', description: 'Each credit is tracked with a serial number and retired once, preventing double counting across jurisdictions.' },
    { title: 'Conservative', description: 'When facing uncertainty, methodologies use conservative estimates that understate rather than overstate reductions.' },
];

export default function TrustStandardsPage() {
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
                    <h1 className="text-[3rem] leading-tight tracking-tight font-serif italic text-linen">Verification Standards</h1>
                    <p className="text-linen/70 font-sans text-lg max-w-2xl">
                        Every carbon credit on CarbonBridge passes through a rigorous multi-stage verification pipeline. Here's how the integrity of each tonne is guaranteed.
                    </p>
                </div>
            </div>

            {/* Verification Pipeline */}
            <div className="page-stagger flex flex-col gap-0">
                <h2 className="text-xl font-semibold text-slate mb-6">Verification Pipeline</h2>
                <div className="relative">
                    {/* Vertical line */}
                    <div className="absolute left-6 top-6 bottom-6 w-px bg-mist" />

                    <div className="flex flex-col gap-1">
                        {verificationSteps.map((step, index) => (
                            <div key={step.title} className="relative flex gap-6 items-start group">
                                {/* Dot */}
                                <div className="relative z-10 w-12 h-12 rounded-xl bg-white border border-mist flex items-center justify-center shadow-sm group-hover:border-canopy group-hover:shadow-md transition-all shrink-0">
                                    <step.icon size={20} className="text-canopy" />
                                </div>
                                {/* Content */}
                                <div className="bg-white border border-mist rounded-2xl p-6 shadow-sm flex-1 mb-4 hover:shadow-md transition-shadow">
                                    <div className="flex items-start justify-between gap-4 mb-2">
                                        <div>
                                            <span className="text-[10px] uppercase font-bold tracking-wider text-slate/30 font-mono">Step {index + 1}</span>
                                            <h3 className="font-sans font-semibold text-slate text-lg">{step.title}</h3>
                                        </div>
                                        <div className="flex gap-2 shrink-0">
                                            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-canopy/5 text-canopy border border-canopy/20">
                                                {step.standard}
                                            </span>
                                            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-mist text-slate/50 border border-mist">
                                                {step.duration}
                                            </span>
                                        </div>
                                    </div>
                                    <p className="font-sans text-sm text-slate/70 leading-relaxed">{step.description}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Quality Principles */}
            <div className="page-stagger flex flex-col gap-6">
                <div>
                    <h2 className="text-xl font-semibold text-slate mb-2">Core Quality Principles</h2>
                    <p className="text-slate/60 font-sans text-sm max-w-2xl">
                        CarbonBridge credits adhere to the ICVCM Core Carbon Principles. Every credit on our platform meets all six criteria.
                    </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {qualityPrinciples.map((principle) => (
                        <div key={principle.title} className="bg-white border border-mist rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
                            <div className="flex items-center gap-3 mb-3">
                                <BadgeCheck size={20} className="text-canopy shrink-0" />
                                <h4 className="font-serif italic text-lg text-slate">{principle.title}</h4>
                            </div>
                            <p className="font-sans text-sm text-slate/70 leading-relaxed">{principle.description}</p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
