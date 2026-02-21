import { TopBar } from "~/modules/layout/components/TopBar/TopBarPresenter";
import { LoaderCircle } from "lucide-react";
import { AuthProvider } from "@clients/api/modules/phantom-token-handler-secured-api-client/AuthContext";

export function PageSkeleton() {
    return (
        <AuthProvider>
            <div className="flex flex-col min-h-screen bg-background text-foreground">
                <TopBar />
                <main className="flex-1 py-4 px-[20px] max-w-4xl w-full flex items-center justify-center">
                    <LoaderCircle className="animate-spin text-primary w-12 h-12" />
                </main>
            </div>
        </AuthProvider>
    );
}
