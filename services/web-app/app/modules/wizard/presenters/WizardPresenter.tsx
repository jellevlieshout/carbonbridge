import React, { useState, useCallback } from "react";
import { LoaderCircle, AlertTriangle } from "lucide-react";
import type { ConversationMessage, WizardStep } from "../types";
import { useWizardSession } from "../hooks/useWizardSession";
import { useWizardSendMessage } from "../hooks/useWizardSendMessage";
import { useWizardSSE } from "../hooks/useWizardSSE";
import { useWizardNavigation } from "../hooks/useWizardNavigation";
import { WizardView } from "../views/WizardView";

export function WizardPresenter() {
  const { data: session, isLoading, isError, error } = useWizardSession();
  const sendMessageMutation = useWizardSendMessage();

  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [currentStep, setCurrentStep] = useState<WizardStep>("profile_check");

  // Sync session data into local state when it arrives
  const [sessionSynced, setSessionSynced] = useState(false);
  if (session && !sessionSynced) {
    setMessages(session.data.conversation_history ?? []);
    setCurrentStep(session.data.current_step ?? "profile_check");
    setSessionSynced(true);
  }

  const { currentIndex, totalSteps, label } = useWizardNavigation(currentStep);

  const handleDone = useCallback((fullResponse: string) => {
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: fullResponse },
    ]);
    setStreamingText("");
  }, []);

  const handleError = useCallback((message: string) => {
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: `Error: ${message}` },
    ]);
    setStreamingText("");
  }, []);

  const { isStreaming, startStream } = useWizardSSE({
    onToken: useCallback((token: string) => {
      setStreamingText((prev) => prev + token);
    }, []),
    onStepChange: useCallback((step: WizardStep) => {
      setCurrentStep(step);
    }, []),
    onDone: handleDone,
    onError: handleError,
  });

  const handleSend = useCallback(
    (text: string) => {
      if (!session) return;

      // Optimistically add user message
      const userMsg: ConversationMessage = { role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setStreamingText("");

      // Send to backend and start streaming
      sendMessageMutation.mutate(
        { sessionId: session.id, content: text },
        {
          onSuccess: () => {
            startStream(session.id);
          },
          onError: (err) => {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content: `Failed to send message: ${err instanceof Error ? err.message : "Unknown error"}` },
            ]);
          },
        },
      );
    },
    [session, sendMessageMutation, startStream],
  );

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 min-h-[50vh]">
        <LoaderCircle className="animate-spin text-canopy w-10 h-10" />
        <p className="text-sm text-slate/60">Starting wizard session...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 min-h-[50vh]">
        <AlertTriangle className="text-ember w-10 h-10" />
        <p className="text-sm text-slate/60">
          {error?.message === "Not Found"
            ? "Wizard backend is not available yet. Please ensure the API is running."
            : `Failed to start session: ${error?.message ?? "Unknown error"}`}
        </p>
      </div>
    );
  }

  return (
    <WizardView
      messages={messages}
      streamingText={streamingText}
      isStreaming={isStreaming}
      currentIndex={currentIndex}
      totalSteps={totalSteps}
      stepLabel={label}
      onSend={handleSend}
    />
  );
}
