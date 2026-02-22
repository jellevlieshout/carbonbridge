import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { agentRunsList, agentRunGet, agentTrigger, agentTriggerAdvisory, agentRunApprove, agentRunReject } from "@clients/api/agent";

export const useAgentRuns = (agentType?: string) => {
    return useQuery({
        queryKey: ["agent-runs", agentType],
        queryFn: () => agentRunsList(agentType),
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
            return status === "running" || status === "awaiting_approval" ? 2000 : false;
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

export const useSellerAdvisoryTrigger = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: () => agentTriggerAdvisory(),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["agent-runs"] });
        },
    });
};
