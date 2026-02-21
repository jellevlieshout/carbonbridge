import { useAuth } from "@clients/api/modules/phantom-token-handler-secured-api-client/AuthContext";
import { HomeView } from "../views/HomeView";

export const HomePresenter = () => {
    const { isLoggedIn, isPageLoaded, isSessionExpired } = useAuth();

    return <HomeView isLoggedIn={isLoggedIn} isPageLoaded={isPageLoaded} isSessionExpired={isSessionExpired} />;
};
