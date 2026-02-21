import React, { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements } from "@stripe/react-stripe-js";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "~/modules/shared/ui/dialog";
import { Button } from "~/modules/shared/ui/button";
import { Input } from "~/modules/shared/ui/input";
import { Label } from "~/modules/shared/ui/label";
import { useCreateOrder, useCancelOrder } from "~/modules/shared/queries/useOrders";
import { CheckoutForm } from "./CheckoutForm";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router";

// It's best to initialize stripe outside the component render
// We'll require the public key to be available via Vite env vars
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLIC_KEY || "");

interface CheckoutModalProps {
    isOpen: boolean;
    onClose: () => void;
    listingId: string;
    listingName: string;
    pricePerTonne: number;
    availableTonnes: number;
}

export function CheckoutModal({
    isOpen,
    onClose,
    listingId,
    listingName,
    pricePerTonne,
    availableTonnes
}: CheckoutModalProps) {
    const navigate = useNavigate();
    const [quantity, setQuantity] = useState<number>(1);
    const [clientSecret, setClientSecret] = useState<string | null>(null);
    const [orderId, setOrderId] = useState<string | null>(null);

    const createOrderMutation = useCreateOrder();
    const cancelOrderMutation = useCancelOrder();

    // Reset state when modal opens
    useEffect(() => {
        if (isOpen) {
            setQuantity(1);
            setClientSecret(null);
            setOrderId(null);
        }
    }, [isOpen]);

    const handleContinueToPayment = async () => {
        if (quantity <= 0 || quantity > availableTonnes) {
            toast.error("Invalid quantity");
            return;
        }

        try {
            const order = await createOrderMutation.mutateAsync({
                line_items: [{ listing_id: listingId, quantity }],
                retirement_requested: false // Defaulting to false for simple buy, can be enhanced later
            });

            setOrderId(order.id);
            if (order.stripe_client_secret) {
                setClientSecret(order.stripe_client_secret);
            } else {
                toast.error("Could not initialize payment.");
            }
        } catch (error: any) {
            toast.error(error.message || "Failed to create order");
        }
    };

    const handlePaymentSuccess = () => {
        setOrderId(null);
        toast.success("Payment successful!");
        onClose();
        navigate("/buyer-credits");
    };

    const handleClose = () => {
        if (orderId) {
            cancelOrderMutation.mutate(orderId);
        }
        onClose();
    };

    const totalCost = (quantity * pricePerTonne).toFixed(2);

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Complete Purchase</DialogTitle>
                    <DialogDescription>
                        You are buying credits from <strong>{listingName}</strong>.
                    </DialogDescription>
                </DialogHeader>

                {!clientSecret ? (
                    <div className="flex flex-col gap-6 py-4">
                        <div className="flex flex-col gap-2">
                            <Label htmlFor="quantity">Quantity (Tonnes)</Label>
                            <Input
                                id="quantity"
                                type="number"
                                min={1}
                                max={availableTonnes}
                                value={quantity}
                                onChange={(e) => setQuantity(Number(e.target.value))}
                            />
                            <p className="text-xs text-muted-foreground">
                                {availableTonnes} tonnes available
                            </p>
                        </div>

                        <div className="flex justify-between items-center py-4 border-t border-b">
                            <span className="font-medium text-muted-foreground">Total Cost</span>
                            <span className="text-xl font-bold">€{totalCost}</span>
                        </div>

                        <Button
                            onClick={handleContinueToPayment}
                            disabled={createOrderMutation.isPending || quantity <= 0 || quantity > availableTonnes}
                            className="w-full"
                        >
                            {createOrderMutation.isPending ? (
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            ) : null}
                            Continue to Payment
                        </Button>
                    </div>
                ) : (
                    <div className="py-4">
                        <Elements stripe={stripePromise} options={{ clientSecret }}>
                            <CheckoutForm clientSecret={clientSecret} onSuccess={handlePaymentSuccess} />
                        </Elements>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
