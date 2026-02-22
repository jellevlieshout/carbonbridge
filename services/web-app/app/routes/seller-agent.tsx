import React from 'react';
import { SellerAdvisoryPanel } from '../components/seller/SellerAdvisoryPanel';
import type { Route } from "./+types/seller-agent";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Seller Agent" },
        { name: "description", content: "AI-powered advisory for your carbon credit listings." },
    ];
}

export default function SellerAgentPage() {
    return (
        <div className="flex flex-col gap-10 w-full animate-in fade-in duration-700">
            <SellerAdvisoryPanel />
        </div>
    );
}
