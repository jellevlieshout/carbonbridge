import { useMutation, useQueryClient } from "@tanstack/react-query";
import { post } from "@clients/api/client";

export const useWizardSendMessage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, content }: { sessionId: string; content: string }) =>
      post(`/wizard/session/${sessionId}/message`, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wizard-session"] });
    },
  });
};
