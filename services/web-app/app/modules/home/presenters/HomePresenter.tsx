import { useAuth } from "@clients/api/modules/phantom-token-handler-secured-api-client/AuthContext";
import { useUserResourcesQuery } from "~/modules/shared/queries/useUserResources";
import { HomeView } from "../views/HomeView";

export const HomePresenter = () => {
    const { isLoggedIn, isPageLoaded, isSessionExpired } = useAuth();
    const { data: userData, isLoading: isUserLoading } = useUserResourcesQuery({ enabled: isLoggedIn });

    const needsOnboarding = isLoggedIn && !isUserLoading && userData?.user && !userData.user.company_name;

    return (
        <HomeView
            isLoggedIn={isLoggedIn}
            isPageLoaded={isPageLoaded}
            isSessionExpired={isSessionExpired}
            needsOnboarding={!!needsOnboarding}
            isUserLoading={isUserLoading && isLoggedIn}
            userRole={userData?.user?.role}
        />
    );
};
