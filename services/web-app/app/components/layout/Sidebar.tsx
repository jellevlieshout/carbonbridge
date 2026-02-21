import React, { useState } from 'react';
import { LayoutDashboard, Leaf, ShoppingCart, Activity, FileText, Settings, Bot, Sparkles, List } from 'lucide-react';
import { NavLink } from 'react-router';
import { Logo } from '~/modules/shared/components/Logo';

const navItems = [
    { label: 'Overview', icon: LayoutDashboard, href: '/buyer/dashboard' },
    { label: 'Purchase Wizard', icon: Sparkles, href: '/buyer/wizard' },
    { label: 'My Listings', icon: List, href: '/seller/listings' },
    { label: 'My Credits', icon: Leaf, href: '/buyer/credits' },
    { label: 'Marketplace', icon: ShoppingCart, href: '/marketplace' },
    { label: 'Agent Activity', icon: Activity, href: '/buyer/agent' },
    { label: 'Reports', icon: FileText, href: '/buyer/reports' },
    { label: 'Settings', icon: Settings, href: '/buyer/settings' },
];

export function Sidebar() {
    const [isHovered, setIsHovered] = useState(false);

    return (
        <aside
            className={`fixed top-0 left-0 h-screen z-40 bg-canopy text-linen flex flex-col transition-[width] duration-300 ease-spring ${isHovered ? 'w-[240px]' : 'w-[80px]'
                }`}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            {/* Noise Texture Overlay */}
            <div
                className="absolute inset-0 pointer-events-none opacity-[0.06] mix-blend-overlay z-0"
                style={{
                    backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")"
                }}
            />

            <div className="relative z-10 flex flex-col h-full w-full overflow-hidden">
                {/* Header / Logo */}
                <div className="h-20 flex items-center px-6 shrink-0 font-semibold font-sans tracking-tight">
                    <NavLink to="/" className="flex items-center gap-4 text-linen whitespace-nowrap no-underline">
                        <div className="w-8 h-8 rounded-lg bg-linen/10 flex items-center justify-center shrink-0 text-sm">
                            CB
                        </div>
                        <span className={`transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
                            <Logo size="sm" variant="light" />
                        </span>
                    </NavLink>
                </div>

                {/* Navigation */}
                <nav className="flex-1 px-4 py-8 space-y-2">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.href}
                            to={item.href}
                            className={({ isActive }) =>
                                `flex items-center gap-4 h-12 px-2 rounded-xl transition-colors ${isActive ? 'bg-linen text-canopy' : 'text-linen/80 hover:text-linen hover:bg-linen/10'
                                }`
                            }
                        >
                            <div className="w-8 flex items-center justify-center shrink-0">
                                <item.icon size={20} className="stroke-[1.5]" />
                            </div>
                            <span className={`font-medium tracking-tight whitespace-nowrap transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
                                {item.label}
                            </span>
                        </NavLink>
                    ))}
                </nav>

                {/* Bottom Actions */}
                <div className="p-4 space-y-6 shrink-0 pb-8">
                    {/* Agent Shortcut Button */}
                    <button className="relative w-full h-12 flex items-center gap-4 px-2 rounded-xl bg-ember text-linen cursor-pointer overflow-hidden group">
                        {/* Pulsing ring behind icon */}
                        <div className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-linen/30 animate-ping" />

                        <div className="relative z-10 w-8 flex items-center justify-center shrink-0">
                            <Bot size={20} className="stroke-[1.5]" />
                        </div>
                        <span className={`relative z-10 font-medium whitespace-nowrap transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
                            Carbon Agent
                        </span>
                    </button>

                    {/* Market Open Status */}
                    <div className="flex items-center gap-4 px-2 h-10">
                        <div className="w-8 flex items-center justify-center shrink-0">
                            <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse ring-2 ring-emerald-400/30" />
                        </div>
                        <div className={`flex flex-col whitespace-nowrap transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
                            <span className="text-xs text-linen/60 font-medium">Market Open</span>
                            <span className="font-mono text-xs text-linen tracking-tight">VCM Ref: €14.20/t</span>
                        </div>
                    </div>
                </div>
            </div>
        </aside>
    );
}
