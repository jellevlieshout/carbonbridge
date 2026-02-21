import React, { useState, useEffect, useRef } from 'react';
import { Bell, Plus, LogOut } from 'lucide-react';
import { useAuth } from '@clients/api/modules/phantom-token-handler-secured-api-client/AuthContext';
import { logout } from '@clients/api/client';
import { ErrorRenderer } from '@clients/api/modules/phantom-token-handler-secured-api-client/utilities/errorRenderer';

export function Topbar() {
    const { userInfo, onLoggedOut } = useAuth();
    const [time, setTime] = useState<string>('');
    const [initials, setInitials] = useState('');
    const [showDropdown, setShowDropdown] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const updateTime = () => {
            const now = new Date();
            setTime(now.toLocaleTimeString('en-GB', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' UTC');
        };
        updateTime();
        const interval = setInterval(updateTime, 1000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (userInfo) {
            if (userInfo.name.givenName && userInfo.name.familyName) {
                const first = userInfo.name.givenName.charAt(0).toUpperCase();
                const last = userInfo.name.familyName.charAt(0).toUpperCase();
                setInitials(`${first}${last}`);
            } else if (userInfo.sub) {
                setInitials(userInfo.sub.substring(0, 2).toUpperCase());
            } else {
                setInitials('??');
            }
        }
    }, [userInfo]);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setShowDropdown(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    async function handleLogout() {
        try {
            const logoutResponse = await logout();
            onLoggedOut();
            if (logoutResponse.logoutUrl) {
                window.location.href = logoutResponse.logoutUrl;
            } else {
                window.location.href = window.location.origin;
            }
        } catch (e: any) {
            if (e.status === 401) {
                onLoggedOut();
                return;
            }
            alert(ErrorRenderer.toDisplayFormat(e));
        }
    }

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
            <div className="flex items-center gap-6">
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

                {/* Profile Dropdown */}
                <div ref={dropdownRef} className="relative">
                    <button
                        onClick={() => setShowDropdown(!showDropdown)}
                        className="w-10 h-10 rounded-full bg-canopy text-linen flex items-center justify-center cursor-pointer font-semibold text-sm select-none border-0 hover:bg-canopy/90 transition-colors"
                    >
                        {initials}
                    </button>
                    {showDropdown && (
                        <div className="absolute top-12 right-0 min-w-[180px] bg-white rounded-xl border border-mist shadow-lg overflow-hidden">
                            {userInfo && (
                                <div className="px-4 py-3 border-b border-mist">
                                    <p className="text-sm font-medium text-slate truncate">
                                        {userInfo.name.givenName} {userInfo.name.familyName}
                                    </p>
                                </div>
                            )}
                            <button
                                onClick={handleLogout}
                                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-slate/80 hover:bg-linen hover:text-slate transition-colors cursor-pointer bg-transparent border-0"
                            >
                                <LogOut size={16} strokeWidth={1.5} />
                                Log out
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
}
