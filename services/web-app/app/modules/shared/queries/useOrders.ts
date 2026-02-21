import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ordersGetMine, orderCreate, orderCancel } from "@clients/api/orders";
import type { CreateOrderRequest } from "@clients/api/orders";

export const useOrdersQuery = () => {
    return useQuery({
        queryKey: ["orders", "me"],
        queryFn: () => ordersGetMine()
    });
};

export const useOrders = () => {
    return useQuery({
        queryKey: ["orders", "me"],
        queryFn: () => ordersGetMine()
    });
};

export const useCreateOrder = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (req: CreateOrderRequest) => orderCreate(req),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["orders", "me"] });
            queryClient.invalidateQueries({ queryKey: ["listings"] });
        },
    });
};

export const useCancelOrder = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (orderId: string) => orderCancel(orderId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["orders", "me"] });
            queryClient.invalidateQueries({ queryKey: ["listings"] });
        },
    });
};
