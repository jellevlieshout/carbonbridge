import React from "react";
import { cn } from "~/lib/utils";
import { STEP_ORDER, STEP_LABELS } from "../types";

interface WizardProgressDotsProps {
  currentIndex: number;
}

export function WizardProgressDots({ currentIndex }: WizardProgressDotsProps) {
  return (
    <div className="flex items-center justify-center gap-0 py-4">
      {STEP_ORDER.map((step, i) => {
        const isCompleted = i < currentIndex;
        const isCurrent = i === currentIndex;

        return (
          <React.Fragment key={step}>
            {/* Connecting line */}
            {i > 0 && (
              <div
                className={cn(
                  "h-0.5 w-10 transition-colors duration-300",
                  isCompleted ? "bg-canopy" : "bg-mist",
                )}
              />
            )}
            {/* Dot */}
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={cn(
                  "w-3 h-3 rounded-full transition-all duration-300",
                  isCompleted && "bg-canopy",
                  isCurrent && "bg-ember ring-2 ring-ember/30 scale-125",
                  !isCompleted && !isCurrent && "bg-mist",
                )}
              />
              <span
                className={cn(
                  "text-[10px] font-medium whitespace-nowrap",
                  isCurrent ? "text-ember" : isCompleted ? "text-canopy" : "text-slate/40",
                )}
              >
                {STEP_LABELS[step]}
              </span>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
}
