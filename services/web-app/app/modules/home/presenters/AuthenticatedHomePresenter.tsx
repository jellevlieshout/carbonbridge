import { useUserResources } from "~/modules/shared/queries/useUserResources";
import { AuthenticatedHomeView } from '../views/AuthenticatedHomeView';
import { AuthenticatedLayout } from "~/modules/layout/views/AuthenticatedLayout";

export function AuthenticatedHomePresenter() {
    const { data: userResources, isLoading } = useUserResources();

    if (isLoading) {
        return null; // Or a loading skeleton
    }

    return (
        <AuthenticatedLayout>
            <AuthenticatedHomeView
                userResources={userResources || { user: null, accounts: [], wallet: null }}
            />
        </AuthenticatedLayout>
    );
}
