import React from "react";
import type { Route } from "./+types/wizard";
import { Suspense } from "react";
import { PageSkeleton } from "~/modules/shared/components/PageSkeleton";
import { WizardPresenter } from "~/modules/wizard/presenters/WizardPresenter";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Purchase Wizard — CarbonBridge" },
    { name: "description", content: "Guided carbon credit purchasing wizard" },
  ];
}

export default function Wizard() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <WizardPresenter />
    </Suspense>
  );
}
