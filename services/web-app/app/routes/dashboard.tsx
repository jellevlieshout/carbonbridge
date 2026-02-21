import React from 'react';
import { HeroPanel } from '../components/dashboard/HeroPanel';
import { CoreTileRow } from '../components/dashboard/CoreTileRow';
import { MarketplaceSpotlight } from '../components/dashboard/MarketplaceSpotlight';
import { TransactionHistoryStack } from '../components/dashboard/TransactionHistoryStack';
import { AgentConfigPanel } from '../components/dashboard/AgentConfigPanel';
import { Footer } from '../components/dashboard/Footer';

export default function DashboardPage() {
    return (
        <div className="flex flex-col gap-10 w-full animate-in fade-in duration-700">
            <HeroPanel />
            <CoreTileRow />
            <MarketplaceSpotlight />
            <TransactionHistoryStack />
            <AgentConfigPanel />
            <Footer />
        </div>
    );
}
