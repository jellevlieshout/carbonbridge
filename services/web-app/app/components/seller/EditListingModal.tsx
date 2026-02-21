import React, { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import { X, Check } from 'lucide-react';
import type { Listing } from '@clients/api/listings';

interface EditListingModalProps {
    listing: Listing;
    onClose: () => void;
    onSave: (id: string, data: Partial<Listing>) => void;
}

export function EditListingModal({ listing, onClose, onSave }: EditListingModalProps) {
    const [price, setPrice] = useState(String(listing.price_per_tonne_eur));
    const [quantity, setQuantity] = useState(String(listing.quantity_tonnes));
    const [description, setDescription] = useState(listing.description || '');
    const panelRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const ctx = gsap.context(() => {
            gsap.fromTo(
                panelRef.current,
                { scale: 0.95, opacity: 0, y: 20 },
                { scale: 1, opacity: 1, y: 0, duration: 0.4, ease: 'back.out(1.7)' },
            );
        });
        return () => ctx.revert();
    }, []);

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
            <div
                ref={panelRef}
                className="relative bg-white rounded-[2rem] p-10 w-full max-w-lg shadow-xl border border-mist"
            >
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
