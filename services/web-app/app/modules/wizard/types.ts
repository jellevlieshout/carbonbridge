export type WizardStep =
  | "profile_check"
  | "onboarding"
  | "footprint_estimate"
  | "preference_elicitation"
  | "listing_search"
  | "recommendation"
  | "order_creation"
  | "autobuy_waitlist";

export interface ConversationMessage {
  role: string;
  content: string;
  timestamp?: string;
}

export interface ExtractedPreferences {
  project_types: string[];
  regions: string[];
  max_price_eur: number | null;
  co_benefits: string[];
}

export interface WizardSessionData {
  buyer_id: string;
  current_step: WizardStep;
  conversation_history: ConversationMessage[];
  extracted_preferences: ExtractedPreferences | null;
  last_active_at: string | null;
  expires_at: string | null;
}

export interface WizardSession {
  id: string;
  data: WizardSessionData;
}

// SSE event types
export interface SSETokenEvent {
  type: "token";
  content: string;
}

export interface SSEStepChangeEvent {
  type: "step_change";
  step: WizardStep;
}

export interface SSEDoneEvent {
  type: "done";
  full_response: string;
}

export interface SSEErrorEvent {
  type: "error";
  message: string;
}

export interface SSEBuyerHandoffEvent {
  type: "buyer_handoff";
  outcome: "purchased" | "proposed_for_approval" | "skipped" | "failed";
  message: string;
}

export interface SSEAutobuywaitlistEvent {
  type: "autobuy_waitlist";
  opted_in: boolean;
}

export interface SSESuggestionsEvent {
  type: "suggestions";
  suggestions: string[];
}

export interface SSECheckoutReadyEvent {
  type: "checkout_ready";
  order_id: string;
  total_eur: number;
  project_name: string;
}

export type SSEEvent =
  | SSETokenEvent
  | SSEStepChangeEvent
  | SSEDoneEvent
  | SSEErrorEvent
  | SSEBuyerHandoffEvent
  | SSEAutobuywaitlistEvent
  | SSESuggestionsEvent
  | SSECheckoutReadyEvent;

// Visual step mapping — collapses 7 backend steps into 5 visual dots
export const STEP_ORDER: WizardStep[] = [
  "profile_check",
  "footprint_estimate",
  "preference_elicitation",
  "recommendation",
  "order_creation",
];

export const STEP_LABELS: Record<WizardStep, string> = {
  profile_check: "Profile Setup",
  onboarding: "Profile Setup",
  footprint_estimate: "Footprint Estimate",
  preference_elicitation: "Preferences",
  listing_search: "Recommendations",
  recommendation: "Recommendations",
  order_creation: "Purchase",
  autobuy_waitlist: "Monitoring",
};

/** Maps any backend step to its visual dot index (0-4) */
export function stepToVisualIndex(step: WizardStep): number {
  const collapsed: Record<WizardStep, WizardStep> = {
    profile_check: "profile_check",
    onboarding: "profile_check",
    footprint_estimate: "footprint_estimate",
    preference_elicitation: "preference_elicitation",
    listing_search: "recommendation",
    recommendation: "recommendation",
    order_creation: "order_creation",
    autobuy_waitlist: "order_creation",
  };
  return STEP_ORDER.indexOf(collapsed[step]);
}
