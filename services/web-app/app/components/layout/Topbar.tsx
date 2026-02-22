import React, { useState, useEffect, useRef } from 'react';
import { Bell, LogOut, ShoppingCart, Leaf } from 'lucide-react';
import { useAuth } from '@clients/api/modules/phantom-token-handler-secured-api-client/AuthContext';
import { logout } from '@clients/api/client';
import { ErrorRenderer } from '@clients/api/modules/phantom-token-handler-secured-api-client/utilities/errorRenderer';
import { useUserResourcesQuery } from '~/modules/shared/queries/useUserResources';
import { useOrdersQuery } from '~/modules/shared/queries/useOrders';
import { useListingsQuery } from '~/modules/shared/queries/useListings';

export function Topbar() {
    const { userInfo, onLoggedOut } = useAuth();
    const { data: userData } = useUserResourcesQuery();
    const [time, setTime] = useState<string>('');
    const [initials, setInitials] = useState('');
    const [showDropdown, setShowDropdown] = useState(false);
    const [showNotifications, setShowNotifications] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const notificationsRef = useRef<HTMLDivElement>(null);

    const { data: orders } = useOrdersQuery();
    const { data: listingsData } = useListingsQuery();
    const recentOrders = (orders ?? []).slice(0, 5);
    const recentListings = (listingsData?.listings ?? []).slice(0, 5);

    const user = userData?.user;
    const companyName = user?.company_name || 'CarbonBridge User';
    const sector = user?.sector;
    const role = user?.role;
    const roleLabel = role === 'buyer' ? 'Buyer' : role === 'seller' ? 'Seller' : role === 'both' ? 'Buyer & Seller' : null;
    const tagLabel = [sector, roleLabel].filter(Boolean).join(' / ');

    useEffect(() => {
        const updateTime = () => {
            const now = new Date();
            setTime(now.toLocaleTimeString('en-GB', { timeZone: 'Europe/Stockholm', hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' CET');
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
            if (notificationsRef.current && !notificationsRef.current.contains(event.target as Node)) {
                setShowNotifications(false);
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
                <h1 className="font-sans font-medium text-lg tracking-tight">Welcome back, {companyName}.</h1>
                {tagLabel && (
                    <div className="mt-1">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sage/10 text-sage">
                            {tagLabel}
                        </span>
                    </div>
                )}
            </div>

            {/* Right side */}
            <div className="flex items-center gap-6">
                {/* Market Clock */}
                <div className="flex flex-col items-end">
                    <span className="font-mono text-sm font-medium tracking-tight text-slate ">{time || '00:00:00 CET'}</span>
                    <span className="text-xs text-slate/60 font-medium">Stockholm Session: Active</span>
                </div>

                {/* Notification Bell */}
                <div ref={notificationsRef} className="relative">
                    <button
                        onClick={() => setShowNotifications(!showNotifications)}
                        className="relative p-2 text-slate/80 hover:text-slate transition-colors cursor-pointer"
                    >
                        <Bell size={20} strokeWidth={1.5} />
                        {(recentOrders.length > 0 || recentListings.length > 0) && (
                            <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-ember rounded-full border-2 border-white" />
                        )}
                    </button>
                    {showNotifications && (
                        <div className="absolute top-12 right-0 w-[360px] bg-white rounded-xl border border-mist shadow-lg overflow-hidden">
                            <div className="px-4 py-3 border-b border-mist">
                                <p className="text-sm font-semibold text-slate">Recent Activity</p>
                            </div>
                            <div className="max-h-[400px] overflow-y-auto">
                                {recentOrders.length === 0 && recentListings.length === 0 && (
                                    <div className="px-4 py-8 text-center text-sm text-slate/50">
                                        No recent activity
                                    </div>
                                )}

                                {recentOrders.length > 0 && (
                                    <>
                                        <div className="px-4 py-2 bg-linen/50">
                                            <p className="text-xs font-medium text-slate/60 uppercase tracking-wide">Transactions</p>
                                        </div>
                                        {recentOrders.map((order) => (
                                            <div key={order.id} className="flex items-start gap-3 px-4 py-3 border-b border-mist/50 hover:bg-linen/30 transition-colors">
                                                <div className="mt-0.5 w-8 h-8 rounded-full bg-canopy/10 flex items-center justify-center flex-shrink-0">
                                                    <ShoppingCart size={14} className="text-canopy" />
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex items-center justify-between gap-2">
                                                        <p className="text-sm font-medium text-slate truncate">
                                                            Order &middot; {order.line_items.length} item{order.line_items.length !== 1 ? 's' : ''}
                                                        </p>
                                                        <span className={`flex-shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${
                                                            order.status === 'completed' ? 'bg-canopy/10 text-canopy' :
                                                            order.status === 'confirmed' ? 'bg-sky-100 text-sky-700' :
                                                            order.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                                                            order.status === 'cancelled' ? 'bg-red-100 text-red-600' :
                                                            'bg-slate/10 text-slate/60'
                                                        }`}>
                                                            {order.status}
                                                        </span>
                                                    </div>
                                                    <p className="text-xs text-slate/50 mt-0.5">
                                                        {order.total_eur.toLocaleString('en-EU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} EUR
                                                        {order.line_items.reduce((sum, li) => sum + li.quantity, 0).toLocaleString()} tCO₂
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </>
                                )}

                                {recentListings.length > 0 && (
                                    <>
                                        <div className="px-4 py-2 bg-linen/50">
                                            <p className="text-xs font-medium text-slate/60 uppercase tracking-wide">Marketplace Listings</p>
                                        </div>
                                        {recentListings.map((listing) => (
                                            <div key={listing.id} className="flex items-start gap-3 px-4 py-3 border-b border-mist/50 hover:bg-linen/30 transition-colors">
                                                <div className="mt-0.5 w-8 h-8 rounded-full bg-sage/10 flex items-center justify-center flex-shrink-0">
                                                    <Leaf size={14} className="text-sage" />
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex items-center justify-between gap-2">
                                                        <p className="text-sm font-medium text-slate truncate">{listing.project_name}</p>
                                                        <span className={`flex-shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${
                                                            listing.status === 'active' ? 'bg-canopy/10 text-canopy' :
                                                            listing.status === 'sold_out' ? 'bg-slate/10 text-slate/60' :
                                                            listing.status === 'draft' ? 'bg-amber-100 text-amber-700' :
                                                            'bg-slate/10 text-slate/60'
                                                        }`}>
                                                            {listing.status === 'sold_out' ? 'sold out' : listing.status}
                                                        </span>
                                                    </div>
                                                    <p className="text-xs text-slate/50 mt-0.5">
                                                        {listing.quantity_tonnes.toLocaleString()} tCO₂ &middot; {listing.price_per_tonne_eur.toLocaleString('en-EU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} EUR/t
                                                        {listing.vintage_year ? ` &middot; ${listing.vintage_year}` : ''}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </>
                                )}
                            </div>
                        </div>
                    )}
                </div>



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
                                    {user?.company_name && (
                                        <p className="text-xs text-slate/50 truncate mt-0.5">
                                            {user.company_name}
                                        </p>
                                    )}
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
