import React from 'react';
import {
    Leaf, Wind, Flame, Factory, Zap, Tractor, Sun, HelpCircle,
    Pause, Play, Archive, Pencil,
    ShieldCheck, AlertTriangle, MapPin, Calendar,
} from 'lucide-react';
import type { Listing } from '@clients/api/listings';

// Project type → icon + color mapping
const projectTypeConfig: Record<string, { icon: typeof Leaf; bg: string; color: string }> = {
    afforestation:      { icon: Leaf,       bg: 'bg-emerald-500/10', color: 'text-emerald-600' },
    renewable:          { icon: Wind,       bg: 'bg-sky-500/10',     color: 'text-sky-600' },
    cookstoves:         { icon: Flame,      bg: 'bg-amber-500/10',   color: 'text-amber-600' },
    methane_capture:    { icon: Factory,    bg: 'bg-purple-500/10',  color: 'text-purple-600' },
    fuel_switching:     { icon: Zap,        bg: 'bg-orange-500/10',  color: 'text-orange-600' },
    energy_efficiency:  { icon: Sun,        bg: 'bg-yellow-500/10',  color: 'text-yellow-600' },
    agriculture:        { icon: Tractor,    bg: 'bg-lime-500/10',    color: 'text-lime-600' },
    other:              { icon: HelpCircle, bg: 'bg-slate/5',        color: 'text-slate/50' },
};

const statusConfig: Record<string, { label: string; bg: string; text: string; dot: string }> = {
    active:   { label: 'Active',   bg: 'bg-emerald-500/10', text: 'text-emerald-700', dot: 'bg-emerald-500' },
    paused:   { label: 'Paused',   bg: 'bg-amber-500/10',   text: 'text-amber-700',   dot: 'bg-amber-500' },
    draft:    { label: 'Draft',    bg: 'bg-slate/10',        text: 'text-slate/60',     dot: 'bg-slate/40' },
    sold_out: { label: 'Sold Out', bg: 'bg-red-500/10',      text: 'text-red-600',      dot: 'bg-red-500' },
};

const verificationConfig: Record<string, { label: string; icon: typeof ShieldCheck; color: string }> = {
    verified: { label: 'Verified', icon: ShieldCheck,    color: 'text-emerald-600' },
    pending:  { label: 'Pending',  icon: AlertTriangle,  color: 'text-amber-500' },
    failed:   { label: 'Failed',   icon: AlertTriangle,  color: 'text-red-500' },
};

interface SellerListingCardProps {
    listing: Listing;
    onEdit: (listing: Listing) => void;
    onStatusChange: (id: string, status: string) => void;
    onArchive: (id: string) => void;
}

