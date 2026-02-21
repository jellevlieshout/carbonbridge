import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listingsGet, listingUpdate, listingDelete, type Listing } from '@clients/api/listings';
import { Leaf, Pause, Play, Archive, Pencil, X, Check, ShieldCheck, AlertTriangle } from 'lucide-react';

const statusConfig: Record<string, { label: string; bg: string; text: string }> = {
    active: { label: 'Active', bg: 'bg-emerald-500/10', text: 'text-emerald-700' },
    paused: { label: 'Paused', bg: 'bg-amber-500/10', text: 'text-amber-700' },
    draft: { label: 'Draft', bg: 'bg-slate/10', text: 'text-slate/60' },
    sold_out: { label: 'Sold Out', bg: 'bg-red-500/10', text: 'text-red-600' },
};

const verificationConfig: Record<string, { label: string; icon: typeof ShieldCheck; color: string }> = {
    verified: { label: 'Verified', icon: ShieldCheck, color: 'text-emerald-600' },
    pending: { label: 'Pending', icon: AlertTriangle, color: 'text-amber-500' },
    failed: { label: 'Failed', icon: AlertTriangle, color: 'text-red-500' },
};

function StatusBadge({ status }: { status: string }) {
    const config = statusConfig[status] || statusConfig.draft;
    return (
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
            {config.label}
        </span>
    );
}

