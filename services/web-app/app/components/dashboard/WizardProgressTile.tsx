import React, { useEffect, useRef, useMemo } from 'react';
import { Link } from 'react-router';
import gsap from 'gsap';
import { Target, ListFilter, Wallet, Link as LinkIcon, CheckCircle2 } from 'lucide-react';
import { useUserResourcesQuery } from '~/modules/shared/queries/useUserResources';
import { useOrdersQuery } from '~/modules/shared/queries/useOrders';

const stepDefinitions = [
    { id: 1, label: 'Emissions Baseline Set', icon: Target },
    { id: 2, label: 'Credit Type Selected', icon: ListFilter },
    { id: 3, label: 'Budget Confirmed', icon: Wallet },
    { id: 4, label: 'Registry Account Linked', icon: LinkIcon },
    { id: 5, label: 'First Purchase Complete', icon: CheckCircle2 },
];

export function WizardProgressTile() {
    const containerRef = useRef<HTMLDivElement>(null);
    const { data: userData, isLoading: isUserLoading } = useUserResourcesQuery();
    const { data: orders, isLoading: isOrdersLoading } = useOrdersQuery();

    const isLoading = isUserLoading || isOrdersLoading;

    const steps = useMemo(() => {
        const user = userData?.user;
        const bp = user?.buyer_profile;

        const completions = [
            bp?.annual_co2_tonnes_estimate != null,
            (bp?.preferred_project_types?.length ?? 0) > 0,
            bp?.budget_per_tonne_max_eur != null,
            user?.stripe_customer_id != null,
            (orders ?? []).some((o: any) => o.status === 'completed'),
        ];

        let foundCurrent = false;
        return stepDefinitions.map((def, i) => {
            let status: 'completed' | 'current' | 'pending';
            if (completions[i] && !foundCurrent) {
                status = 'completed';
            } else if (!foundCurrent) {
                status = 'current';
                foundCurrent = true;
            } else {
                status = 'pending';
            }
            return { ...def, status };
        });
    }, [userData, orders]);

    const completedCount = steps.filter(s => s.status === 'completed').length;

    useEffect(() => {
        if (isLoading) return;

        const ctx = gsap.context(() => {
            gsap.fromTo(
                ".svg-check-path",
                { strokeDasharray: 100, strokeDashoffset: 100 },
                { strokeDashoffset: 0, duration: 0.8, ease: "power2.out", stagger: 0.15, delay: 0.5 }
            );

            gsap.fromTo(
                ".wizard-row",
                { opacity: 0, x: -10 },
                { opacity: 1, x: 0, duration: 0.5, stagger: 0.1, ease: "power2.out" }
            );
        }, containerRef);
        return () => ctx.revert();
    }, [isLoading]);

    return (
        <div
            ref={containerRef}
            className="flex flex-col h-full w-full rounded-[1.25rem] bg-white border border-mist p-6 shadow-sm overflow-hidden"
        >
            <div className="flex items-center justify-between mb-6">
                <h3 className="font-sans font-semibold text-slate tracking-tight">Onboarding Protocol Tracker</h3>
                <span className="font-mono text-[10px] uppercase font-semibold text-canopy tracking-wider bg-canopy/10 px-2 py-1 rounded-[1rem]">{completedCount}/5 Complete</span>
            </div>

            <div className="flex-1 flex flex-col justify-between gap-1">
                {steps.map((step) => {
                    const isCompleted = step.status === 'completed';
                    const isCurrent = step.status === 'current';

                    let rowClasses = "wizard-row flex items-center gap-4 p-3 rounded-xl transition-all duration-300 ";

                    if (isCompleted) {
                        rowClasses += "bg-mist/30 text-slate";
                    } else if (isCurrent) {
                        rowClasses += "bg-white border text-slate border-ember shadow-sm animate-pulse-gentle ";
                    } else {
                        rowClasses += "bg-transparent text-slate/40";
                    }

                    return (
                        <div key={step.id} className={rowClasses}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${isCompleted ? 'bg-canopy text-linen' : isCurrent ? 'bg-ember/10 text-ember' : 'bg-mist text-slate/40'}`}>
                                {isCompleted ? (
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 text-linen">
                                        <path className="svg-check-path" d="M20 6L9 17l-5-5" />
                                    </svg>
                                ) : (
                                    <step.icon size={16} strokeWidth={2} />
                                )}
                            </div>
                            <div className="flex-1 flex items-center justify-between">
                                <span className={`font-sans font-medium text-sm ${isCompleted ? 'text-slate' : isCurrent ? 'text-slate' : 'text-slate/60'}`}>
                                    {step.label}
                                </span>
                                {isCurrent && (
                                    <Link
                                        to="/buyer/wizard"
                                        className="text-[10px] font-bold uppercase tracking-wider text-ember hover:text-ember/80 transition-colors cursor-pointer"
                                    >
                                        Resume
                                    </Link>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
