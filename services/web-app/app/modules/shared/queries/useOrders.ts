import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { ordersGetMine } from "@clients/api/orders";

export const useOrdersQuery = () => {
    return useQuery({
        queryKey: ["orders", "me"],
        queryFn: () => ordersGetMine()
    });
};

export const useOrders = () => {
    return useSuspenseQuery({
        queryKey: ["orders", "me"],
        queryFn: () => ordersGetMine()
    });
};
