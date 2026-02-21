import React from 'react';

interface AuthenticatedHomeViewProps {
    userResources: any;
}

export function AuthenticatedHomeView({
    userResources
}: AuthenticatedHomeViewProps) {

    if (!userResources) return null; // Or skeleton

    return (
        <>
            <div className="mx-10">
                <h2>Welcome to CarbonBridge Lab</h2>
            </div>
        </>
    );
}
