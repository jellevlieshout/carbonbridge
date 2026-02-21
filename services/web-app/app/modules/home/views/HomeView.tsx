import { AuthenticatedHomePresenter as AuthenticatedHome } from "~/modules/home/presenters/AuthenticatedHomePresenter";
import { AnonymousView } from "~/modules/auth/views/AnonymousView";
import { AuthenticatingView } from "~/modules/auth/views/AuthenticatingView";
import { SessionExpiredView } from "~/modules/auth/views/SessionExpiredView";

interface HomeViewProps {
    isLoggedIn: boolean;
    isPageLoaded: boolean;
    isSessionExpired: boolean;
}

export const HomeView = ({ isLoggedIn, isPageLoaded, isSessionExpired }: HomeViewProps) => {
    if (isSessionExpired) {
        return <SessionExpiredView />;
    }

    if (!isPageLoaded) {
        return <AuthenticatingView />;
    }

    if (isLoggedIn) {
        return <AuthenticatedHome />;
    }

    return <AnonymousView />;
};
