import React from 'react';
import { Link } from 'react-router';

export default function NotFound() {
    return (
        <div
            className="flex flex-col items-center min-h-[100dvh] w-full p-4"
            style={{
                background: '#336050'
            }}
        >
            <div className="flex-1 flex flex-col items-center justify-center w-full max-w-md text-center">
                <img
                    src="/TODO"
                    alt="TODO"
                    className="h-16 md:h-24 w-auto mb-8"
                />

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
