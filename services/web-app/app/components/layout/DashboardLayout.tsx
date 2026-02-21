import React from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { Outlet, Navigate } from 'react-router';
import { useAuth } from '@clients/api/modules/phantom-token-handler-secured-api-client/AuthContext';
import { useUserResourcesQuery } from '~/modules/shared/queries/useUserResources';

export default function DashboardLayout() {
    const { isLoggedIn, isPageLoaded } = useAuth();
    const { data: userData, isLoading } = useUserResourcesQuery({ enabled: isLoggedIn });

    // Redirect to login if not authenticated
    if (isPageLoaded && !isLoggedIn) {
        return <Navigate to="/" replace />;
    }

    // While loading user data, show a minimal loading state
    if (!isPageLoaded || isLoading) {
        return (
            <div className="min-h-screen bg-linen flex items-center justify-center">
                <div className="w-6 h-6 border-2 border-canopy/30 border-t-canopy rounded-full animate-spin" />
            </div>
        );
    }

    // Redirect to onboarding if user hasn't completed it
    if (userData?.user && !userData.user.company_name) {
        return <Navigate to="/onboarding" replace />;
    }

    return (
        <div className="min-h-screen bg-linen selection:bg-ember/20 selection:text-slate">
            {/* Fixed Navigation Rail */}
            <Sidebar />

            {/* Main Content Area */}
            <main className="ml-[80px] min-h-screen flex flex-col relative z-10">
                <Topbar />

                {/* Scrollable container with top padding matching topbar height */}
                <div className="flex-1 pt-20 px-8 pb-32 max-w-7xl mx-auto w-full">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}