export function SellerListingCard({ listing, onEdit, onStatusChange, onArchive }: SellerListingCardProps) {
    const available = listing.quantity_tonnes - listing.quantity_reserved - listing.quantity_sold;
    const soldPercent = listing.quantity_tonnes > 0
        ? Math.round((listing.quantity_sold / listing.quantity_tonnes) * 100)
        : 0;

    const projectType = projectTypeConfig[listing.project_type] || projectTypeConfig.other;
    const ProjectIcon = projectType.icon;
    const status = statusConfig[listing.status] || statusConfig.draft;
    const verification = verificationConfig[listing.verification_status] || verificationConfig.pending;
    const VerifIcon = verification.icon;

    return (
        <div className="listing-card group bg-white rounded-[1.5rem] border border-mist overflow-hidden hover:shadow-lg transition-all duration-300">
            {/* Top accent bar based on project type */}
            <div className={`h-1 ${projectType.bg.replace('/10', '/40')}`} />

            <div className="p-7">
                {/* Header row */}
                <div className="flex items-start justify-between gap-4 mb-5">
                    {/* Left: icon + name + metadata */}
                    <div className="flex gap-4 flex-1 min-w-0">
                        <div className={`w-12 h-12 rounded-xl ${projectType.bg} flex items-center justify-center shrink-0`}>
                            <ProjectIcon size={22} className={projectType.color} strokeWidth={1.5} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3 mb-1.5">
                                <h3 className="font-sans font-bold text-lg text-slate truncate">{listing.project_name}</h3>
                                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}`}>
                                    <span className={`w-1.5 h-1.5 rounded-full ${status.dot}`} />
                                    {status.label}
                                </span>
                            </div>
                            <div className="flex items-center gap-3 text-sm text-slate/50">
                                <span className="font-mono text-xs">{listing.registry_name}</span>
                                {listing.project_country && (
                                    <>
                                        <span className="text-mist">·</span>
                                        <span className="flex items-center gap-1 font-mono text-xs">
                                            <MapPin size={10} strokeWidth={1.5} />
                                            {listing.project_country}
                                        </span>
                                    </>
                                )}
                                {listing.vintage_year && (
                                    <>
                                        <span className="text-mist">·</span>
                                        <span className="flex items-center gap-1 font-mono text-xs">
                                            <Calendar size={10} strokeWidth={1.5} />
                                            {listing.vintage_year}
                                        </span>
                                    </>
                                )}
                                <span className="text-mist">·</span>
                                <span className={`inline-flex items-center gap-1 text-xs font-medium ${verification.color}`}>
                                    <VerifIcon size={12} strokeWidth={1.5} />
                                    {verification.label}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Right: Price display */}
                    <div className="text-right shrink-0">
                        <span className="font-serif italic text-3xl text-canopy">€{listing.price_per_tonne_eur.toFixed(2)}</span>
                        <span className="block font-mono text-[10px] text-slate/40 mt-1 uppercase tracking-widest">per tCO₂e</span>
                    </div>
                </div>

                {/* Stats + progress bar */}
                <div className="bg-linen/60 rounded-xl p-4 mb-4">
                    <div className="flex items-center gap-8 mb-3">
                        <div>
                            <span className="block font-mono text-[10px] text-slate/40 uppercase tracking-widest">Available</span>
                            <span className="font-mono text-sm font-medium text-slate">{available.toLocaleString()}t</span>
                        </div>
                        <div>
                            <span className="block font-mono text-[10px] text-slate/40 uppercase tracking-widest">Reserved</span>
                            <span className="font-mono text-sm font-medium text-amber-600">{listing.quantity_reserved.toLocaleString()}t</span>
                        </div>
                        <div>
                            <span className="block font-mono text-[10px] text-slate/40 uppercase tracking-widest">Sold</span>
                            <span className="font-mono text-sm font-medium text-emerald-600">{listing.quantity_sold.toLocaleString()}t</span>
                        </div>
                        <div className="ml-auto">
                            <span className="font-mono text-xs text-slate/50">{soldPercent}% sold</span>
                        </div>
                    </div>
                    <div className="w-full h-2 rounded-full bg-mist overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-sage to-emerald-500 transition-all duration-700" style={{ width: `${soldPercent}%` }} />
                    </div>
                </div>

                {/* Actions row */}
                <div className="flex items-center justify-between pt-2">
                    {/* Co-benefits tags */}
                    <div className="flex gap-2 flex-wrap">
                        {listing.co_benefits.slice(0, 3).map((benefit) => (
                            <span key={benefit} className="bg-mist/60 text-slate/50 text-[10px] font-mono uppercase tracking-wider px-2.5 py-1 rounded-full">
                                {benefit}
                            </span>
                        ))}
                        {listing.co_benefits.length > 3 && (
                            <span className="text-slate/30 text-[10px] font-mono px-1">+{listing.co_benefits.length - 3}</span>
                        )}
                    </div>

                    {/* Action buttons */}
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                        <button
                            onClick={() => onEdit(listing)}
                            title="Edit"
                            className="p-2.5 rounded-xl hover:bg-mist/50 text-slate/40 hover:text-slate transition-colors cursor-pointer"
                        >
                            <Pencil size={15} strokeWidth={1.5} />
                        </button>
                        {listing.status === 'active' ? (
                            <button
                                onClick={() => onStatusChange(listing.id, 'paused')}
                                title="Pause listing"
                                className="p-2.5 rounded-xl hover:bg-amber-50 text-slate/40 hover:text-amber-600 transition-colors cursor-pointer"
                            >
                                <Pause size={15} strokeWidth={1.5} />
                            </button>
                        ) : listing.status === 'paused' ? (
                            <button
                                onClick={() => onStatusChange(listing.id, 'active')}
                                title="Resume listing"
                                className="p-2.5 rounded-xl hover:bg-emerald-50 text-slate/40 hover:text-emerald-600 transition-colors cursor-pointer"
                            >
                                <Play size={15} strokeWidth={1.5} />
                            </button>
                        ) : null}
                        <button
                            onClick={() => onArchive(listing.id)}
                            title="Archive"
                            className="p-2.5 rounded-xl hover:bg-red-50 text-slate/40 hover:text-red-500 transition-colors cursor-pointer"
                        >
                            <Archive size={15} strokeWidth={1.5} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
