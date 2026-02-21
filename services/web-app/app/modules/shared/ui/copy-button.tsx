import { useState } from "react";
import { Button } from "~/modules/shared/ui/button";
import { Copy, Check } from "lucide-react";
import { cn } from "~/lib/utils";

interface CopyButtonProps {
    value: string;
    variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
    size?: "default" | "sm" | "lg" | "icon";
    className?: string;
}

export const CopyButton = ({ value, variant = "ghost", size = "sm", className }: CopyButtonProps) => {
    const [copied, setCopied] = useState(false);

    const onCopy = async () => {
        try {
            await navigator.clipboard.writeText(value);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy text: ', err);
        }
    };

    return (
        <Button size={size} variant={variant} className={className} onClick={onCopy}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
        </Button>
    );
};
