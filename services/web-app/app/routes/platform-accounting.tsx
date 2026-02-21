import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { FileSpreadsheet, FileText, FileCode, Download, Calendar, CheckCircle2 } from 'lucide-react';
import type { Route } from "./+types/platform-accounting";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Carbon Accounting Export" },
        { name: "description", content: "Export your carbon credit data in audit-ready formats for compliance and reporting." },
    ];
}

const exportFormats = [
    {
        icon: FileSpreadsheet,
        title: 'CSV / Excel',
        description: 'Flat tabular export of all transactions, credits, and retirements. Compatible with Excel, Google Sheets, and any BI tool.',
        extension: '.csv',
        color: 'text-emerald-600 bg-emerald-50 border-emerald-200',
    },
    {
        icon: FileText,
        title: 'PDF Report',
        description: 'Formatted carbon accounting report with executive summary, charts, and transaction breakdown. Print-ready for board presentations.',
        extension: '.pdf',
        color: 'text-rose-600 bg-rose-50 border-rose-200',
    },
    {
        icon: FileCode,
        title: 'XBRL / iXBRL',
        description: 'Machine-readable structured disclosure format for regulatory submissions. Aligned with ESRS E1 and SEC climate rule taxonomies.',
        extension: '.xbrl',
        color: 'text-sky-600 bg-sky-50 border-sky-200',
    },
];

const frameworks = [
    { name: 'GHG Protocol', scope: 'Scope 1, 2 & 3', status: 'Aligned' },
    { name: 'CDP', scope: 'Climate Change Questionnaire', status: 'Aligned' },
    { name: 'TCFD', scope: 'Metrics & Targets', status: 'Aligned' },
    { name: 'CSRD / ESRS E1', scope: 'Climate Change Standard', status: 'Aligned' },
    { name: 'SBTi', scope: 'Beyond Value Chain Mitigation', status: 'Compatible' },
    { name: 'ISO 14064-1', scope: 'GHG Inventory', status: 'Compatible' },
];

const periods = ['Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024', 'FY 2024', 'Custom Range'];

export default function PlatformAccountingPage() {
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
                    <h1 className="text-[3rem] leading-tight tracking-tight font-serif italic text-linen">Carbon Accounting Export</h1>
                    <p className="text-linen/70 font-sans text-lg max-w-2xl">
                        Generate audit-ready reports and machine-readable disclosures for your carbon credit portfolio. Aligned with major compliance frameworks.
                    </p>
                </div>
            </div>

            {/* Period Selector */}
            <div className="page-stagger flex flex-col gap-4">
                <h2 className="text-xl font-semibold text-slate flex items-center gap-2">
                    <Calendar size={20} className="text-canopy" /> Reporting Period
                </h2>
                <div className="flex flex-wrap gap-3">
                    {periods.map((period) => (
                        <button
                            key={period}
                            className={`px-5 py-2.5 rounded-full font-sans text-sm border transition-colors cursor-pointer ${period === 'FY 2024'
                                ? 'bg-canopy text-linen border-canopy'
                                : 'bg-white text-slate/70 border-mist hover:border-canopy hover:text-canopy'
                                }`}
                        >
                            {period}
                        </button>
                    ))}
                </div>
            </div>

            {/* Export Format Cards */}
            <div className="page-stagger grid grid-cols-1 md:grid-cols-3 gap-6">
                {exportFormats.map((format) => (
                    <div key={format.title} className="bg-white border border-mist rounded-2xl p-8 shadow-sm flex flex-col gap-6 hover:shadow-md transition-shadow">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${format.color}`}>
                            <format.icon size={24} />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-sans font-bold text-slate text-lg mb-2">{format.title}</h3>
                            <p className="font-sans text-slate/60 text-sm leading-relaxed">{format.description}</p>
                        </div>
                        <button className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-canopy/5 text-canopy font-medium text-sm border border-canopy/20 hover:bg-canopy hover:text-linen transition-colors cursor-pointer">
                            <Download size={16} />
                            Export {format.extension}
                        </button>
                    </div>
                ))}
            </div>

            {/* Compliance Frameworks */}
            <div className="page-stagger flex flex-col gap-4">
                <h2 className="text-xl font-semibold text-slate">Compliance Framework Alignment</h2>
                <p className="text-slate/60 font-sans text-sm max-w-2xl">
                    CarbonBridge exports are structured to satisfy disclosure requirements across these international standards and frameworks.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-2">
                    {frameworks.map((fw) => (
                        <div key={fw.name} className="bg-white border border-mist rounded-2xl p-6 shadow-sm flex items-start gap-4">
                            <CheckCircle2 size={20} className="text-emerald-500 mt-0.5 shrink-0" />
                            <div>
                                <h4 className="font-sans font-semibold text-slate text-sm">{fw.name}</h4>
                                <p className="text-xs text-slate/50 font-sans mt-1">{fw.scope}</p>
                                <span className="inline-block mt-2 text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200">
                                    {fw.status}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
