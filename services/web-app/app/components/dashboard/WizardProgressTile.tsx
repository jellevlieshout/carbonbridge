import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { Target, ListFilter, Wallet, Link, CheckCircle2 } from 'lucide-react';

const steps = [
    { id: 1, label: 'Emissions Baseline Set', icon: Target, status: 'completed' },
    { id: 2, label: 'Credit Type Selected', icon: ListFilter, status: 'completed' },
    { id: 3, label: 'Budget Confirmed', icon: Wallet, status: 'completed' },
    { id: 4, label: 'Registry Account Linked', icon: Link, status: 'current' },
    { id: 5, label: 'First Purchase Complete', icon: CheckCircle2, status: 'pending' },
];

export function WizardProgressTile() {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const ctx = gsap.context(() => {
            // Animate the SVG checkmarks drawing themselves
            gsap.fromTo(
                ".svg-check-path",
                { strokeDasharray: 100, strokeDashoffset: 100 },
                { strokeDashoffset: 0, duration: 0.8, ease: "power2.out", stagger: 0.15, delay: 0.5 }
            );

            // Animate the rows staggering in
            gsap.fromTo(
                ".wizard-row",
                { opacity: 0, x: -10 },
                { opacity: 1, x: 0, duration: 0.5, stagger: 0.1, ease: "power2.out" }
            );
        }, containerRef);
        return () => ctx.revert();
    }, []);

    return (
        <div
            ref={containerRef}
            className="flex flex-col h-full w-full rounded-[1.25rem] bg-white border border-mist p-6 shadow-sm overflow-hidden"
        >
            <div className="flex items-center justify-between mb-6">
                <h3 className="font-sans font-semibold text-slate tracking-tight">Onboarding Protocol Tracker</h3>
                <span className="font-mono text-[10px] uppercase font-semibold text-canopy tracking-wider bg-canopy/10 px-2 py-1 rounded-[1rem]">3/5 Complete</span>
            </div>

            <div className="flex-1 flex flex-col justify-between gap-1">
                {steps.map((step) => {
                    const isCompleted = step.status === 'completed';
                    const isCurrent = step.status === 'current';
                    const isPending = step.status === 'pending';

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
                                    <button className="text-[10px] font-bold uppercase tracking-wider text-ember hover:text-ember/80 transition-colors uppercase cursor-pointer">
                                        Resume
                                    </button>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
