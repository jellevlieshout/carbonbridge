import React from 'react';
import { Logo } from '~/modules/shared/components/Logo';

export function AuthenticatingView() {
    return (
        <div
            className="flex flex-col items-center min-h-[100dvh] w-full p-4"
            style={{
                background: '#336050'
            }}
        >
            <div className="flex-1 flex flex-col items-center justify-center w-full max-w-md">
                <Logo size="lg" variant="light" />

                <div className="mt-16 text-white text-lg font-semibold animate-pulse">
                    Authenticating...
                </div>
            </div>
        </div>
    );
}
