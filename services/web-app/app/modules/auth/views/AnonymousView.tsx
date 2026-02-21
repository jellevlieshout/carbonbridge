import React from 'react';
import { startLogin } from '@clients/api/client';
import { ErrorRenderer } from '@clients/api/modules/phantom-token-handler-secured-api-client/utilities/errorRenderer';
import { Button } from '~/modules/shared/ui/button';
import { Logo } from '~/modules/shared/components/Logo';

export function AnonymousView() {
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
            <div className="flex-1 flex flex-col items-center justify-center w-full max-w-md">
                <Logo size="lg" variant="light" />

                <Button
                    onClick={handleLogin}
                    size="lg"
                    className="mt-16 font-semibold text-lg px-8 bg-white text-[rgb(0,74,173)] hover:bg-gray-100 cursor-pointer w-full md:w-auto whitespace-normal h-auto py-3"
                >
                    Log in or sign up
                </Button>
            </div>




        </div>
    );
}
