import React, { useEffect, useRef } from "react";
import gsap from "gsap";

interface WizardCardProps {
  stepLabel: string;
  stepNumber: number;
  totalSteps: number;
  children: React.ReactNode;
}

export function WizardCard({ stepLabel, stepNumber, totalSteps, children }: WizardCardProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const prevStep = useRef(stepNumber);

  useEffect(() => {
    if (prevStep.current !== stepNumber && contentRef.current) {
      gsap.fromTo(
        contentRef.current,
        { x: 40, opacity: 0 },
        { x: 0, opacity: 1, duration: 0.4, ease: "power2.out" },
      );
    }
    prevStep.current = stepNumber;
  }, [stepNumber]);

  return (
    <div className="flex flex-col rounded-[1.25rem] bg-white border border-mist shadow-sm overflow-hidden min-h-[calc(100vh-12rem)]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-mist">
        <h2 className="font-sans font-semibold text-slate tracking-tight">{stepLabel}</h2>
        <span className="font-mono text-[10px] uppercase font-semibold text-canopy tracking-wider bg-canopy/10 px-2 py-1 rounded-[1rem]">
          Step {stepNumber + 1} of {totalSteps}
        </span>
      </div>

      {/* Content */}
      <div ref={contentRef} className="flex-1 flex flex-col">
        {children}
      </div>
    </div>
  );
}
