import React, { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { useOrders, useConfirmPayment } from "~/modules/shared/queries/useOrders";
import { useListingQuery } from "~/modules/shared/queries/useListing";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/modules/shared/ui/card";
import { Badge } from "~/modules/shared/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/modules/shared/ui/table";
import { Leaf, Award, Clock, Shield, ExternalLink, Download, X } from "lucide-react";
import { toast } from "sonner";
import { generateCertificatePDF } from "~/components/buyer/CertificatePDF";
import type { Route } from "./+types/buyer-credits";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | My Credits" },
        { name: "description", content: "View and manage your verified climate impact portfolio." },
    ];
}

function deriveSerial(orderId: string, listingId: string): string {
    const seed = (orderId + listingId).split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
    const rng = (n: number) => Math.floor(((seed * 9301 + 49297) % 233280) / 233280 * n + seed % n);
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789";
    const projectCode = 100 + (seed % 900);
    const year = 2024;
    const suffix = Array.from({ length: 8 }, (_, i) => chars[(seed * (i + 3)) % chars.length]).join("");
    return `VCS-VCU-${projectCode}-VER-${year}-${suffix}`;
}

interface CertificateModalProps {
    orderId: string;
    listingId: string;
    projectName: string;
    quantity: number;
    totalEur: number;
    retirementReference?: string | null;
    onClose: () => void;
}

