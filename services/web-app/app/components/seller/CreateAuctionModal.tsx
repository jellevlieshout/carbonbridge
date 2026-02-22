import React, { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import { X, Gavel, ChevronDown } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { listingsGetMine, type Listing } from '@clients/api/listings';
import type { CreateAuctionRequest } from '@clients/api/auctions';

const DURATION_OPTIONS = [
    { value: 12, label: '12 hours' },
    { value: 24, label: '24 hours' },
    { value: 48, label: '48 hours' },
    { value: 72, label: '3 days' },
    { value: 168, label: '7 days' },
] as const;

interface CreateAuctionModalProps {
    onClose: () => void;
    onSave: (data: CreateAuctionRequest) => void;
    isSubmitting?: boolean;
}

export function CreateAuctionModal({ onClose, onSave, isSubmitting }: CreateAuctionModalProps) {
    const [step, setStep] = useState(0);
    const panelRef = useRef<HTMLDivElement>(null);

    // Form state
    const [selectedListingId, setSelectedListingId] = useState('');
    const [startingPrice, setStartingPrice] = useState('');
    const [reservePrice, setReservePrice] = useState('');
    const [buyNowPrice, setBuyNowPrice] = useState('');
    const [quantity, setQuantity] = useState('');
    const [duration, setDuration] = useState(24);
    const [minIncrement, setMinIncrement] = useState('0.50');
    const [autoExtend, setAutoExtend] = useState('5');

    // Fetch seller's active listings
    const { data: listingsData } = useQuery({
        queryKey: ['listings', 'mine'],
        queryFn: listingsGetMine,
    });

    const activeListings = (listingsData?.listings || []).filter(
        (l: Listing) => l.status === 'active' && l.verification_status === 'verified',
    );

    const selectedListing = activeListings.find((l: Listing) => l.id === selectedListingId);
    const maxAvailable = selectedListing
        ? selectedListing.quantity_tonnes - selectedListing.quantity_reserved - selectedListing.quantity_sold
        : 0;

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

    const canProceedStep0 = selectedListingId !== '' && parseFloat(quantity) > 0 && parseFloat(quantity) <= maxAvailable;
    const canProceedStep1 = parseFloat(startingPrice) > 0 && parseFloat(minIncrement) > 0;

    const handleSubmit = () => {
        const data: CreateAuctionRequest = {
            listing_id: selectedListingId,
            starting_price_per_tonne_eur: parseFloat(startingPrice),
            reserve_price_per_tonne_eur: reservePrice ? parseFloat(reservePrice) : null,
            buy_now_price_per_tonne_eur: buyNowPrice ? parseFloat(buyNowPrice) : null,
            min_bid_increment_eur: parseFloat(minIncrement) || 0.50,
            quantity_tonnes: parseFloat(quantity),
            duration_hours: duration,
            auto_extend_minutes: parseInt(autoExtend) || 5,
        };
        onSave(data);
    };

    const inputClass = 'w-full h-12 px-4 rounded-xl border border-mist bg-linen text-slate font-mono text-sm focus:outline-none focus:ring-2 focus:ring-sage/30';
    const labelClass = 'block font-mono text-xs text-slate/50 uppercase tracking-widest mb-2';

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-slate/40 backdrop-blur-sm" onClick={onClose} />
            <div
                ref={panelRef}
                className="relative bg-white rounded-[2rem] p-10 w-full max-w-2xl shadow-xl border border-mist max-h-[90vh] overflow-y-auto"
            >
                <button onClick={onClose} className="absolute top-6 right-6 text-slate/40 hover:text-slate transition-colors cursor-pointer">
                    <X size={20} />
                </button>

                <h3 className="font-sans font-bold text-xl text-slate mb-1">New Auction</h3>
                <p className="text-sm text-slate/50 font-mono mb-8">Create an auction for your carbon credits</p>

                {/* Step indicators */}
                <div className="flex items-center gap-2 mb-8">
                    {['Select Listing', 'Auction Parameters', 'Review'].map((label, i) => (
                        <button
                            key={label}
                            onClick={() => {
                                if (i === 0) setStep(0);
                                if (i === 1 && canProceedStep0) setStep(1);
                                if (i === 2 && canProceedStep0 && canProceedStep1) setStep(2);
                            }}
                            className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium transition-colors cursor-pointer border-0 ${
                                step === i
                                    ? 'bg-canopy text-linen'
                                    : step > i
                                        ? 'bg-sage/20 text-canopy'
                                        : 'bg-mist/50 text-slate/40'
                            }`}
                        >
                            <span className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center text-[10px] font-bold">{i + 1}</span>
                            {label}
                        </button>
                    ))}
                </div>

                {/* Step 0: Select Listing */}
                {step === 0 && (
                    <div className="space-y-5">
                        <div>
                            <label className={labelClass}>Select Listing *</label>
                            {activeListings.length === 0 ? (
                                <p className="text-sm text-slate/50 italic">No verified active listings available. Please create and verify a listing first.</p>
                            ) : (
                                <div className="space-y-2">
                                    {activeListings.map((listing: Listing) => {
                                        const avail = listing.quantity_tonnes - listing.quantity_reserved - listing.quantity_sold;
                                        const isSelected = selectedListingId === listing.id;
                                        return (
                                            <button
                                                key={listing.id}
                                                onClick={() => {
                                                    setSelectedListingId(listing.id);
                                                    if (!quantity || parseFloat(quantity) > avail) {
                                                        setQuantity(String(Math.min(avail, parseFloat(quantity) || avail)));
                                                    }
                                                }}
                                                className={`w-full text-left p-4 rounded-xl border transition-all cursor-pointer ${
                                                    isSelected
                                                        ? 'border-canopy bg-canopy/5 ring-2 ring-canopy/20'
                                                        : 'border-mist hover:border-sage/50 bg-white'
                                                }`}
                                            >
                                                <div className="flex justify-between items-start">
                                                    <div>
                                                        <span className="font-sans font-medium text-sm text-slate">{listing.project_name}</span>
                                                        <div className="flex items-center gap-3 mt-1 text-xs text-slate/50 font-mono">
                                                            {listing.project_type && <span>{listing.project_type.replace('_', ' ')}</span>}
                                                            {listing.vintage_year && <span>Vintage {listing.vintage_year}</span>}
                                                        </div>
                                                    </div>
                                                    <div className="text-right">
                                                        <span className="font-mono text-sm font-semibold text-slate">{avail}t</span>
                                                        <span className="block text-[10px] text-slate/40 font-mono">available</span>
                                                    </div>
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                        {selectedListingId && (
                            <div>
                                <label className={labelClass}>Quantity to Auction (tonnes) *</label>
                                <input
                                    type="number"
                                    min="1"
                                    max={maxAvailable}
                                    step="1"
                                    value={quantity}
                                    onChange={(e) => setQuantity(e.target.value)}
                                    placeholder={`Max ${maxAvailable}`}
                                    className={inputClass}
                                />
                                <span className="text-[10px] text-slate/40 font-mono mt-1 block">{maxAvailable} tonnes available</span>
                            </div>
                        )}
                    </div>
                )}

                {/* Step 1: Auction Parameters */}
                {step === 1 && (
                    <div className="space-y-5">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className={labelClass}>Starting Price (/t) *</label>
                                <input
                                    type="number"
                                    min="0.01"
                                    step="0.01"
                                    value={startingPrice}
                                    onChange={(e) => setStartingPrice(e.target.value)}
                                    placeholder="e.g. 8.00"
                                    className={inputClass}
                                />
                            </div>
                            <div>
                                <label className={labelClass}>Reserve Price (/t)</label>
                                <input
                                    type="number"
                                    min="0.01"
                                    step="0.01"
                                    value={reservePrice}
                                    onChange={(e) => setReservePrice(e.target.value)}
                                    placeholder="Optional"
                                    className={inputClass}
                                />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className={labelClass}>Buy Now Price (/t)</label>
                                <input
                                    type="number"
                                    min="0.01"
                                    step="0.01"
                                    value={buyNowPrice}
                                    onChange={(e) => setBuyNowPrice(e.target.value)}
                                    placeholder="Optional"
                                    className={inputClass}
                                />
                            </div>
                            <div>
                                <label className={labelClass}>Min Bid Increment</label>
                                <input
                                    type="number"
                                    min="0.01"
                                    step="0.01"
                                    value={minIncrement}
                                    onChange={(e) => setMinIncrement(e.target.value)}
                                    placeholder="0.50"
                                    className={inputClass}
                                />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className={labelClass}>Duration</label>
                                <div className="relative">
                                    <select
                                        value={duration}
                                        onChange={(e) => setDuration(Number(e.target.value))}
                                        className={`${inputClass} appearance-none pr-10`}
                                    >
                                        {DURATION_OPTIONS.map(d => (
                                            <option key={d.value} value={d.value}>{d.label}</option>
                                        ))}
                                    </select>
                                    <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate/30 pointer-events-none" />
                                </div>
                            </div>
                            <div>
                                <label className={labelClass}>Anti-snipe Window (min)</label>
                                <input
                                    type="number"
                                    min="1"
                                    max="30"
                                    value={autoExtend}
                                    onChange={(e) => setAutoExtend(e.target.value)}
                                    placeholder="5"
                                    className={inputClass}
                                />
                            </div>
                        </div>

                        {startingPrice && quantity && (
                            <div className="bg-linen/60 rounded-xl p-5 border border-mist">
                                <span className="block font-mono text-[10px] text-slate/40 uppercase tracking-widest mb-1">Starting Total Value</span>
                                <span className="font-serif italic text-3xl text-canopy">
                                    {(parseFloat(startingPrice || '0') * parseFloat(quantity || '0')).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </span>
                                {buyNowPrice && (
                                    <div className="mt-2">
                                        <span className="block font-mono text-[10px] text-slate/40 uppercase tracking-widest mb-1">Buy Now Total</span>
                                        <span className="font-serif italic text-xl text-violet-600">
                                            {(parseFloat(buyNowPrice || '0') * parseFloat(quantity || '0')).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                        </span>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* Step 2: Review */}
                {step === 2 && selectedListing && (
                    <div className="space-y-5">
                        <div className="bg-linen/40 rounded-xl p-6 border border-mist space-y-4">
                            <div className="flex justify-between items-start">
                                <div>
                                    <span className="block font-mono text-[10px] text-slate/40 uppercase tracking-widest mb-1">Project</span>
                                    <span className="font-sans font-medium text-slate">{selectedListing.project_name}</span>
                                </div>
                                <div className="text-right">
                                    <span className="block font-mono text-[10px] text-slate/40 uppercase tracking-widest mb-1">Quantity</span>
                                    <span className="font-mono font-semibold text-slate">{quantity}t</span>
                                </div>
                            </div>

                            <div className="h-px bg-mist" />

                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="font-mono text-[10px] text-slate/40 uppercase tracking-widest">Starting Price</span>
                                    <span className="block font-semibold text-slate">{parseFloat(startingPrice).toFixed(2)}/t</span>
                                </div>
                                {reservePrice && (
                                    <div>
                                        <span className="font-mono text-[10px] text-slate/40 uppercase tracking-widest">Reserve</span>
                                        <span className="block font-semibold text-slate">{parseFloat(reservePrice).toFixed(2)}/t</span>
                                    </div>
                                )}
                                {buyNowPrice && (
                                    <div>
                                        <span className="font-mono text-[10px] text-slate/40 uppercase tracking-widest">Buy Now</span>
                                        <span className="block font-semibold text-violet-600">{parseFloat(buyNowPrice).toFixed(2)}/t</span>
                                    </div>
                                )}
                                <div>
                                    <span className="font-mono text-[10px] text-slate/40 uppercase tracking-widest">Duration</span>
                                    <span className="block font-semibold text-slate">
                                        {DURATION_OPTIONS.find(d => d.value === duration)?.label}
                                    </span>
                                </div>
                                <div>
                                    <span className="font-mono text-[10px] text-slate/40 uppercase tracking-widest">Min Increment</span>
                                    <span className="block font-semibold text-slate">{parseFloat(minIncrement).toFixed(2)}</span>
                                </div>
                                <div>
                                    <span className="font-mono text-[10px] text-slate/40 uppercase tracking-widest">Anti-snipe</span>
                                    <span className="block font-semibold text-slate">{autoExtend} min</span>
                                </div>
                            </div>

                            <div className="h-px bg-mist" />

                            <div>
                                <span className="block font-mono text-[10px] text-slate/40 uppercase tracking-widest mb-1">Starting Total Value</span>
                                <span className="font-serif italic text-3xl text-canopy">
                                    {(parseFloat(startingPrice) * parseFloat(quantity)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </span>
                            </div>
                        </div>

                        <p className="text-xs text-slate/50 font-mono leading-relaxed">
                            The auctioned quantity will be reserved from your listing inventory.
                            If the auction ends without bids or fails to meet the reserve, the quantity will be returned.
                        </p>
                    </div>
                )}

                {/* Navigation */}
                <div className="flex gap-3 mt-8">
                    {step > 0 ? (
                        <button
                            onClick={() => setStep(step - 1)}
                            className="flex-1 h-12 rounded-full border border-mist text-slate/60 font-medium text-sm cursor-pointer hover:bg-mist/50 transition-colors"
                        >
                            Back
                        </button>
                    ) : (
                        <button
                            onClick={onClose}
                            className="flex-1 h-12 rounded-full border border-mist text-slate/60 font-medium text-sm cursor-pointer hover:bg-mist/50 transition-colors"
                        >
                            Cancel
                        </button>
                    )}
                    {step < 2 ? (
                        <button
                            onClick={() => setStep(step + 1)}
                            disabled={step === 0 ? !canProceedStep0 : !canProceedStep1}
                            className="magnetic-btn flex-1 h-12 rounded-full bg-slate text-linen font-medium text-sm cursor-pointer border-0 flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            <div className="magnetic-bg bg-canopy" />
                            <span className="relative z-10">Continue</span>
                        </button>
                    ) : (
                        <button
                            onClick={handleSubmit}
                            disabled={isSubmitting}
                            className="magnetic-btn flex-1 h-12 rounded-full bg-slate text-linen font-medium text-sm cursor-pointer border-0 flex items-center justify-center gap-2 disabled:opacity-40"
                        >
                            <div className="magnetic-bg bg-ember" />
                            <Gavel size={16} className="relative z-10" />
                            <span className="relative z-10">{isSubmitting ? 'Creating...' : 'Create Auction'}</span>
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
