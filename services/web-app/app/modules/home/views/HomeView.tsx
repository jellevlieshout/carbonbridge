import { Navigate } from "react-router";
import { AnonymousView } from "~/modules/auth/views/AnonymousView";
import { AuthenticatingView } from "~/modules/auth/views/AuthenticatingView";
import { SessionExpiredView } from "~/modules/auth/views/SessionExpiredView";

interface HomeViewProps {
    isLoggedIn: boolean;
    isPageLoaded: boolean;
    isSessionExpired: boolean;
    needsOnboarding: boolean;
    isUserLoading: boolean;
    userRole?: string;
}

export const HomeView = ({ isLoggedIn, isPageLoaded, isSessionExpired, needsOnboarding, isUserLoading, userRole }: HomeViewProps) => {
    if (isSessionExpired) {
        return <SessionExpiredView />;
    }

    if (!isPageLoaded) {
        return <AuthenticatingView />;
    }

    if (isLoggedIn && isUserLoading) {
        return <AuthenticatingView />;
    }

    if (isLoggedIn && needsOnboarding) {
        return <Navigate to="/onboarding" replace />;
    }

    if (isLoggedIn) {
        const destination = userRole === 'seller' ? '/seller/listings' : '/buyer/dashboard';
        return <Navigate to={destination} replace />;
    }

    return <AnonymousView />;
};
