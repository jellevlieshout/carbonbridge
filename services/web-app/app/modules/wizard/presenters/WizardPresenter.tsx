import React, { useState, useCallback, useEffect, useRef } from "react";
import { LoaderCircle, AlertTriangle, Sparkles, ArrowRight, Bot } from "lucide-react";
import type { ConversationMessage, WizardStep } from "../types";
import { useWizardSession } from "../hooks/useWizardSession";
import { useWizardSendMessage } from "../hooks/useWizardSendMessage";
import { useWizardSSE } from "../hooks/useWizardSSE";
import { useWizardNavigation } from "../hooks/useWizardNavigation";
import { WizardView } from "../views/WizardView";
import { post } from "@clients/api/client";

const NUDGE_DELAY_MS = 38_000; // 38s of silence → proactive agent follow-up

interface WizardPresenterProps {
  onComplete?: () => void;
}

export function WizardPresenter({ onComplete }: WizardPresenterProps = {}) {
  const { data: session, isLoading, isError, error } = useWizardSession();
  const sendMessageMutation = useWizardSendMessage();

  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [currentStep, setCurrentStep] = useState<WizardStep>("profile_check");
  const [isComplete, setIsComplete] = useState(false);
  const [completionType, setCompletionType] = useState<"handoff" | "waitlist" | null>(null);

  const autoStarted = useRef(false);
  const [sessionSynced, setSessionSynced] = useState(false);
  const nudgeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isCompleteRef = useRef(false);

  if (session && !sessionSynced) {
    setMessages(session.data.conversation_history ?? []);
    setCurrentStep(session.data.current_step ?? "profile_check");
    setSessionSynced(true);
  }

  const { currentIndex, totalSteps, label } = useWizardNavigation(currentStep);

  // Keep a stable ref to startStream so we can use it in nudge timer
  const startStreamRef = useRef<((sessionId: string) => Promise<void>) | null>(null);

  const clearNudge = useCallback(() => {
    if (nudgeTimerRef.current) {
      clearTimeout(nudgeTimerRef.current);
      nudgeTimerRef.current = null;
    }
  }, []);

  const scheduleNudge = useCallback(
    (sessionId: string) => {
      clearNudge();
      if (isCompleteRef.current) return;
      nudgeTimerRef.current = setTimeout(async () => {
        if (isCompleteRef.current) return;
        try {
          await post(`/wizard/session/${sessionId}/nudge`, {});
          startStreamRef.current?.(sessionId);
        } catch {
          // ignore nudge errors
        }
      }, NUDGE_DELAY_MS);
    },
    [clearNudge],
  );

  const handleDone = useCallback(
    (fullResponse: string) => {
      setMessages((prev) => [...prev, { role: "assistant", content: fullResponse }]);
      setStreamingText("");
      if (session && !isCompleteRef.current) {
        scheduleNudge(session.id);
      }
    },
    [session, scheduleNudge],
  );

  const handleError = useCallback((message: string) => {
    setMessages((prev) => [...prev, { role: "assistant", content: `⚠️ ${message}` }]);
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
    onBuyerHandoff: useCallback(
      (_outcome: string, _message: string) => {
        clearNudge();
        isCompleteRef.current = true;
        setIsComplete(true);
        setCompletionType("handoff");
      },
      [clearNudge],
    ),
    onAutobuyWaitlist: useCallback(
      (_optedIn: boolean) => {
        clearNudge();
        isCompleteRef.current = true;
        setIsComplete(true);
        setCompletionType("waitlist");
      },
      [clearNudge],
    ),
  });

  // Keep ref up-to-date
  useEffect(() => {
    startStreamRef.current = startStream;
  }, [startStream]);

  // Auto-start: when session loads with no messages, agent goes first
  useEffect(() => {
    if (!session || autoStarted.current || !sessionSynced) return;
    autoStarted.current = true;
    const history = session.data.conversation_history ?? [];
    if (history.length === 0) {
      startStream(session.id);
    } else {
      // Existing session with messages — schedule nudge in case user is idle
      scheduleNudge(session.id);
    }
  }, [session, sessionSynced, startStream, scheduleNudge]);

  const handleSend = useCallback(
    (text: string) => {
      if (!session) return;
      clearNudge();
      setMessages((prev) => [...prev, { role: "user", content: text }]);
      setStreamingText("");

      sendMessageMutation.mutate(
        { sessionId: session.id, content: text },
        {
          onSuccess: () => startStream(session.id),
          onError: (err) => {
            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: `Failed to send message: ${err instanceof Error ? err.message : "Unknown error"}`,
              },
            ]);
          },
        },
      );
    },
    [session, sendMessageMutation, startStream, clearNudge],
  );

  useEffect(() => () => clearNudge(), [clearNudge]);

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

  if (isComplete) {
    return <WizardCompletionScreen type={completionType} onContinue={() => onComplete?.()} />;
  }

  return (
    <>
      <WizardView
        messages={messages}
        streamingText={streamingText}
        isStreaming={isStreaming}
        currentIndex={currentIndex}
        totalSteps={totalSteps}
        stepLabel={label}
        onSend={handleSend}
      />
      {onComplete && (
        <div className="flex justify-center mt-3">
          <button
            onClick={onComplete}
            className="text-sm text-slate/30 hover:text-slate/50 transition-colors cursor-pointer bg-transparent border-0 underline underline-offset-2"
          >
            Skip for now
          </button>
        </div>
      )}
    </>
  );
}

// ── Completion/handoff screen ──────────────────────────────────────────────

interface WizardCompletionScreenProps {
  type: "handoff" | "waitlist" | null;
  onContinue: () => void;
}

function WizardCompletionScreen({ type, onContinue }: WizardCompletionScreenProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-16 text-center">
      <div className="w-16 h-16 rounded-full bg-canopy/10 flex items-center justify-center">
        {type === "handoff" ? (
          <Bot size={28} className="text-canopy" />
        ) : (
          <Sparkles size={28} className="text-canopy" />
        )}
      </div>

      <div className="space-y-2">
        <h2 className="font-serif italic text-2xl text-slate">
          {type === "handoff"
            ? "Your AI agent is on it"
            : type === "waitlist"
              ? "Monitoring the market for you"
              : "You're all set!"}
        </h2>
        <p className="text-sm text-slate/50 max-w-xs mx-auto leading-relaxed">
          {type === "handoff"
            ? "Your autonomous buyer agent is searching for the best carbon credits that match your profile."
            : type === "waitlist"
              ? "We'll automatically purchase matching credits as soon as they become available on the market."
              : "Your carbon profile is saved. Head to your dashboard to explore the marketplace."}
        </p>
      </div>

      <button
        onClick={onContinue}
        className="flex items-center gap-2 px-6 py-3 rounded-full text-sm font-semibold bg-canopy text-linen hover:bg-canopy/90 transition-colors cursor-pointer border-0"
      >
        Enter CarbonBridge
        <ArrowRight size={16} />
      </button>
    </div>
  );
}
