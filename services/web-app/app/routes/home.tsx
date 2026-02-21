import React from 'react';
import type { Route } from "./+types/home";
import { Suspense } from 'react';
import { PageSkeleton } from '~/modules/shared/components/PageSkeleton';
import { HomePresenter } from "~/modules/home/presenters/HomePresenter";

export function meta({ }: Route.MetaArgs) {
  return [
    { title: "Smart SEB Lab" },
    { name: "description", content: "Smart SEB Lab Application" },
  ];
}

export default function Home() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <HomePresenter />
    </Suspense>
  );
}
