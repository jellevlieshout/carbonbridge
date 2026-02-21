import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { userDataGet } from "@clients/api/user";

export const useUserResourcesQuery = () => {
    return useQuery({
        queryKey: ["userResources"],
        queryFn: () => userDataGet()
    });
};

export const useUserResources = () => {
    return useSuspenseQuery({
        queryKey: ["userResources"],
        queryFn: () => userDataGet()
    });
};
