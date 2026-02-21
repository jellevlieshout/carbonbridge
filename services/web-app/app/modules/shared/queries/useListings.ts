import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listingsGet, listingCreate, type ListingCreateRequest } from "@clients/api/listings";

export const useListingsQuery = () => {
    return useQuery({
        queryKey: ["listings"],
        queryFn: () => listingsGet()
    });
};

export const useListings = () => {
    return useQuery({
        queryKey: ["listings"],
        queryFn: () => listingsGet()
    });
};

export const useCreateListing = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data: ListingCreateRequest) => listingCreate(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["listings"] });
            queryClient.invalidateQueries({ queryKey: ["listings", "mine"] });
        },
    });
};
