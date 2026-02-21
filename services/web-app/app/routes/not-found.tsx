import React from 'react';
import { Link } from 'react-router';
import { Logo } from '~/modules/shared/components/Logo';
import type { Route } from "./+types/not-found";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Page Not Found" },
        { name: "description", content: "The page you are looking for does not exist." },
    ];
}

export default function NotFound() {
    return (
        <div
            className="flex flex-col items-center min-h-[100dvh] w-full p-4"
            style={{
                background: '#336050'
            }}
        >
            <div className="flex-1 flex flex-col items-center justify-center w-full max-w-md text-center">
                <div className="mb-8">
                    <Logo size="lg" variant="light" />
                </div>

                <h1 className="text-6xl font-bold text-white mb-4">404</h1>
                <p className="text-xl text-white mb-8">We haven't built this page (yet)</p>

                <Link
                    to="/"
                    className="bg-white text-blue-900 px-6 py-3 rounded-full font-semibold hover:bg-opacity-90 transition-all duration-200"
                >
                    Return to Home
                </Link>
            </div>
        </div>
    );
}
