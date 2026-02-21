import React, { useState } from "react";
import { useStripe, useElements, PaymentElement } from "@stripe/react-stripe-js";
import { Button } from "~/modules/shared/ui/button";
import { Alert, AlertDescription } from "~/modules/shared/ui/alert";
import { Loader2 } from "lucide-react";
import { orderConfirmPayment } from "@clients/api/orders";

interface CheckoutFormProps {
    clientSecret: string;
    onSuccess?: () => void;
}

export function CheckoutForm({ clientSecret, onSuccess }: CheckoutFormProps) {
    const stripe = useStripe();
    const elements = useElements();

    const [isProcessing, setIsProcessing] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!stripe || !elements) return;

        setIsProcessing(true);
        setErrorMessage(null);

        const { error, paymentIntent } = await stripe.confirmPayment({
            elements,
            confirmParams: {
                return_url: `${window.location.origin}/buyer/credits`,
            },
            redirect: "if_required",
        });

        if (error) {
            setErrorMessage(error.message ?? "An error occurred during payment.");
        } else if (paymentIntent && paymentIntent.status === "succeeded") {
            await orderConfirmPayment(paymentIntent.id);
            if (onSuccess) onSuccess();
        }

        setIsProcessing(false);
    };

    return (
        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            <PaymentElement />

            {errorMessage && (
                <Alert variant="destructive">
                    <AlertDescription>{errorMessage}</AlertDescription>
                </Alert>
            )}

            <Button type="submit" disabled={isProcessing || !stripe || !elements} className="w-full">
                {isProcessing ? (
                    <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Processing...
                    </>
                ) : (
                    "Confirm Payment"
                )}
            </Button>
        </form>
    );
}
