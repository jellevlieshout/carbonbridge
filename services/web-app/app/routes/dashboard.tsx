import React from 'react';
import { HeroPanel } from '../components/dashboard/HeroPanel';
import { CoreTileRow } from '../components/dashboard/CoreTileRow';
import { MarketplaceSpotlight } from '../components/dashboard/MarketplaceSpotlight';
import { TransactionHistoryStack } from '../components/dashboard/TransactionHistoryStack';
import { AgentActivityPanel } from '../components/dashboard/AgentActivityPanel';
import { Footer } from '../components/dashboard/Footer';

export default function DashboardPage() {
    return (
        <div className="flex flex-col gap-10 w-full animate-in fade-in duration-700">
            <HeroPanel />
            <CoreTileRow />
            <MarketplaceSpotlight />
            <TransactionHistoryStack />
            <AgentActivityPanel />
            <Footer />
        </div>
    );
}
