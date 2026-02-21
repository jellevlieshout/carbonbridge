import React from 'react';

export function AuthenticatingView() {
    return (
        <div
            className="flex flex-col items-center min-h-[100dvh] w-full p-4"
            style={{
                background: '#336050'
            }}
        >
            <div className="flex-1 flex flex-col items-center justify-center w-full max-w-md">
                <img
                    src="/TODO"
                    alt="TODO"
                    className="h-16 md:h-24 w-auto"
                />

                <div className="mt-16 text-white text-lg font-semibold animate-pulse">
                    Authenticating...
                </div>
            </div>
        </div>
    );
}
