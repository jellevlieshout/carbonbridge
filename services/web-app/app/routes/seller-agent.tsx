import React from 'react';
import { SellerAdvisoryPanel } from '../components/seller/SellerAdvisoryPanel';
import { BarChart3, TrendingUp, ShieldCheck, Lightbulb } from 'lucide-react';
import type { Route } from "./+types/seller-agent";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Market Advisory" },
        { name: "description", content: "AI-powered pricing and market intelligence for your carbon credit listings." },
    ];
}

const CAPABILITIES = [
    { icon: BarChart3, label: 'Market Benchmarking', desc: 'Compares your listings against CarbonPlan OffsetsDB data' },
    { icon: TrendingUp, label: 'Pricing Intelligence', desc: 'Suggests optimal price bands based on project type and vintage' },
    { icon: ShieldCheck, label: 'Competitive Position', desc: 'Rates your listings as underpriced, competitive, or overpriced' },
    { icon: Lightbulb, label: 'Actionable Tips', desc: 'Per-listing recommendations to maximize sell-through rate' },
];

export default function SellerAgentPage() {
    return (
        <div className="flex flex-col gap-10 w-full animate-in fade-in duration-700 pb-12">
            {/* Page header */}
            <div className="flex flex-col gap-2">
                <h1 className="text-4xl font-bold tracking-tight text-foreground">Market Advisory</h1>
                <p className="text-muted-foreground text-lg max-w-2xl">
                    AI-powered pricing and market intelligence using CarbonPlan's OffsetsDB market context.
                </p>
            </div>

            {/* Capability pills */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {CAPABILITIES.map(({ icon: Icon, label, desc }) => (
                    <div key={label} className="flex flex-col gap-2 p-4 rounded-xl border border-border/40 bg-card/50">
                        <div className="flex items-center gap-2 text-primary">
                            <Icon size={15} />
                            <span className="text-xs font-semibold">{label}</span>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
                    </div>
                ))}
            </div>

            <SellerAdvisoryPanel />
        </div>
    );
}
