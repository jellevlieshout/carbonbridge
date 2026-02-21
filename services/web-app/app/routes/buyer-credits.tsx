import React, { useEffect, useRef } from "react";
import { useSearchParams } from "react-router";
import { useOrders, useConfirmPayment } from "~/modules/shared/queries/useOrders";
import { useListingQuery } from "~/modules/shared/queries/useListing";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/modules/shared/ui/card";
import { Badge } from "~/modules/shared/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/modules/shared/ui/table";
import { Leaf, Award, Clock } from "lucide-react";
import { toast } from "sonner";

function ListingCell({ listingId }: { listingId: string }) {
    const { data: listing, isLoading } = useListingQuery(listingId);

    if (isLoading) return <span className="text-muted-foreground animate-pulse">Loading project details...</span>;
    if (!listing) return <span className="text-muted-foreground">Unknown project</span>;

    return (
        <div className="flex flex-col">
            <span className="font-medium text-foreground">{listing.project_name}</span>
            <span className="text-xs text-muted-foreground">{listing.project_type.replace('_', ' ')} • {listing.registry_name}</span>
        </div>
    );
}

export default function BuyerCreditsPage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const confirmPayment = useConfirmPayment();
    const confirmedRef = useRef(false);
    const { data: orders, isLoading, isError, error } = useOrders();

    useEffect(() => {
        const paymentIntentId = searchParams.get("payment_intent");
        const redirectStatus = searchParams.get("redirect_status");

        if (paymentIntentId && redirectStatus === "succeeded" && !confirmedRef.current) {
            confirmedRef.current = true;
            confirmPayment.mutate(paymentIntentId, {
                onSuccess: () => toast.success("Payment confirmed!"),
                onError: () => toast.error("Could not confirm payment. Please contact support."),
            });
            setSearchParams({}, { replace: true });
        }
    }, [searchParams]);

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px]">
                <div className="w-8 h-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-4" />
                <p className="text-muted-foreground animate-pulse font-medium">Loading your credits...</p>
            </div>
        );
    }

    if (isError) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
                <Leaf className="w-12 h-12 text-destructive/20 mb-4" />
                <h3 className="text-lg font-semibold text-foreground mb-2">Failed to load credits</h3>
                <p className="text-muted-foreground">{error instanceof Error ? error.message : "An unexpected error occurred."}</p>
            </div>
        );
    }

    const totalTonnesFetched = (orders || [])
        .filter(o => o.status === "completed")
        .reduce((sum, o) => sum + o.line_items.reduce((lsum, li) => lsum + li.quantity, 0), 0);

    return (
        <div className="flex flex-col gap-8 w-full animate-in fade-in duration-700 max-w-7xl mx-auto py-8">
            <div className="flex justify-between items-end">
                <div className="flex flex-col gap-2">
                    <h1 className="text-4xl font-bold tracking-tight text-foreground">My Carbon Credits</h1>
                    <p className="text-muted-foreground text-lg max-w-2xl">
                        View and manage your verified climate impact portfolio.
                    </p>
                </div>

                <Card className="bg-primary/5 border-primary/20 shadow-none min-w-[200px]">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="bg-primary/20 p-3 rounded-full">
                            <Leaf className="w-8 h-8 text-primary" />
                        </div>
                        <div className="flex flex-col">
                            <span className="text-sm font-medium text-muted-foreground">Total Offset</span>
                            <span className="text-2xl font-bold text-foreground">{totalTonnesFetched.toFixed(1)} <span className="text-sm font-normal">tonnes</span></span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {orders.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-12 text-center border rounded-xl bg-card/50 text-muted-foreground">
                    <Award className="w-12 h-12 mb-4 opacity-20" />
                    <p className="text-lg font-medium">You haven't purchased any carbon credits yet.</p>
                    <p className="text-sm mt-1">Visit the marketplace or start the wizard to make a positive impact.</p>
                </div>
            ) : (
                <Card className="border-border/40 shadow-sm overflow-hidden">
                    <CardHeader className="bg-muted/20 pb-4">
                        <CardTitle className="text-xl">Transaction History</CardTitle>
                        <CardDescription>All your credit purchases and reservations</CardDescription>
                    </CardHeader>
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-muted/50 hover:bg-muted/50">
                                    <TableHead className="w-[120px]">Order ID</TableHead>
                                    <TableHead>Project</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead className="text-right">Quantity</TableHead>
                                    <TableHead className="text-right">Total Price</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {orders.map((order) => {
                                    return order.line_items.map((item, index) => (
                                        <TableRow key={`${order.id}-${index}`} className="hover:bg-muted/20 transition-colors">
                                            <TableCell className="font-mono text-xs text-muted-foreground">
                                                {index === 0 ? order.id.substring(0, 8) : ''}
                                            </TableCell>
                                            <TableCell>
                                                <ListingCell listingId={item.listing_id} />
                                            </TableCell>
                                            <TableCell>
                                                {index === 0 && (
                                                    <Badge
                                                        variant={order.status === 'completed' ? 'default' : (order.status === 'pending' ? 'secondary' : 'outline')}
                                                        className={order.status === 'completed' ? "bg-green-500/10 text-green-600 hover:bg-green-500/20 shadow-none border-green-200" : ""}
                                                    >
                                                        {order.status === 'pending' && <Clock className="w-3 h-3 mr-1" />}
                                                        {order.status}
                                                    </Badge>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-right font-medium">
                                                {item.quantity} t
                                            </TableCell>
                                            <TableCell className="text-right">
                                                {index === 0 ? (
                                                    <span className="font-semibold">€{order.total_eur.toFixed(2)}</span>
                                                ) : <span className="text-muted-foreground">in total</span>}
                                            </TableCell>
                                        </TableRow>
                                    ));
                                })}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
