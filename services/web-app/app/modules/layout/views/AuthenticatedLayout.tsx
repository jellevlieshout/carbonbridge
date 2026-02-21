import { ReactNode } from "react";
import { TopBar } from "~/modules/layout/components/TopBar/TopBarPresenter";
import { cn } from "~/lib/utils";

export function AuthenticatedLayout({ children, className }: { children: ReactNode; className?: string }) {
    return (
        <div className="flex flex-col min-h-screen bg-background text-foreground">
            <TopBar />
            <main className={cn("flex-1 py-4 px-[20px] flex flex-col gap-4 max-w-8xl w-full", className)}>
                {children}
            </main>
        </div>
    );
}
