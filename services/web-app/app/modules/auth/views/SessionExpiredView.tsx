import React from 'react';
import { startLogin } from '@clients/api/client';
import { ErrorRenderer } from '@clients/api/modules/phantom-token-handler-secured-api-client/utilities/errorRenderer';
import { Button } from '~/modules/shared/ui/button';
import { Logo } from '~/modules/shared/components/Logo';

export function SessionExpiredView() {
    async function handleLogin() {
        try {
            const response = await startLogin();
            location.href = response.authorizationUrl;
        } catch (e: any) {
            alert(ErrorRenderer.toDisplayFormat(e));
        }
    }

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

                <h1 className="text-4xl font-bold text-white mb-4">Session Expired</h1>
                <p className="text-xl text-white mb-8">Your session has timed out. Please log in again to continue.</p>

                <Button
                    onClick={handleLogin}
                    size="lg"
                    className="font-semibold text-lg px-8 bg-white text-[rgb(0,74,173)] hover:bg-gray-100 cursor-pointer w-full md:w-auto whitespace-normal h-auto py-3 rounded-full"
                >
                    Log in
                </Button>
            </div>
        </div>
    );
}
