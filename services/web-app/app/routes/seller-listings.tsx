import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listingsGetMine, listingUpdate, listingDelete, listingVerify, type Listing } from '@clients/api/listings';
import { Leaf, Plus } from 'lucide-react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

import { SellerHeroPanel } from '../components/seller/SellerHeroPanel';
import { SellerStatsTiles } from '../components/seller/SellerStatsTiles';
import { SellerListingCard } from '../components/seller/SellerListingCard';
import { EditListingModal } from '../components/seller/EditListingModal';
import { CreateListingModal } from '../components/seller/CreateListingModal';
import { useCreateListing } from '../modules/shared/queries/useListings';
import type { Route } from "./+types/seller-listings";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | My Listings" },
        { name: "description", content: "Manage your carbon credit portfolio." },
    ];
}

gsap.registerPlugin(ScrollTrigger);

export default function SellerListingsPage() {
    const queryClient = useQueryClient();
    const [editingListing, setEditingListing] = useState<Listing | null>(null);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [filter, setFilter] = useState<string>('all');
    const listingsRef = useRef<HTMLDivElement>(null);
    const createMutation = useCreateListing();

    const { data, isLoading } = useQuery({
        queryKey: ['listings', 'mine'],
        queryFn: listingsGetMine,
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, updates }: { id: string; updates: Partial<Listing> }) => listingUpdate(id, updates),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['listings', 'mine'] });
            setEditingListing(null);
        },
    });

    const archiveMutation = useMutation({
        mutationFn: (id: string) => listingDelete(id),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['listings', 'mine'] }),
    });

    const verifyMutation = useMutation({
        mutationFn: (id: string) => listingVerify(id),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['listings', 'mine'] }),
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

    // Animate listing cards on scroll
    useEffect(() => {
        if (!listingsRef.current || filtered.length === 0) return;

        const ctx = gsap.context(() => {
            gsap.fromTo(
                '.listing-card',
                { y: 30, opacity: 0 },
                {
                    y: 0,
                    opacity: 1,
                    stagger: 0.08,
                    duration: 0.6,
                    ease: 'power3.out',
                },
            );
        }, listingsRef);

        return () => ctx.revert();
    }, [filtered.length, filter]);

    return (
        <div className="flex flex-col gap-10 w-full animate-in fade-in duration-700">
            {/* Hero Panel */}
            {!isLoading && <SellerHeroPanel listings={listings} />}

            {/* Stats Tiles */}
            {!isLoading && <SellerStatsTiles listings={listings} />}

            {/* Section header + Filter Tabs */}
            <div className="flex items-end justify-between mt-4">
                <div className="flex items-center gap-4">
                    <div>
                        <h2 className="font-serif italic text-3xl text-slate">Your Listings</h2>
                        <p className="text-slate/50 text-sm mt-1 font-sans">Manage, pause, and track your carbon credit portfolio</p>
                    </div>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="magnetic-btn h-10 px-5 rounded-full bg-slate text-linen font-medium text-sm cursor-pointer border-0 flex items-center gap-2 shrink-0 self-start mt-1"
                    >
                        <div className="magnetic-bg bg-canopy" />
                        <Plus size={16} className="relative z-10" />
                        <span className="relative z-10">Add Listing</span>
                    </button>
                </div>

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
            </div>

            {/* Listings */}
            {isLoading ? (
                <div className="flex items-center justify-center py-20">
                    <div className="w-6 h-6 border-2 border-sage/30 border-t-sage rounded-full animate-spin" />
                </div>
            ) : filtered.length === 0 ? (
                <div className="text-center py-20">
                    <div className="w-16 h-16 rounded-full bg-mist/50 flex items-center justify-center mx-auto mb-4">
                        <Leaf size={28} className="text-slate/30" />
                    </div>
                    <p className="text-slate/40 font-sans text-lg">No listings found</p>
                    <p className="text-slate/30 font-mono text-xs mt-2">Try adjusting the filter above</p>
                </div>
            ) : (
                <div ref={listingsRef} className="space-y-5">
                    {filtered.map((listing) => (
                        <SellerListingCard
                            key={listing.id}
                            listing={listing}
                            onEdit={setEditingListing}
                            onStatusChange={handleStatusChange}
                            onArchive={(id) => archiveMutation.mutate(id)}
                            onVerify={(id) => verifyMutation.mutate(id)}
                            isVerifying={verifyMutation.isPending}
                        />
                    ))}
                </div>
            )}

            {/* Edit Modal */}
            {editingListing && (
                <EditListingModal
                    listing={editingListing}
                    onClose={() => setEditingListing(null)}
                    onSave={handleEdit}
                />
            )}

            {/* Create Modal */}
            {showCreateModal && (
                <CreateListingModal
                    onClose={() => setShowCreateModal(false)}
                    onSave={(data) => {
                        createMutation.mutate(data, {
                            onSuccess: () => setShowCreateModal(false),
                        });
                    }}
                    isSubmitting={createMutation.isPending}
                />
            )}
        </div>
    );
}
