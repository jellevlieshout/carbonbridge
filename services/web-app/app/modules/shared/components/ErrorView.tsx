import { Link } from 'react-router';

interface ErrorViewProps {
    message: string;
    details: string;
    showTryAgain?: boolean;
}

export function ErrorView({ message, details, showTryAgain = true }: ErrorViewProps) {
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

                <h1 className="text-6xl font-bold text-white mb-4">{message}</h1>
                <p className="text-xl text-white mb-8">{details}</p>

                <div className="flex flex-col sm:flex-row gap-4">
                    <Link
                        to="/"
                        className="bg-white text-blue-900 px-6 py-3 rounded-full font-semibold hover:bg-opacity-90 transition-all duration-200 no-underline"
                    >
                        Return to Home
                    </Link>
                    {showTryAgain && (
                        <button
                            onClick={() => window.location.reload()}
                            className="bg-transparent border-2 border-white text-white px-6 py-3 rounded-full font-semibold hover:bg-white hover:text-blue-900 transition-all duration-200 cursor-pointer"
                        >
                            Try again
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
