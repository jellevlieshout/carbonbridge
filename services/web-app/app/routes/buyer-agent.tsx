import React from 'react';
import { AgentActivityPanel } from '../components/dashboard/AgentActivityPanel';
import type { Route } from "./+types/buyer-agent";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Buyer Agent" },
        { name: "description", content: "Configure and monitor your autonomous buying agent." },
    ];
}

export default function BuyerAgentPage() {
    return (
        <div className="flex flex-col gap-10 w-full animate-in fade-in duration-700">
            <AgentActivityPanel />
        </div>
    );
}
