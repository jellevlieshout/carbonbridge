import { useQuery } from "@tanstack/react-query";
import { userDataGet } from "@clients/api/user";

export const useUserResourcesQuery = (options?: { enabled?: boolean }) => {
    return useQuery({
        queryKey: ["userResources"],
        queryFn: () => userDataGet(),
        enabled: options?.enabled,
    });
};

export const useUserResources = () => {
    return useQuery({
        queryKey: ["userResources"],
        queryFn: () => userDataGet()
    });
};
