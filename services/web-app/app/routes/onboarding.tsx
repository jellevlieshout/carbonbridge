import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { userOnboardingSubmit, type OnboardingData } from '@clients/api/user';
import { Logo } from '~/modules/shared/components/Logo';
import {
    ShoppingCart,
    Leaf,
    ArrowRight,
    ArrowLeft,
    Building2,
    Globe,
    Users,
    Factory,
    TreePine,
    Sun,
    Flame,
    Wind,
    Zap,
    Wheat,
    Loader2,
} from 'lucide-react';
import type { Route } from "./+types/onboarding";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Onboarding" },
        { name: "description", content: "Join CarbonBridge and start trading carbon credits." },
    ];
}

const SECTORS = [
    'Manufacturing',
    'Technology',
    'Finance',
    'Energy',
    'Transportation',
    'Agriculture',
    'Real Estate',
    'Retail',
    'Healthcare',
    'Other',
];

const COUNTRIES = [
    'Netherlands',
    'United Kingdom',
    'Germany',
    'France',
    'Belgium',
    'United States',
    'Brazil',
    'India',
    'Kenya',
    'Australia',
    'Other',
];

const MOTIVATIONS = [
    { value: 'compliance' as const, label: 'Regulatory Compliance', desc: 'Meet mandatory carbon reduction targets' },
    { value: 'esg_reporting' as const, label: 'ESG Reporting', desc: 'Strengthen sustainability disclosures' },
    { value: 'brand' as const, label: 'Brand & Marketing', desc: 'Demonstrate climate commitment to customers' },
    { value: 'personal' as const, label: 'Personal Commitment', desc: 'Offset your own carbon footprint' },
];

const PROJECT_TYPES = [
    { value: 'afforestation', label: 'Afforestation', icon: TreePine },
    { value: 'renewable', label: 'Renewable Energy', icon: Sun },
    { value: 'cookstoves', label: 'Clean Cookstoves', icon: Flame },
    { value: 'methane_capture', label: 'Methane Capture', icon: Wind },
    { value: 'energy_efficiency', label: 'Energy Efficiency', icon: Zap },
    { value: 'agriculture', label: 'Agriculture', icon: Wheat },
];

