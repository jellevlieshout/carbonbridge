import { ArrowLeft } from "lucide-react";
import { Link } from "react-router";
import { Button } from "~/modules/shared/ui/button";

interface PageHeaderProps {
    title: string;
    description?: string;
    backUrl?: string;
    actions?: React.ReactNode;
}

export const PageHeader = ({ title, description, backUrl, actions }: PageHeaderProps) => {
    return (
        <div className="flex flex-col gap-4 mb-6">
            <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    {backUrl && (
                        <Button variant="ghost" size="icon" asChild className="-ml-2 shrink-0">
                            <Link to={backUrl}>
                                <ArrowLeft className="h-6 w-6" />
                                <span className="sr-only">Go back</span>
                            </Link>
                        </Button>
                    )}
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
                        {description && (
                            <p className="text-muted-foreground">{description}</p>
                        )}
                    </div>
                </div>
                {actions && (
                    <div className="flex items-center gap-2">
                        {actions}
                    </div>
                )}
            </div>
        </div>
    );
};
