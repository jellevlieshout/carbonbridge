import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { listingGetById } from "@clients/api/listings";

export const useListingQuery = (id: string) => {
    return useQuery({
        queryKey: ["listing", id],
        queryFn: () => listingGetById(id),
        enabled: !!id
    });
};

export const useListing = (id: string) => {
    return useSuspenseQuery({
        queryKey: ["listing", id],
        queryFn: () => listingGetById(id)
    });
};