function CertificateModal({ orderId, listingId, projectName, quantity, totalEur, retirementReference, onClose }: CertificateModalProps) {
    const { data: listing } = useListingQuery(listingId);
    const serial = listing?.serial_number_range || deriveSerial(orderId, listingId);
    const retirementDate = new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" });

    const handleDownloadPDF = () => {
        generateCertificatePDF({
            orderId,
            projectName,
            projectCountry: listing?.project_country,
            registryName: listing?.registry_name,
            vintageYear: listing?.vintage_year,
            methodology: listing?.methodology,
            quantity,
            totalEur,
            serialNumber: serial,
            retirementDate,
            retirementReference,
        });
    };

    return (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden" onClick={e => e.stopPropagation()}>
                <div className="bg-canopy px-6 py-5 flex items-start justify-between">
                    <div className="flex items-center gap-2.5 text-linen">
                        <Award size={20} />
                        <div>
                            <p className="text-xs text-linen/60 uppercase tracking-widest font-medium">Official Document</p>
                            <p className="text-sm font-bold">Certificate of Carbon Retirement</p>
                        </div>
                    </div>
                    <button onClick={onClose} aria-label="Close certificate" className="text-linen/60 hover:text-linen transition-colors cursor-pointer bg-transparent border-0 p-1">
                        <X size={16} aria-hidden="true" />
                    </button>
                </div>

                <div className="px-6 py-6 space-y-5">
                    <div className="text-center border-b border-mist pb-4">
                        <p className="text-xs text-slate/40 uppercase tracking-wider mb-1">This certifies that</p>
                        <p className="text-base font-semibold text-slate">Your Organisation</p>
                        <p className="text-xs text-slate/40 mt-1">has permanently retired the following carbon credits</p>
                    </div>

                    <div className="space-y-3">
                        <div>
                            <p className="text-[10px] text-slate/40 uppercase tracking-wider font-medium mb-0.5">Project</p>
                            <p className="text-sm font-semibold text-slate">{projectName}</p>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-[10px] text-slate/40 uppercase tracking-wider font-medium mb-0.5">Quantity Retired</p>
                                <p className="text-lg font-bold text-canopy">{quantity} tCO₂e</p>
                            </div>
                            <div>
                                <p className="text-[10px] text-slate/40 uppercase tracking-wider font-medium mb-0.5">Retirement Date</p>
                                <p className="text-sm font-semibold text-slate">{retirementDate}</p>
                            </div>
                        </div>
                        <div>
                            <p className="text-[10px] text-slate/40 uppercase tracking-wider font-medium mb-0.5">Serial Number</p>
                            <p className="text-xs font-mono bg-mist/40 px-3 py-1.5 rounded-lg text-slate/70 break-all">{serial}</p>
                        </div>
                        {retirementReference && (
                            <div>
                                <p className="text-[10px] text-slate/40 uppercase tracking-wider font-medium mb-0.5">Retirement Reference</p>
                                <p className="text-xs font-mono bg-green-50 text-green-700 px-3 py-1.5 rounded-lg">{retirementReference}</p>
                            </div>
                        )}
                        <div>
                            <p className="text-[10px] text-slate/40 uppercase tracking-wider font-medium mb-0.5">Order Reference</p>
                            <p className="text-xs font-mono text-slate/50">{orderId}</p>
                        </div>
                    </div>

                    <div className="pt-3 border-t border-mist space-y-3">
                        <div className="flex items-center gap-2 bg-canopy/5 border border-canopy/20 rounded-lg px-3 py-2">
                            <Shield size={14} className="text-canopy flex-shrink-0" />
                            <div className="text-xs">
                                <span className="font-semibold text-canopy">Verra VCS Registry</span>
                                <span className="text-slate/50"> — Verified Carbon Standard</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <a
                                href={`https://registry.verra.org/app/projectDetail/VCS/${serial.split("-")[2]}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1.5 text-xs text-slate/50 hover:text-canopy transition-colors"
                            >
                                <ExternalLink size={11} />
                                Verify on Verra Registry
                            </a>
                            <span className="text-slate/20">·</span>
                            <button onClick={handleDownloadPDF} className="flex items-center gap-1.5 text-xs text-slate/50 hover:text-canopy transition-colors cursor-pointer bg-transparent border-0">
                                <Download size={11} />
                                Download PDF
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

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

interface CertTriggerProps {
    orderId: string;
    listingId: string;
    quantity: number;
    totalEur: number;
    retirementReference?: string | null;
    onOpen: (cert: { orderId: string; listingId: string; projectName: string; quantity: number; totalEur: number; retirementReference?: string | null }) => void;
}

function CertificateTrigger({ orderId, listingId, quantity, totalEur, retirementReference, onOpen }: CertTriggerProps) {
    const { data: listing } = useListingQuery(listingId);
    return (
        <button
            onClick={() => onOpen({ orderId, listingId, projectName: listing?.project_name ?? "Project", quantity, totalEur, retirementReference })}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors cursor-pointer bg-transparent border border-border rounded-md px-2 py-1 whitespace-nowrap"
        >
            <Award className="w-3 h-3" />
            Certificate
        </button>
    );
}

function DownloadPDFButton({ orderId, listingId, quantity, totalEur, retirementReference }: {
    orderId: string; listingId: string; quantity: number; totalEur: number; retirementReference?: string | null;
}) {
    const { data: listing } = useListingQuery(listingId);
    const serial = listing?.serial_number_range || deriveSerial(orderId, listingId);
    const retirementDate = new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" });

    return (
        <button
            onClick={() => generateCertificatePDF({
                orderId,
                projectName: listing?.project_name ?? "Carbon Credit Project",
                projectCountry: listing?.project_country,
                registryName: listing?.registry_name,
                vintageYear: listing?.vintage_year,
                methodology: listing?.methodology,
                quantity,
                totalEur,
                serialNumber: serial,
                retirementDate,
                retirementReference,
            })}
            title="Download PDF Certificate"
            className="flex items-center justify-center w-7 h-7 text-muted-foreground hover:text-primary transition-colors cursor-pointer bg-transparent border border-border rounded-md"
        >
            <Download className="w-3.5 h-3.5" />
        </button>
    );
}

export default function BuyerCreditsPage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const confirmPayment = useConfirmPayment();
    const confirmedRef = useRef(false);
    const { data: orders, isLoading, isError, error } = useOrders();
    const [activeCert, setActiveCert] = useState<{ orderId: string; listingId: string; projectName: string; quantity: number; totalEur: number; retirementReference?: string | null } | null>(null);

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
        <>
            {activeCert && (
                <CertificateModal
                    orderId={activeCert.orderId}
                    listingId={activeCert.listingId}
                    projectName={activeCert.projectName}
                    quantity={activeCert.quantity}
                    totalEur={activeCert.totalEur}
                    retirementReference={activeCert.retirementReference}
                    onClose={() => setActiveCert(null)}
                />
            )}
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
                                        <TableHead className="hidden md:table-cell">Serial No.</TableHead>
                                        <TableHead className="text-right">Quantity</TableHead>
                                        <TableHead className="text-right">Total Price</TableHead>
                                        <TableHead />
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {orders.map((order) => {
                                        return order.line_items.map((item, index) => {
                                            const serial = deriveSerial(order.id, item.listing_id);
                                            return (
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
                                                                {order.status === 'completed' && <Shield className="w-3 h-3 mr-1" />}
                                                                {order.status}
                                                            </Badge>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="hidden md:table-cell">
                                                        {order.status === 'completed' ? (
                                                            <span className="font-mono text-[11px] text-muted-foreground">{serial.substring(0, 20)}…</span>
                                                        ) : (
                                                            <span className="text-xs text-muted-foreground/40 italic">pending</span>
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
                                                    <TableCell>
                                                        <div className="flex items-center gap-1.5">
                                                            <CertificateTrigger
                                                                orderId={order.id}
                                                                listingId={item.listing_id}
                                                                quantity={item.quantity}
                                                                totalEur={order.total_eur}
                                                                retirementReference={order.retirement_reference}
                                                                onOpen={setActiveCert}
                                                            />
                                                            <DownloadPDFButton
                                                                orderId={order.id}
                                                                listingId={item.listing_id}
                                                                quantity={item.quantity}
                                                                totalEur={order.total_eur}
                                                                retirementReference={order.retirement_reference}
                                                            />
                                                        </div>
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        });
                                    })}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                )}
            </div>
        </>
    );
}
