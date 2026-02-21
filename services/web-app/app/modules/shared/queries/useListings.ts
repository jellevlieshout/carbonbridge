import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { listingsGet } from "@clients/api/listings";

export const useListingsQuery = () => {
    return useQuery({
        queryKey: ["listings"],
        queryFn: () => listingsGet()
    });
};

export const useListings = () => {
    return useSuspenseQuery({
        queryKey: ["listings"],
        queryFn: () => listingsGet()
    });
};
