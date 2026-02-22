import React, { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import { loadStripe } from "@stripe/stripe-js";
import { Elements } from "@stripe/react-stripe-js";
import { LoaderCircle, AlertTriangle, Sparkles, ArrowRight, Bot, ShoppingCart, CheckCircle2, Shield, Award, Download, ExternalLink } from "lucide-react";
import type { ConversationMessage, WizardStep } from "../types";
import { useWizardSession } from "../hooks/useWizardSession";
import { useWizardSendMessage } from "../hooks/useWizardSendMessage";
import { useWizardSSE } from "../hooks/useWizardSSE";
import { useWizardNavigation } from "../hooks/useWizardNavigation";
import { useMockConfirmOrder } from "~/modules/shared/queries/useOrders";
import { CheckoutForm } from "~/components/buyer/CheckoutForm";
import { WizardView } from "../views/WizardView";

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLIC_KEY || "");

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
  const [completionType, setCompletionType] = useState<"handoff" | "waitlist" | "checkout" | null>(null);
  const [awaitingWaitlistAgreement, setAwaitingWaitlistAgreement] = useState(false);
  const [checkoutOrderId, setCheckoutOrderId] = useState<string | null>(null);
  const [checkoutTotalEur, setCheckoutTotalEur] = useState<number>(0);
  const [checkoutProjectName, setCheckoutProjectName] = useState<string>("");
  const [checkoutClientSecret, setCheckoutClientSecret] = useState<string>("");
  const [suggestions, setSuggestions] = useState<string[]>([]);

  const autoStarted = useRef(false);
  const [sessionSynced, setSessionSynced] = useState(false);
  const isCompleteRef = useRef(false);

  if (session && !sessionSynced) {
    setMessages(session.data.conversation_history ?? []);
    setCurrentStep(session.data.current_step ?? "profile_check");
    setSessionSynced(true);
  }

  const { currentIndex, totalSteps, label } = useWizardNavigation(currentStep);

  const startStreamRef = useRef<((sessionId: string) => Promise<void>) | null>(null);

  const handleDone = useCallback((fullResponse: string) => {
    setMessages((prev) => [...prev, { role: "assistant", content: fullResponse }]);
    setStreamingText("");
  }, []);

  const handleError = useCallback((message: string) => {
    setMessages((prev) => [...prev, { role: "assistant", content: `⚠️ ${message}` }]);
    setStreamingText("");
    setSuggestions([]);
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
    onSuggestions: useCallback((newSuggestions: string[]) => {
      setSuggestions(newSuggestions);
    }, []),
    onBuyerHandoff: useCallback(
      (_outcome: string, _message: string) => {
        isCompleteRef.current = true;
        setIsComplete(true);
        setCompletionType("handoff");
        setSuggestions([]);
      },
      [],
    ),
    onAutobuyWaitlist: useCallback(
      (_optedIn: boolean) => {
        isCompleteRef.current = true;
        setCompletionType("waitlist");
        setSuggestions([]);
        setAwaitingWaitlistAgreement(true);
      },
      [],
    ),
    onCheckoutReady: useCallback(
      (orderId: string, totalEur: number, projectName: string, clientSecret: string) => {
        isCompleteRef.current = true;
        setCheckoutOrderId(orderId);
        setCheckoutTotalEur(totalEur);
        setCheckoutProjectName(projectName);
        setCheckoutClientSecret(clientSecret);
        setCompletionType("checkout");
        setIsComplete(true);
        setSuggestions([]);
      },
      [],
    ),
  });

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
    }
  }, [session, sessionSynced, startStream]);

  const handleSend = useCallback(
    (text: string) => {
      if (!session) return;
      setSuggestions([]);
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

  if (isComplete) {
    return (
      <WizardCompletionScreen
        type={completionType}
        checkoutOrderId={checkoutOrderId}
        checkoutTotalEur={checkoutTotalEur}
        checkoutProjectName={checkoutProjectName}
        checkoutClientSecret={checkoutClientSecret}
        onContinue={() => onComplete?.()}
      />
    );
  }

  return (
    <>
      <WizardView
        messages={messages}
        streamingText={streamingText}
        isStreaming={isStreaming}
        hideStreamingState={awaitingWaitlistAgreement}
        disableInput={awaitingWaitlistAgreement}
        currentIndex={currentIndex}
        totalSteps={totalSteps}
        stepLabel={label}
        suggestions={suggestions}
        onSend={handleSend}
      />
      {awaitingWaitlistAgreement && (
        <div className="mt-4 rounded-2xl border-2 border-canopy/30 bg-gradient-to-br from-canopy/8 to-canopy/4 p-6 text-center shadow-lg animate-in fade-in slide-in-from-bottom-3 duration-400">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-canopy/15 flex items-center justify-center">
              <Sparkles size={22} className="text-canopy" />
            </div>
            <div className="space-y-1">
              <p className="text-base font-semibold text-slate">Autonomous agent ready</p>
              <p className="text-sm text-slate/60 max-w-xs mx-auto">
                Your agent will monitor the market and buy matching credits automatically. Cancel any time from your dashboard.
              </p>
            </div>
            <button
              onClick={() => {
                setAwaitingWaitlistAgreement(false);
                setIsComplete(true);
              }}
              className="w-full max-w-xs inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full text-sm font-semibold bg-canopy text-linen hover:bg-canopy/90 active:scale-95 transition-all cursor-pointer border-0 shadow-md"
            >
              Enter CarbonBridge
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}
      {onComplete && (
        <div className="flex justify-center mt-3">
          <button
            onClick={onComplete}
            disabled={awaitingWaitlistAgreement}
            className="text-sm text-slate/30 hover:text-slate/50 transition-colors cursor-pointer bg-transparent border-0 underline underline-offset-2 disabled:opacity-40 disabled:cursor-not-allowed"
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
  type: "handoff" | "waitlist" | "checkout" | null;
  checkoutOrderId?: string | null;
  checkoutTotalEur?: number;
  checkoutProjectName?: string;
  checkoutClientSecret?: string;
  onContinue: () => void;
}

const RETIREMENT_STAGES = [
  { label: "Initiating payment...", duration: 1200 },
  { label: "Verifying credit availability...", duration: 1400 },
  { label: "Securing credits on registry...", duration: 1600 },
  { label: "Awaiting retirement confirmation...", duration: 1800 },
  { label: "Issuing certificate...", duration: 1000 },
];

function generateSerialNumber(projectName: string): string {
  const prefix = "VCS-VCU";
  const projectCode = Math.floor(100 + Math.random() * 900);
  const year = new Date().getFullYear();
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789";
  const suffix = Array.from({ length: 8 }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
  return `${prefix}-${projectCode}-VER-${year}-${suffix}`;
}

function WizardCompletionScreen({
  type,
  checkoutOrderId,
  checkoutTotalEur,
  checkoutProjectName,
  checkoutClientSecret,
  onContinue,
}: WizardCompletionScreenProps) {
  const navigate = useNavigate();
  const mockConfirm = useMockConfirmOrder();
  const [paymentDone, setPaymentDone] = useState(false);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [retirementStageIdx, setRetirementStageIdx] = useState(0);
  const [serialNumber] = useState(() => generateSerialNumber(checkoutProjectName || "project"));
  const retirementDate = new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" });

  const isMockMode = !checkoutClientSecret || checkoutClientSecret.startsWith("mock_secret_");

  if (type === "checkout" && checkoutOrderId) {
    const handleSimulatePayment = () => {
      setPaymentLoading(true);
      setRetirementStageIdx(0);

      let stageIndex = 0;
      const advanceStage = () => {
        stageIndex += 1;
        if (stageIndex < RETIREMENT_STAGES.length) {
          setRetirementStageIdx(stageIndex);
          setTimeout(advanceStage, RETIREMENT_STAGES[stageIndex].duration);
        }
      };
      setTimeout(advanceStage, RETIREMENT_STAGES[0].duration);

      const totalDuration = RETIREMENT_STAGES.reduce((sum, s) => sum + s.duration, 0);
      mockConfirm.mutate(checkoutOrderId, {
        onSuccess: () => {
          setTimeout(() => {
            setPaymentDone(true);
            setPaymentLoading(false);
          }, totalDuration);
        },
        onError: () => setPaymentLoading(false),
      });
    };

    const handleStripeSuccess = () => {
      setPaymentDone(true);
    };

    if (paymentLoading) {
      const stage = RETIREMENT_STAGES[retirementStageIdx];
      return (
        <div className="flex flex-col items-center justify-center gap-6 py-16 text-center">
          <div className="w-16 h-16 rounded-full bg-canopy/10 flex items-center justify-center">
            <LoaderCircle size={28} className="text-canopy animate-spin" />
          </div>
          <div className="space-y-3">
            <h2 className="font-serif italic text-2xl text-slate">Processing transaction</h2>
            <p className="text-sm text-canopy font-medium animate-pulse">{stage.label}</p>
            <div className="flex items-center justify-center gap-1.5 mt-2">
              {RETIREMENT_STAGES.map((_, i) => (
                <div
                  key={i}
                  className={`h-1 rounded-full transition-all duration-500 ${i <= retirementStageIdx ? "w-6 bg-canopy" : "w-3 bg-mist"}`}
                />
              ))}
            </div>
          </div>
          <p className="text-xs text-slate/30 max-w-xs">
            Do not close this window. We are coordinating with the registry to retire your credits.
          </p>
        </div>
      );
    }

    if (paymentDone) {
      return (
        <div className="flex flex-col items-center gap-6 py-8 text-center">
          <div className="w-16 h-16 rounded-full bg-canopy/10 flex items-center justify-center">
            <CheckCircle2 size={28} className="text-canopy" />
          </div>

          {/* Certificate card */}
          <div className="w-full max-w-sm border border-canopy/20 rounded-2xl overflow-hidden shadow-sm bg-white">
            <div className="bg-canopy px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2 text-linen">
                <Award size={18} />
                <span className="text-sm font-semibold tracking-wide uppercase">Certificate of Carbon Retirement</span>
              </div>
              <Shield size={16} className="text-linen/60" />
            </div>
            <div className="px-6 py-5 space-y-3 text-left">
              {checkoutProjectName && (
                <div>
                  <p className="text-[10px] text-slate/40 uppercase tracking-wider font-medium">Project</p>
                  <p className="text-sm font-semibold text-slate">{checkoutProjectName}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[10px] text-slate/40 uppercase tracking-wider font-medium">Quantity Retired</p>
                  <p className="text-sm font-bold text-canopy">{checkoutTotalEur ? `${Math.round(checkoutTotalEur / 15)} tCO₂e` : "—"}</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate/40 uppercase tracking-wider font-medium">Retirement Date</p>
                  <p className="text-sm font-semibold text-slate">{retirementDate}</p>
                </div>
              </div>
              <div>
                <p className="text-[10px] text-slate/40 uppercase tracking-wider font-medium">Serial Number</p>
                <p className="text-xs font-mono text-slate/70 break-all">{serialNumber}</p>
              </div>
              <div className="pt-2 border-t border-mist flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-canopy">
                  <Shield size={12} />
                  <span className="text-[10px] font-medium">Verra VCS Registry — Verified</span>
                </div>
                <a
                  href={`https://registry.verra.org/app/projectDetail/VCS/${serialNumber.split("-")[2]}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-slate/40 hover:text-canopy flex items-center gap-0.5 transition-colors"
                >
                  Verify <ExternalLink size={9} />
                </a>
              </div>
            </div>
          </div>

          <div className="flex flex-col items-center gap-2">
            <button
              onClick={() => navigate("/buyer/credits")}
              className="flex items-center gap-2 px-6 py-3 rounded-full text-sm font-semibold bg-canopy text-linen hover:bg-canopy/90 transition-colors cursor-pointer border-0"
            >
              View My Portfolio
              <ArrowRight size={16} />
            </button>
            <button
              onClick={() => navigate("/buyer/credits")}
              className="flex items-center gap-1.5 text-xs text-slate/40 hover:text-slate/60 transition-colors cursor-pointer bg-transparent border-0"
            >
              <Download size={11} />
              Download PDF certificate
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="flex flex-col items-center justify-center gap-6 py-16 text-center">
        <div className="w-16 h-16 rounded-full bg-canopy/10 flex items-center justify-center">
          <ShoppingCart size={28} className="text-canopy" />
        </div>
        <div className="space-y-2">
          <h2 className="font-serif italic text-2xl text-slate">Ready to purchase</h2>
          {checkoutProjectName && (
            <p className="text-base font-medium text-slate/80">{checkoutProjectName}</p>
          )}
          <p className="text-sm text-slate/50 max-w-xs mx-auto leading-relaxed">
            Total: <span className="font-semibold text-slate">€{checkoutTotalEur?.toFixed(2)}</span>
            <br />
            Confirm to complete your carbon offset purchase.
          </p>
        </div>
        {isMockMode ? (
          <div className="flex flex-col items-center gap-3">
            <button
              onClick={handleSimulatePayment}
              disabled={paymentLoading}
              className="flex items-center gap-2 px-6 py-3 rounded-full text-sm font-semibold bg-canopy text-linen hover:bg-canopy/90 transition-colors cursor-pointer border-0 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <CheckCircle2 size={16} />
              Confirm Purchase
            </button>
            <button
              onClick={() => navigate("/buyer/credits")}
              className="text-sm text-slate/40 hover:text-slate/60 transition-colors cursor-pointer bg-transparent border-0 underline underline-offset-2"
            >
              View My Orders instead
            </button>
          </div>
        ) : (
          <div className="w-full max-w-md mx-auto">
            <Elements stripe={stripePromise} options={{ clientSecret: checkoutClientSecret }}>
              <CheckoutForm clientSecret={checkoutClientSecret!} onSuccess={handleStripeSuccess} />
            </Elements>
          </div>
        )}
      </div>
    );
  }

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
