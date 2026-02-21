import { useQuery } from "@tanstack/react-query";
import { listingsGet } from "@clients/api/listings";

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
