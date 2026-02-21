import { useState } from "react";
import { Button } from "~/modules/shared/ui/button";
import { Input } from "~/modules/shared/ui/input";
import { Loader2, Copy, Check, Eye, EyeOff } from "lucide-react";

interface SecretRevealProps {
    value: string | null;
    isRevealed: boolean;
    isLoading: boolean;
    onReveal: () => void;
    onHide: () => void;
    placeholder?: string;
    label?: string;
    className?: string;
}

export const SecretReveal = ({
    value,
    isRevealed,
    isLoading,
    onReveal,
    onHide,
    placeholder = "••••••••••••",
    label,
    className
}: SecretRevealProps) => {
    const [copied, setCopied] = useState(false);

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleToggle = () => {
        if (isRevealed) {
            onHide();
        } else {
            onReveal();
        }
    };

    return (
        <div className={className}>
            {label && <span className="text-xs font-semibold text-muted-foreground uppercase">{label}</span>}
            <div className="flex items-center gap-2 mt-1">
                <Input
                    value={isRevealed && value ? value : placeholder}
                    readOnly
                    className="font-mono text-sm"
                    type={isRevealed ? "text" : "password"}
                />
                <Button
                    size="icon"
                    variant="outline"
                    onClick={handleToggle}
                    disabled={isLoading}
                    title={isRevealed ? "Hide" : "Reveal"}
                >
                    {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> :
                        (isRevealed ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />)
                    }
                </Button>
                {isRevealed && value && (
                    <Button size="icon" variant="outline" onClick={() => copyToClipboard(value)}>
                        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                )}
            </div>
        </div>
    );
};
