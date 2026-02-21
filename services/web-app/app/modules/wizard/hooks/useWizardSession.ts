import { useQuery } from "@tanstack/react-query";
import { post } from "@clients/api/client";
import type { WizardSession } from "../types";

export const useWizardSession = () => {
  return useQuery<WizardSession>({
    queryKey: ["wizard-session"],
    queryFn: () => post("/wizard/session"),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
};
