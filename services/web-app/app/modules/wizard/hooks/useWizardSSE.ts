import { useCallback, useEffect, useRef, useState } from "react";
import { refreshToken } from "@clients/api/client";
import type { WizardStep, SSEEvent } from "../types";

interface UseWizardSSEOptions {
  onToken: (token: string) => void;
  onStepChange: (step: WizardStep) => void;
  onDone: (fullResponse: string) => void;
  onError: (message: string) => void;
  onBuyerHandoff?: (outcome: string, message: string) => void;
  onAutobuyWaitlist?: (optedIn: boolean) => void;
  onSuggestions?: (suggestions: string[]) => void;
}

async function fetchSSE(url: string, signal: AbortSignal): Promise<Response> {
  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "text/event-stream",
      "token-handler-version": "1",
    },
    signal,
  });

  if (response.status === 401) {
    try {
      await refreshToken();
    } catch {
      window.location.href = '/';
      throw new Error("Session expired");
    }
    const retry = await fetch(url, {
      method: "GET",
      credentials: "include",
      headers: {
        Accept: "text/event-stream",
        "token-handler-version": "1",
      },
      signal,
    });
    if (retry.status === 401) {
      window.location.href = '/';
      throw new Error("Session expired");
    }
    if (!retry.ok) {
      throw new Error(`Stream request failed: ${retry.status}`);
    }
    return retry;
  }

  if (!response.ok) {
    throw new Error(`Stream request failed: ${response.status}`);
  }
  return response;
}

export const useWizardSSE = ({
  onToken,
  onStepChange,
  onDone,
  onError,
  onBuyerHandoff,
  onAutobuyWaitlist,
  onSuggestions,
}: UseWizardSSEOptions) => {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
  }, []);

  const startStream = useCallback(
    async (sessionId: string) => {
      stopStream();

      const controller = new AbortController();
      abortRef.current = controller;
      setIsStreaming(true);

      try {
        const url = `${window.location.origin}/api/wizard/session/${sessionId}/stream`;
        const response = await fetchSSE(url, controller.signal);

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No readable stream");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const jsonStr = line.slice(6).trim();
            if (!jsonStr || jsonStr === "[DONE]") continue;

            try {
              const event: SSEEvent = JSON.parse(jsonStr);
              switch (event.type) {
                case "token":
                  onToken(event.content);
                  break;
                case "step_change":
                  onStepChange(event.step);
                  break;
                case "done":
                  onDone(event.full_response);
                  break;
                case "error":
                  onError(event.message);
                  break;
                case "buyer_handoff":
                  onBuyerHandoff?.(event.outcome, event.message);
                  break;
                case "autobuy_waitlist":
                  onAutobuyWaitlist?.(event.opted_in);
                  break;
                case "suggestions":
                  onSuggestions?.(event.suggestions);
                  break;
              }
            } catch {
              // skip malformed JSON
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        onError(err instanceof Error ? err.message : "Stream failed");
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [onToken, onStepChange, onDone, onError, onBuyerHandoff, onAutobuyWaitlist, onSuggestions, stopStream],
  );

  useEffect(() => {
    return () => stopStream();
  }, [stopStream]);

  return { isStreaming, startStream, stopStream };
};
