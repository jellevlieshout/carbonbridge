import React from 'react';
import { CreditShufflerTile } from './CreditShufflerTile';
import { AgentStreamTile } from './AgentStreamTile';
import { WizardProgressTile } from './WizardProgressTile';

export function CoreTileRow() {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 w-full h-[400px]">
            <CreditShufflerTile />
            <AgentStreamTile />
            <WizardProgressTile />
        </div>
    );
}