export default function OnboardingPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [step, setStep] = useState(0);
    const [role, setRole] = useState<'buyer' | 'seller' | null>(null);

    // Shared fields
    const [companyName, setCompanyName] = useState('');
    const [sector, setSector] = useState('');
    const [country, setCountry] = useState('');
    const [companySize, setCompanySize] = useState('');

    // Buyer-specific fields
    const [annualCo2, setAnnualCo2] = useState('');
    const [motivation, setMotivation] = useState<'compliance' | 'esg_reporting' | 'brand' | 'personal' | ''>('');
    const [preferredTypes, setPreferredTypes] = useState<string[]>([]);
    const [budgetMax, setBudgetMax] = useState('');

    const mutation = useMutation({
        mutationFn: userOnboardingSubmit,
        onSuccess: async (data) => {
            queryClient.setQueryData(['userResources'], data);
            await queryClient.invalidateQueries({ queryKey: ['userResources'] });
            if (role === 'buyer') {
                navigate('/buyer/dashboard', { replace: true });
            } else {
                navigate('/seller/listings', { replace: true });
            }
        },
    });

    function toggleProjectType(type: string) {
        setPreferredTypes(prev =>
            prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
        );
    }

    function handleSubmit() {
        if (!role || !companyName) return;

        const data: OnboardingData = {
            role,
            company_name: companyName,
            sector: sector || undefined,
            country: country || undefined,
            company_size_employees: companySize ? parseInt(companySize) : undefined,
        };

        if (role === 'buyer') {
            data.buyer_profile = {
                annual_co2_tonnes_estimate: annualCo2 ? parseFloat(annualCo2) : undefined,
                primary_offset_motivation: motivation || undefined,
                preferred_project_types: preferredTypes.length > 0 ? preferredTypes : undefined,
                budget_per_tonne_max_eur: budgetMax ? parseFloat(budgetMax) : undefined,
            };
        }

        mutation.mutate(data);
    }

    const canProceedStep0 = role !== null;
    const canProceedStep1 = companyName.trim().length > 0;
    const isLastStep = role === 'seller' ? step === 1 : step === 2;

    return (
        <div className="min-h-screen bg-linen flex flex-col items-center justify-center p-4">
            {/* Background decoration */}
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[radial-gradient(circle,rgba(61,107,82,0.06)_0%,transparent_70%)]" />
                <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-[radial-gradient(circle,rgba(198,93,53,0.04)_0%,transparent_70%)]" />
            </div>

            <div className="relative z-10 w-full max-w-xl">
                {/* Logo */}
                <div className="flex justify-center mb-10">
                    <Logo size="md" />
                </div>

                {/* Progress indicator */}
                <div className="flex items-center justify-center gap-2 mb-8">
                    {[0, 1, ...(role === 'buyer' ? [2] : [])].map((s) => (
                        <div
                            key={s}
                            className={`h-1.5 rounded-full transition-all duration-500 ${s === step ? 'w-8 bg-canopy' : s < step ? 'w-8 bg-canopy/40' : 'w-8 bg-slate/15'
                                }`}
                        />
                    ))}
                </div>

                {/* Card */}
                <div className="bg-white rounded-2xl border border-mist shadow-sm overflow-hidden">
                    {/* Step 0: Role Selection */}
                    {step === 0 && (
                        <div className="p-10">
                            <h1 className="font-serif italic text-3xl text-slate text-center">
                                Welcome to CarbonBridge
                            </h1>
                            <p className="text-slate/50 text-center mt-3 font-sans text-sm">
                                How would you like to use the platform?
                            </p>

                            <div className="grid grid-cols-2 gap-4 mt-8">
                                <button
                                    onClick={() => setRole('buyer')}
                                    className={`group relative flex flex-col items-center gap-4 p-8 rounded-xl border-2 transition-all cursor-pointer bg-transparent ${role === 'buyer'
                                        ? 'border-canopy bg-canopy/5'
                                        : 'border-mist hover:border-canopy/30'
                                        }`}
                                >
                                    <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-colors ${role === 'buyer' ? 'bg-canopy text-linen' : 'bg-mist/50 text-slate/50 group-hover:bg-canopy/10 group-hover:text-canopy'
                                        }`}>
                                        <ShoppingCart size={28} strokeWidth={1.5} />
                                    </div>
                                    <div className="text-center">
                                        <h3 className="font-sans font-semibold text-slate text-lg">Buyer</h3>
                                        <p className="text-slate/50 text-xs mt-1 leading-relaxed">
                                            Purchase carbon credits to offset your emissions
                                        </p>
                                    </div>
                                </button>

                                <button
                                    onClick={() => setRole('seller')}
                                    className={`group relative flex flex-col items-center gap-4 p-8 rounded-xl border-2 transition-all cursor-pointer bg-transparent ${role === 'seller'
                                        ? 'border-canopy bg-canopy/5'
                                        : 'border-mist hover:border-canopy/30'
                                        }`}
                                >
                                    <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-colors ${role === 'seller' ? 'bg-canopy text-linen' : 'bg-mist/50 text-slate/50 group-hover:bg-canopy/10 group-hover:text-canopy'
                                        }`}>
                                        <Leaf size={28} strokeWidth={1.5} />
                                    </div>
                                    <div className="text-center">
                                        <h3 className="font-sans font-semibold text-slate text-lg">Seller</h3>
                                        <p className="text-slate/50 text-xs mt-1 leading-relaxed">
                                            List and sell verified carbon credits
                                        </p>
                                    </div>
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Step 1: Company Details */}
                    {step === 1 && (
                        <div className="p-10">
                            <h1 className="font-serif italic text-3xl text-slate text-center">
                                Your Organisation
                            </h1>
                            <p className="text-slate/50 text-center mt-3 font-sans text-sm">
                                Tell us about your company
                            </p>

                            <div className="space-y-5 mt-8">
                                <div>
                                    <label className="flex items-center gap-2 text-sm font-medium text-slate mb-2">
                                        <Building2 size={14} className="text-slate/40" />
                                        Company Name <span className="text-ember">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={companyName}
                                        onChange={(e) => setCompanyName(e.target.value)}
                                        placeholder="e.g. Acme Industries"
                                        className="w-full h-11 px-4 rounded-lg border border-mist bg-linen/50 text-slate font-sans text-sm placeholder:text-slate/30 focus:outline-none focus:border-canopy focus:ring-1 focus:ring-canopy/20 transition-colors"
                                    />
                                </div>

                                <div>
                                    <label className="flex items-center gap-2 text-sm font-medium text-slate mb-2">
                                        <Factory size={14} className="text-slate/40" />
                                        Sector
                                    </label>
                                    <select
                                        value={sector}
                                        onChange={(e) => setSector(e.target.value)}
                                        className="w-full h-11 px-4 rounded-lg border border-mist bg-linen/50 text-slate font-sans text-sm focus:outline-none focus:border-canopy focus:ring-1 focus:ring-canopy/20 transition-colors"
                                    >
                                        <option value="">Select sector...</option>
                                        {SECTORS.map(s => (
                                            <option key={s} value={s}>{s}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="flex items-center gap-2 text-sm font-medium text-slate mb-2">
                                            <Globe size={14} className="text-slate/40" />
                                            Country
                                        </label>
                                        <select
                                            value={country}
                                            onChange={(e) => setCountry(e.target.value)}
                                            className="w-full h-11 px-4 rounded-lg border border-mist bg-linen/50 text-slate font-sans text-sm focus:outline-none focus:border-canopy focus:ring-1 focus:ring-canopy/20 transition-colors"
                                        >
                                            <option value="">Select country...</option>
                                            {COUNTRIES.map(c => (
                                                <option key={c} value={c}>{c}</option>
                                            ))}
                                        </select>
                                    </div>

                                    <div>
                                        <label className="flex items-center gap-2 text-sm font-medium text-slate mb-2">
                                            <Users size={14} className="text-slate/40" />
                                            Company Size
                                        </label>
                                        <input
                                            type="number"
                                            value={companySize}
                                            onChange={(e) => setCompanySize(e.target.value)}
                                            placeholder="Employees"
                                            className="w-full h-11 px-4 rounded-lg border border-mist bg-linen/50 text-slate font-sans text-sm placeholder:text-slate/30 focus:outline-none focus:border-canopy focus:ring-1 focus:ring-canopy/20 transition-colors"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 2: Buyer Profile (only for buyers) */}
                    {step === 2 && role === 'buyer' && (
                        <div className="p-10">
                            <h1 className="font-serif italic text-3xl text-slate text-center">
                                Your Carbon Profile
                            </h1>
                            <p className="text-slate/50 text-center mt-3 font-sans text-sm">
                                Help us tailor your experience
                            </p>

                            <div className="space-y-6 mt-8">
                                {/* Annual CO2 */}
                                <div>
                                    <label className="text-sm font-medium text-slate mb-2 block">
                                        Estimated annual CO&#8322; emissions (tonnes)
                                    </label>
                                    <input
                                        type="number"
                                        value={annualCo2}
                                        onChange={(e) => setAnnualCo2(e.target.value)}
                                        placeholder="e.g. 5000"
                                        className="w-full h-11 px-4 rounded-lg border border-mist bg-linen/50 text-slate font-sans text-sm placeholder:text-slate/30 focus:outline-none focus:border-canopy focus:ring-1 focus:ring-canopy/20 transition-colors"
                                    />
                                </div>

                                {/* Motivation */}
                                <div>
                                    <label className="text-sm font-medium text-slate mb-3 block">
                                        Primary offset motivation
                                    </label>
                                    <div className="grid grid-cols-2 gap-2">
                                        {MOTIVATIONS.map(m => (
                                            <button
                                                key={m.value}
                                                onClick={() => setMotivation(m.value)}
                                                className={`text-left p-3 rounded-lg border transition-all cursor-pointer bg-transparent ${motivation === m.value
                                                    ? 'border-canopy bg-canopy/5'
                                                    : 'border-mist hover:border-canopy/30'
                                                    }`}
                                            >
                                                <span className="text-sm font-medium text-slate block">{m.label}</span>
                                                <span className="text-xs text-slate/40 mt-0.5 block">{m.desc}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Preferred project types */}
                                <div>
                                    <label className="text-sm font-medium text-slate mb-3 block">
                                        Preferred project types
                                    </label>
                                    <div className="flex flex-wrap gap-2">
                                        {PROJECT_TYPES.map(pt => {
                                            const Icon = pt.icon;
                                            const active = preferredTypes.includes(pt.value);
                                            return (
                                                <button
                                                    key={pt.value}
                                                    onClick={() => toggleProjectType(pt.value)}
                                                    className={`flex items-center gap-2 px-3 py-2 rounded-full text-xs font-medium border transition-all cursor-pointer bg-transparent ${active
                                                        ? 'border-canopy bg-canopy/10 text-canopy'
                                                        : 'border-mist text-slate/50 hover:border-canopy/30 hover:text-slate'
                                                        }`}
                                                >
                                                    <Icon size={14} />
                                                    {pt.label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>

                                {/* Budget max */}
                                <div>
                                    <label className="text-sm font-medium text-slate mb-2 block">
                                        Maximum budget per tonne (EUR)
                                    </label>
                                    <input
                                        type="number"
                                        value={budgetMax}
                                        onChange={(e) => setBudgetMax(e.target.value)}
                                        placeholder="e.g. 25.00"
                                        step="0.01"
                                        className="w-full h-11 px-4 rounded-lg border border-mist bg-linen/50 text-slate font-sans text-sm placeholder:text-slate/30 focus:outline-none focus:border-canopy focus:ring-1 focus:ring-canopy/20 transition-colors"
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Footer with navigation buttons */}
                    <div className="px-10 py-6 bg-mist/20 border-t border-mist flex items-center justify-between">
                        {step > 0 ? (
                            <button
                                onClick={() => setStep(s => s - 1)}
                                className="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium text-slate/60 hover:text-slate transition-colors cursor-pointer bg-transparent border-0"
                            >
                                <ArrowLeft size={16} />
                                Back
                            </button>
                        ) : (
                            <div />
                        )}

                        {isLastStep ? (
                            <button
                                onClick={handleSubmit}
                                disabled={mutation.isPending || (step === 1 && !canProceedStep1)}
                                className="flex items-center gap-2 px-6 py-2.5 rounded-full text-sm font-semibold bg-canopy text-linen hover:bg-canopy/90 transition-colors cursor-pointer border-0 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {mutation.isPending ? (
                                    <Loader2 size={16} className="animate-spin" />
                                ) : null}
                                Get Started
                                <ArrowRight size={16} />
                            </button>
                        ) : (
                            <button
                                onClick={() => setStep(s => s + 1)}
                                disabled={step === 0 ? !canProceedStep0 : !canProceedStep1}
                                className="flex items-center gap-2 px-6 py-2.5 rounded-full text-sm font-semibold bg-canopy text-linen hover:bg-canopy/90 transition-colors cursor-pointer border-0 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Continue
                                <ArrowRight size={16} />
                            </button>
                        )}
                    </div>

                    {/* Error message */}
                    {mutation.isError && (
                        <div className="px-10 py-3 bg-red-50 border-t border-red-100">
                            <p className="text-sm text-red-600">
                                Something went wrong. Please try again.
                            </p>
                        </div>
                    )}
                </div>

                {/* Skip option for buyer profile step */}
                {step === 2 && role === 'buyer' && (
                    <p className="text-center mt-4 text-xs text-slate/40">
                        All fields are optional — you can update them later in settings.
                    </p>
                )}
            </div>
        </div>
    );
}
