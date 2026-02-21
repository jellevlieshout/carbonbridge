import { useMemo } from "react";
import { type WizardStep, STEP_ORDER, STEP_LABELS, stepToVisualIndex } from "../types";

export const useWizardNavigation = (currentStep: WizardStep) => {
  return useMemo(() => {
    const currentIndex = stepToVisualIndex(currentStep);
    const totalSteps = STEP_ORDER.length;
    const label = STEP_LABELS[currentStep];

    return {
      currentIndex,
      totalSteps,
      label,
      steps: STEP_ORDER,
      stepLabels: STEP_LABELS,
    };
  }, [currentStep]);
};
