import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    auctionsSearch,
    auctionGetById,
    auctionGetBids,
    auctionCreate,
    auctionPlaceBid,
    auctionBuyNow,
    auctionCancel,
    auctionsGetMine,
    type CreateAuctionRequest,
} from "@clients/api/auctions";

/** Active auctions for marketplace (refreshes every 10s) */
export const useAuctions = () => {
    return useQuery({
        queryKey: ["auctions"],
        queryFn: () => auctionsSearch({ status: "active" }),
        refetchInterval: 10_000,
    });
};

/** Single auction detail (3s polling when active) */
export const useAuction = (auctionId: string | null) => {
    return useQuery({
        queryKey: ["auction", auctionId],
        queryFn: () => auctionGetById(auctionId!),
        enabled: !!auctionId,
        refetchInterval: (query) => {
            const status = query.state.data?.status;
            return status === "active" || status === "scheduled" ? 3000 : false;
        },
    });
};

/** Bid history for an auction (3s polling) */
export const useAuctionBids = (auctionId: string | null) => {
    return useQuery({
        queryKey: ["auction-bids", auctionId],
        queryFn: () => auctionGetBids(auctionId!),
        enabled: !!auctionId,
        refetchInterval: 3000,
    });
};

/** Seller's own auctions (refreshes every 10s) */
export const useMyAuctions = () => {
    return useQuery({
        queryKey: ["auctions", "mine"],
        queryFn: () => auctionsGetMine(),
        refetchInterval: 10_000,
    });
};

/** Create auction mutation */
export const useCreateAuction = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data: CreateAuctionRequest) => auctionCreate(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["auctions"] });
            queryClient.invalidateQueries({ queryKey: ["listings"] });
            queryClient.invalidateQueries({ queryKey: ["listings", "mine"] });
        },
    });
};

/** Place bid mutation */
export const usePlaceBid = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ auctionId, amount }: { auctionId: string; amount: number }) =>
            auctionPlaceBid(auctionId, { amount_per_tonne_eur: amount }),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["auction", variables.auctionId] });
            queryClient.invalidateQueries({ queryKey: ["auction-bids", variables.auctionId] });
            queryClient.invalidateQueries({ queryKey: ["auctions"] });
        },
    });
};

/** Buy-now mutation */
export const useBuyNow = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (auctionId: string) => auctionBuyNow(auctionId),
        onSuccess: (_, auctionId) => {
            queryClient.invalidateQueries({ queryKey: ["auction", auctionId] });
            queryClient.invalidateQueries({ queryKey: ["auction-bids", auctionId] });
            queryClient.invalidateQueries({ queryKey: ["auctions"] });
        },
    });
};

/** Cancel auction mutation */
export const useCancelAuction = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (auctionId: string) => auctionCancel(auctionId),
        onSuccess: (_, auctionId) => {
            queryClient.invalidateQueries({ queryKey: ["auction", auctionId] });
            queryClient.invalidateQueries({ queryKey: ["auctions"] });
            queryClient.invalidateQueries({ queryKey: ["listings"] });
        },
    });
};
