import React, { useState, useEffect } from 'react';
import { Bell, Plus } from 'lucide-react';

export function Topbar() {
    const [time, setTime] = useState<string>('');

    useEffect(() => {
        const updateTime = () => {
            const now = new Date();
            setTime(now.toLocaleTimeString('en-GB', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' UTC');
        };
        updateTime();
        const interval = setInterval(updateTime, 1000);
        return () => clearInterval(interval);
    }, []);

    return (
        <header className="fixed top-0 right-0 left-[80px] h-20 z-30 bg-white/70 backdrop-blur-md border-b border-mist flex items-center justify-between px-8 text-slate">
            {/* Left side */}
            <div className="flex flex-col justify-center">
                <h1 className="font-sans font-medium text-lg tracking-tight">Welcome back, Hargreaves & Sons.</h1>
                <div className="mt-1">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sage/10 text-sage">
                        Manufacturing / Scope 2
                    </span>
                </div>
            </div>

            {/* Right side */}
            <div className="flex items-center gap-8">
                {/* Market Clock */}
                <div className="flex flex-col items-end">
                    <span className="font-mono text-sm font-medium tracking-tight text-slate ">{time || '00:00:00 UTC'}</span>
                    <span className="text-xs text-slate/60 font-medium">London Session: Active</span>
                </div>

                {/* Notification Bell */}
                <button className="relative p-2 text-slate/80 hover:text-slate transition-colors cursor-pointer">
                    <Bell size={20} strokeWidth={1.5} />
                    <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-ember rounded-full border-2 border-white" />
                </button>

                {/* New Transaction Button */}
                <button className="magnetic-btn h-10 px-5 rounded-full bg-slate text-linen font-medium text-sm flex items-center gap-2 group cursor-pointer border-0">
                    <div className="magnetic-bg bg-ember" />
                    <Plus size={16} strokeWidth={2} className="relative z-10" />
                    <span className="relative z-10">New Transaction</span>
                </button>
            </div>
        </header>
    );
}
