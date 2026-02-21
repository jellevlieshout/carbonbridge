import React, { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import { X, Plus, ChevronDown } from 'lucide-react';
import type { ListingCreateRequest } from '@clients/api/listings';

const PROJECT_TYPES = [
    { value: 'afforestation', label: 'Afforestation' },
    { value: 'renewable', label: 'Renewable Energy' },
    { value: 'cookstoves', label: 'Cookstoves' },
    { value: 'methane_capture', label: 'Methane Capture' },
    { value: 'fuel_switching', label: 'Fuel Switching' },
    { value: 'energy_efficiency', label: 'Energy Efficiency' },
    { value: 'agriculture', label: 'Agriculture' },
    { value: 'other', label: 'Other' },
] as const;

const CO_BENEFIT_OPTIONS = [
    'Biodiversity', 'Community Development', 'Clean Water',
    'Job Creation', 'Health Improvement', 'Education',
    'Gender Equality', 'Soil Conservation', 'Air Quality',
];

interface CreateListingModalProps {
    onClose: () => void;
    onSave: (data: ListingCreateRequest) => void;
    isSubmitting?: boolean;
}

export function CreateListingModal({ onClose, onSave, isSubmitting }: CreateListingModalProps) {
    const [step, setStep] = useState(0);
    const panelRef = useRef<HTMLDivElement>(null);

    // Form state
    const [projectName, setProjectName] = useState('');
    const [projectType, setProjectType] = useState('other');
    const [projectCountry, setProjectCountry] = useState('');
    const [registryName, setRegistryName] = useState('');
    const [registryProjectId, setRegistryProjectId] = useState('');
    const [serialNumberRange, setSerialNumberRange] = useState('');
    const [vintageYear, setVintageYear] = useState('');
    const [quantityTonnes, setQuantityTonnes] = useState('');
    const [pricePerTonne, setPricePerTonne] = useState('');
    const [methodology, setMethodology] = useState('');
    const [description, setDescription] = useState('');
    const [coBenefits, setCoBenefits] = useState<string[]>([]);

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

    const toggleCoBenefit = (benefit: string) => {
        setCoBenefits(prev =>
            prev.includes(benefit) ? prev.filter(b => b !== benefit) : [...prev, benefit]
        );
    };

    const canProceedStep0 = projectName.trim() && registryName.trim();
    const canProceedStep1 = parseFloat(quantityTonnes) > 0 && parseFloat(pricePerTonne) > 0;

    const handleSubmit = () => {
        const data: ListingCreateRequest = {
            project_name: projectName.trim(),
            project_type: projectType,
            project_country: projectCountry.trim() || null,
            registry_name: registryName.trim(),
            registry_project_id: registryProjectId.trim() || null,
            serial_number_range: serialNumberRange.trim() || null,
            vintage_year: vintageYear ? parseInt(vintageYear) : null,
            quantity_tonnes: parseFloat(quantityTonnes),
            price_per_tonne_eur: parseFloat(pricePerTonne),
            methodology: methodology.trim() || null,
            description: description.trim() || null,
            co_benefits: coBenefits,
        };
        onSave(data);
    };

    const inputClass = "w-full h-12 px-4 rounded-xl border border-mist bg-linen text-slate font-mono text-sm focus:outline-none focus:ring-2 focus:ring-sage/30";
    const labelClass = "block font-mono text-xs text-slate/50 uppercase tracking-widest mb-2";

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

                <h3 className="font-sans font-bold text-xl text-slate mb-1">New Listing</h3>
                <p className="text-sm text-slate/50 font-mono mb-8">List carbon credits for sale on the marketplace</p>

                {/* Step indicators */}
                <div className="flex items-center gap-2 mb-8">
                    {['Project Details', 'Pricing & Quantity', 'Additional Info'].map((label, i) => (
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

                {/* Step 0: Project Details */}
                {step === 0 && (
                    <div className="space-y-5">
                        <div>
                            <label className={labelClass}>Project Name *</label>
                            <input
                                type="text"
                                value={projectName}
                                onChange={(e) => setProjectName(e.target.value)}
                                placeholder="e.g. Kenyan Mangrove Restoration"
                                className={inputClass}
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className={labelClass}>Project Type</label>
                                <div className="relative">
                                    <select
                                        value={projectType}
                                        onChange={(e) => setProjectType(e.target.value)}
                                        className={`${inputClass} appearance-none pr-10`}
                                    >
                                        {PROJECT_TYPES.map(t => (
                                            <option key={t.value} value={t.value}>{t.label}</option>
                                        ))}
                                    </select>
                                    <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate/30 pointer-events-none" />
                                </div>
                            </div>
                            <div>
                                <label className={labelClass}>Country</label>
                                <input
                                    type="text"
                                    value={projectCountry}
                                    onChange={(e) => setProjectCountry(e.target.value)}
                                    placeholder="e.g. Kenya"
                                    className={inputClass}
                                />
                            </div>
                        </div>
                        <div>
                            <label className={labelClass}>Registry Name *</label>
                            <input
                                type="text"
                                value={registryName}
                                onChange={(e) => setRegistryName(e.target.value)}
                                placeholder="e.g. Verra, Gold Standard"
                                className={inputClass}
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className={labelClass}>Registry Project ID</label>
                                <input
                                    type="text"
                                    value={registryProjectId}
                                    onChange={(e) => setRegistryProjectId(e.target.value)}
                                    placeholder="e.g. VCS-1234"
                                    className={inputClass}
                                />
                            </div>
                            <div>
                                <label className={labelClass}>Serial Number Range</label>
                                <input
                                    type="text"
                                    value={serialNumberRange}
                                    onChange={(e) => setSerialNumberRange(e.target.value)}
                                    placeholder="e.g. 1001-2000"
                                    className={inputClass}
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Step 1: Pricing & Quantity */}
                {step === 1 && (
                    <div className="space-y-5">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className={labelClass}>Quantity (tonnes CO₂e) *</label>
                                <input
                                    type="number"
                                    min="1"
                                    step="1"
                                    value={quantityTonnes}
                                    onChange={(e) => setQuantityTonnes(e.target.value)}
                                    placeholder="e.g. 1000"
                                    className={inputClass}
                                />
                            </div>
                            <div>
                                <label className={labelClass}>Price per tonne (EUR) *</label>
                                <input
                                    type="number"
                                    min="0.01"
                                    step="0.01"
                                    value={pricePerTonne}
                                    onChange={(e) => setPricePerTonne(e.target.value)}
                                    placeholder="e.g. 12.50"
                                    className={inputClass}
                                />
                            </div>
                        </div>
                        <div>
                            <label className={labelClass}>Vintage Year</label>
                            <input
                                type="number"
                                min="2000"
                                max="2030"
                                value={vintageYear}
                                onChange={(e) => setVintageYear(e.target.value)}
                                placeholder="e.g. 2024"
                                className={inputClass}
                            />
                        </div>
                        {quantityTonnes && pricePerTonne && (
                            <div className="bg-linen/60 rounded-xl p-5 border border-mist">
                                <span className="block font-mono text-[10px] text-slate/40 uppercase tracking-widest mb-1">Total Listing Value</span>
                                <span className="font-serif italic text-3xl text-canopy">
                                    €{(parseFloat(quantityTonnes || '0') * parseFloat(pricePerTonne || '0')).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </span>
                            </div>
                        )}
                    </div>
                )}

                {/* Step 2: Additional Info */}
                {step === 2 && (
                    <div className="space-y-5">
                        <div>
                            <label className={labelClass}>Description</label>
                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                rows={3}
                                placeholder="Describe your carbon credit project..."
                                className="w-full px-4 py-3 rounded-xl border border-mist bg-linen text-slate text-sm focus:outline-none focus:ring-2 focus:ring-sage/30 resize-none"
                            />
                        </div>
                        <div>
                            <label className={labelClass}>Methodology</label>
                            <input
                                type="text"
                                value={methodology}
                                onChange={(e) => setMethodology(e.target.value)}
                                placeholder="e.g. VM0007, AMS-I.D"
                                className={inputClass}
                            />
                        </div>
                        <div>
                            <label className={labelClass}>Co-benefits</label>
                            <div className="flex flex-wrap gap-2">
                                {CO_BENEFIT_OPTIONS.map(benefit => (
                                    <button
                                        key={benefit}
                                        type="button"
                                        onClick={() => toggleCoBenefit(benefit)}
                                        className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors cursor-pointer border ${
                                            coBenefits.includes(benefit)
                                                ? 'bg-canopy text-linen border-canopy'
                                                : 'bg-white text-slate/50 border-mist hover:border-sage/50 hover:text-slate'
                                        }`}
                                    >
                                        {benefit}
                                    </button>
                                ))}
                            </div>
                        </div>
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
                            <Plus size={16} className="relative z-10" />
                            <span className="relative z-10">{isSubmitting ? 'Creating...' : 'Create Listing'}</span>
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
