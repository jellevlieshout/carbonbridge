import { useUserResources } from "~/modules/shared/queries/useUserResources";
import { AuthenticatedHomeView } from '../views/AuthenticatedHomeView';
import { AuthenticatedLayout } from "~/modules/layout/views/AuthenticatedLayout";

export function AuthenticatedHomePresenter() {
    const { data: userResources } = useUserResources();

    return (
        <AuthenticatedLayout>
            <AuthenticatedHomeView
                userResources={userResources}
            />
        </AuthenticatedLayout>
    );
}
