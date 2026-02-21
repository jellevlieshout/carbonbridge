import React from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { Outlet } from 'react-router';

export default function DashboardLayout() {
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