function VerificationBadge({ status }: { status: string }) {
    const config = verificationConfig[status] || verificationConfig.pending;
    const Icon = config.icon;
    return (
        <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${config.color}`}>
            <Icon size={14} strokeWidth={1.5} />
            {config.label}
        </span>
    );
}

function EditModal({ listing, onClose, onSave }: {
    listing: Listing;
    onClose: () => void;
    onSave: (id: string, data: Partial<Listing>) => void;
}) {
    const [price, setPrice] = useState(String(listing.price_per_tonne_eur));
    const [quantity, setQuantity] = useState(String(listing.quantity_tonnes));
    const [description, setDescription] = useState(listing.description || '');

    const handleSave = () => {
        onSave(listing.id, {
            price_per_tonne_eur: parseFloat(price),
            quantity_tonnes: parseFloat(quantity),
            description,
        });
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-slate/40 backdrop-blur-sm" onClick={onClose} />
            <div className="relative bg-white rounded-[2rem] p-10 w-full max-w-lg shadow-xl border border-mist">
                <button onClick={onClose} className="absolute top-6 right-6 text-slate/40 hover:text-slate transition-colors cursor-pointer">
                    <X size={20} />
                </button>

                <h3 className="font-sans font-bold text-xl text-slate mb-2">{listing.project_name}</h3>
                <p className="text-sm text-slate/50 font-mono mb-8">{listing.registry_name} / {listing.registry_project_id}</p>

                <div className="space-y-6">
                    <div>
                        <label className="block font-mono text-xs text-slate/50 uppercase tracking-widest mb-2">Price per tonne (EUR)</label>
                        <input
                            type="number"
                            step="0.01"
                            value={price}
                            onChange={(e) => setPrice(e.target.value)}
                            className="w-full h-12 px-4 rounded-xl border border-mist bg-linen text-slate font-mono focus:outline-none focus:ring-2 focus:ring-sage/30"
                        />
                    </div>
                    <div>
                        <label className="block font-mono text-xs text-slate/50 uppercase tracking-widest mb-2">Quantity (tonnes)</label>
                        <input
                            type="number"
                            step="1"
                            value={quantity}
                            onChange={(e) => setQuantity(e.target.value)}
                            className="w-full h-12 px-4 rounded-xl border border-mist bg-linen text-slate font-mono focus:outline-none focus:ring-2 focus:ring-sage/30"
                        />
                    </div>
                    <div>
                        <label className="block font-mono text-xs text-slate/50 uppercase tracking-widest mb-2">Description</label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={3}
                            className="w-full px-4 py-3 rounded-xl border border-mist bg-linen text-slate text-sm focus:outline-none focus:ring-2 focus:ring-sage/30 resize-none"
                        />
                    </div>
                </div>

                <div className="flex gap-3 mt-8">
                    <button onClick={onClose} className="flex-1 h-12 rounded-full border border-mist text-slate/60 font-medium text-sm cursor-pointer hover:bg-mist/50 transition-colors">
                        Cancel
                    </button>
                    <button onClick={handleSave} className="magnetic-btn flex-1 h-12 rounded-full bg-slate text-linen font-medium text-sm cursor-pointer border-0 flex items-center justify-center gap-2">
                        <div className="magnetic-bg bg-ember" />
                        <Check size={16} className="relative z-10" />
                        <span className="relative z-10">Save Changes</span>
                    </button>
                </div>
            </div>
        </div>
    );
}

function ListingRow({ listing, onEdit, onStatusChange, onArchive }: {
    listing: Listing;
    onEdit: (listing: Listing) => void;
    onStatusChange: (id: string, status: string) => void;
    onArchive: (id: string) => void;
}) {
    const available = listing.quantity_tonnes - listing.quantity_reserved - listing.quantity_sold;
    const soldPercent = listing.quantity_tonnes > 0
        ? Math.round((listing.quantity_sold / listing.quantity_tonnes) * 100)
        : 0;

    return (
        <div className="group bg-white rounded-2xl border border-mist p-6 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between gap-4">
                {/* Left: Project Info */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-sans font-bold text-lg text-slate truncate">{listing.project_name}</h3>
                        <StatusBadge status={listing.status} />
                        <VerificationBadge status={listing.verification_status} />
                    </div>

                    <div className="flex items-center gap-4 text-sm text-slate/50 font-mono">
                        <span>{listing.registry_name}</span>
                        {listing.registry_project_id && (
                            <>
                                <span className="text-mist">|</span>
                                <span>{listing.registry_project_id}</span>
                            </>
                        )}
                        {listing.project_country && (
                            <>
                                <span className="text-mist">|</span>
                                <span>{listing.project_country}</span>
                            </>
                        )}
                        {listing.vintage_year && (
                            <>
                                <span className="text-mist">|</span>
                                <span>{listing.vintage_year}</span>
                            </>
                        )}
                    </div>
                </div>

                {/* Right: Price */}
                <div className="text-right shrink-0">
                    <span className="font-serif italic text-3xl text-canopy">€{listing.price_per_tonne_eur.toFixed(2)}</span>
                    <span className="block font-mono text-xs text-slate/40 mt-1">/ tCO₂e</span>
                </div>
            </div>

            {/* Stats Row */}
            <div className="flex items-center gap-6 mt-5 pt-5 border-t border-mist/60">
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
                <div className="flex-1">
                    <div className="w-full max-w-[200px] h-2 rounded-full bg-mist overflow-hidden">
                        <div className="h-full rounded-full bg-sage transition-all" style={{ width: `${soldPercent}%` }} />
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                        onClick={() => onEdit(listing)}
                        title="Edit"
                        className="p-2 rounded-lg hover:bg-mist/50 text-slate/40 hover:text-slate transition-colors cursor-pointer"
                    >
                        <Pencil size={16} strokeWidth={1.5} />
                    </button>
                    {listing.status === 'active' ? (
                        <button
                            onClick={() => onStatusChange(listing.id, 'paused')}
                            title="Pause"
                            className="p-2 rounded-lg hover:bg-amber-50 text-slate/40 hover:text-amber-600 transition-colors cursor-pointer"
                        >
                            <Pause size={16} strokeWidth={1.5} />
                        </button>
                    ) : listing.status === 'paused' ? (
                        <button
                            onClick={() => onStatusChange(listing.id, 'active')}
                            title="Unpause"
                            className="p-2 rounded-lg hover:bg-emerald-50 text-slate/40 hover:text-emerald-600 transition-colors cursor-pointer"
                        >
                            <Play size={16} strokeWidth={1.5} />
                        </button>
                    ) : null}
                    <button
                        onClick={() => onArchive(listing.id)}
                        title="Archive"
                        className="p-2 rounded-lg hover:bg-red-50 text-slate/40 hover:text-red-500 transition-colors cursor-pointer"
                    >
                        <Archive size={16} strokeWidth={1.5} />
                    </button>
                </div>
            </div>
        </div>
    );
}

export default function SellerListingsPage() {
    const queryClient = useQueryClient();
    const [editingListing, setEditingListing] = useState<Listing | null>(null);
    const [filter, setFilter] = useState<string>('all');

    const { data, isLoading } = useQuery({
        queryKey: ['listings'],
        queryFn: listingsGet,
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, updates }: { id: string; updates: Partial<Listing> }) => listingUpdate(id, updates),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['listings'] });
            setEditingListing(null);
        },
    });

    const archiveMutation = useMutation({
        mutationFn: (id: string) => listingDelete(id),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['listings'] }),
    });

    const handleStatusChange = (id: string, status: string) => {
        updateMutation.mutate({ id, updates: { status: status as any } });
    };

    const handleEdit = (id: string, updates: Partial<Listing>) => {
        updateMutation.mutate({ id, updates });
    };

    const listings = data?.listings || [];
    const filtered = filter === 'all' ? listings : listings.filter(l => l.status === filter);

    const counts = {
        all: listings.length,
        active: listings.filter(l => l.status === 'active').length,
        paused: listings.filter(l => l.status === 'paused').length,
        draft: listings.filter(l => l.status === 'draft').length,
    };

    return (
        <div className="flex flex-col gap-10 w-full animate-in fade-in duration-700">
            {/* Header */}
            <div className="flex items-end justify-between">
                <div>
                    <h1 className="font-serif italic text-4xl text-slate">My Listings</h1>
                    <p className="text-slate/50 text-sm mt-2 font-sans">Manage your carbon credit listings</p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 bg-white rounded-full border border-mist p-1">
                        <Leaf size={14} className="text-sage ml-3" />
                        <span className="font-mono text-xs text-slate/60 mr-3">{counts.active} active</span>
                    </div>
                </div>
            </div>

            {/* Filter Tabs */}
            <div className="flex gap-2">
                {(['all', 'active', 'paused', 'draft'] as const).map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setFilter(tab)}
                        className={`px-5 py-2 rounded-full text-sm font-medium transition-colors cursor-pointer border-0 ${filter === tab
                            ? 'bg-canopy text-linen'
                            : 'bg-white text-slate/60 hover:text-slate hover:bg-mist/50'
                            }`}
                    >
                        {tab.charAt(0).toUpperCase() + tab.slice(1)}
                        <span className="ml-2 font-mono text-xs opacity-60">{counts[tab as keyof typeof counts] ?? 0}</span>
                    </button>
                ))}
            </div>

            {/* Listings */}
            {isLoading ? (
                <div className="flex items-center justify-center py-20">
                    <div className="w-6 h-6 border-2 border-sage/30 border-t-sage rounded-full animate-spin" />
                </div>
            ) : filtered.length === 0 ? (
                <div className="text-center py-20">
                    <Leaf size={40} className="text-mist mx-auto mb-4" />
                    <p className="text-slate/40 font-sans">No listings found</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {filtered.map((listing) => (
                        <ListingRow
                            key={listing.id}
                            listing={listing}
                            onEdit={setEditingListing}
                            onStatusChange={handleStatusChange}
                            onArchive={(id) => archiveMutation.mutate(id)}
                        />
                    ))}
                </div>
            )}

            {/* Edit Modal */}
            {editingListing && (
                <EditModal
                    listing={editingListing}
                    onClose={() => setEditingListing(null)}
                    onSave={handleEdit}
                />
            )}
        </div>
    );
}
