import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { agentRunsList, agentRunGet, agentTrigger, agentRunApprove, agentRunReject } from "@clients/api/agent";

export const useAgentRuns = () => {
    return useQuery({
        queryKey: ["agent-runs"],
        queryFn: () => agentRunsList(),
        refetchInterval: 5000,
    });
};

export const useAgentRunDetail = (runId: string | null) => {
    return useQuery({
        queryKey: ["agent-run", runId],
        queryFn: () => agentRunGet(runId!),
        enabled: !!runId,
        refetchInterval: (query) => {
            const status = query.state.data?.status;
            return status === "running" ? 2000 : false;
        },
    });
};

export const useAgentTrigger = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: () => agentTrigger(),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["agent-runs"] });
        },
    });
};

export const useAgentApprove = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (runId: string) => agentRunApprove(runId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["agent-runs"] });
            queryClient.invalidateQueries({ queryKey: ["agent-run"] });
        },
    });
};

export const useAgentReject = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (runId: string) => agentRunReject(runId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["agent-runs"] });
            queryClient.invalidateQueries({ queryKey: ["agent-run"] });
        },
    });
};
