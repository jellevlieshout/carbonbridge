Plan to implement                                                                                                │
│                                                                                                                  │
│ Buyer Wizard UI Implementation Plan                                                                              │
│                                                                                                                  │
│ Context                                                                                                          │
│                                                                                                                  │
│ The Buyer Wizard is the primary buyer experience in CarbonBridge (spec section 5.3). It's a conversational,      │
│ agent-assisted, multi-step flow where buyers are guided through carbon credit purchasing without needing carbon  │
│ market expertise. The wizard agent streams responses via SSE, and session state persists in Couchbase so         │
│ sessions survive browser closes.                                                                                 │
│                                                                                                                  │
│ Currently, authenticated users land on a placeholder "CarbonBridge" page. This plan implements the   │
│ full wizard UI and redirects authenticated buyers to it.                                                         │
│                                                                                                                  │
│ ---                                                                                                              │
│ Files to Modify (3)                                                                                              │
│                                                                                                                  │
│ File: services/web-app/app/routes.ts                                                                             │
│ Change: Add buyer/wizard route inside DashboardLayout                                                            │
│ ────────────────────────────────────────                                                                         │
│ File: services/web-app/app/modules/home/views/HomeView.tsx                                                       │
│ Change: Redirect authenticated users to /buyer/wizard via <Navigate>                                             │
│ ────────────────────────────────────────                                                                         │
│ File: services/web-app/app/components/layout/Sidebar.tsx                                                         │
│ Change: Add wizard nav entry                                                                                     │
│                                                                                                                  │
│ Files to Create (15)                                                                                             │
│                                                                                                                  │
│ All under services/web-app/app/modules/wizard/:                                                                  │
│                                                                                                                  │
│ modules/wizard/                                                                                                  │
│   types.ts                          # TypeScript types mirroring backend models                                  │
│   hooks/                                                                                                         │
│     useWizardSession.ts             # TanStack query: create/fetch session                                       │
│     useWizardSendMessage.ts         # TanStack mutation: send user message                                       │
│     useWizardSSE.ts                 # SSE streaming hook for agent responses                                     │
│     useWizardNavigation.ts          # Step index/progress computation                                            │
│   components/                                                                                                    │
│     WizardCard.tsx                  # Main card container with step header                                       │
│     WizardProgressDots.tsx          # Horizontal dot progress indicator                                          │
│     AgentMessage.tsx                # Agent chat bubble with streaming cursor                                    │
│     UserMessage.tsx                 # User chat bubble (right-aligned)                                           │
│     ChatInput.tsx                   # Message input bar with send button                                         │
│     ListingRecommendationCard.tsx   # Recommendation card for step 3                                             │
│   views/                                                                                                         │
│     WizardView.tsx                  # Pure layout composing all components                                       │
│   presenters/                                                                                                    │
│     WizardPresenter.tsx             # Data-fetching orchestrator wiring hooks                                    │
│                                                                                                                  │
│ Plus the route entry: services/web-app/app/routes/wizard.tsx                                                     │
│                                                                                                                  │
│ ---                                                                                                              │
│ Implementation Details                                                                                           │
│                                                                                                                  │
│ 1. Types (modules/wizard/types.ts)                                                                               │
│                                                                                                                  │
│ Define types mirroring backend models from models/python/models/entities/couchbase/wizard_sessions.py:           │
│ - WizardStep union: "profile_check" | "onboarding" | "footprint_estimate" | "preference_elicitation" |           │
│ "listing_search" | "recommendation" | "order_creation"                                                           │
│ - ConversationMessage: { role, content, timestamp }                                                              │
│ - ExtractedPreferences: { project_types, regions, max_price_eur, co_benefits }                                   │
│ - WizardSession: { id, data: WizardSessionData }                                                                 │
│ - SSE event types: SSETokenEvent, SSEStepChangeEvent, SSEDoneEvent, SSEErrorEvent                                │
│ - STEP_ORDER array mapping steps to visual positions (5 dots)                                                    │
│ - STEP_LABELS record for display names                                                                           │
│                                                                                                                  │
│ 2. TanStack Query Hooks                                                                                          │
│                                                                                                                  │
│ useWizardSession — Query key: ["wizard-session"]                                                                 │
│ - Calls POST /wizard/session (creates or resumes active session)                                                 │
│ - staleTime: 5 * 60 * 1000 (session data is long-lived)                                                          │
│ - Uses get/post from @clients/api/client (same pattern as useUserResources)                                      │
│                                                                                                                  │
│ useWizardSendMessage — Mutation                                                                                  │
│ - Calls POST /wizard/session/{id}/message with { content }                                                       │
│ - On success, invalidates session query to sync conversation history                                             │
│                                                                                                                  │
│ useWizardSSE — Custom hook (not TanStack — it's push-based)                                                      │
│ - Uses fetch + ReadableStream (not EventSource) because the API client requires a token-handler-version: 1       │
│ header that EventSource can't send                                                                               │
│ - Accepts callbacks: onToken, onStepChange, onDone, onError                                                      │
│ - Returns { isStreaming, startStream, stopStream }                                                               │
│ - Cleans up on unmount via useEffect                                                                             │
│                                                                                                                  │
│ useWizardNavigation — Pure computation hook                                                                      │
│ - Maps currentStep to a numeric index for progress dots                                                          │
│ - Collapses onboarding → profile_check and listing_search → recommendation for visual step mapping               │
│                                                                                                                  │
│ 3. Core Components                                                                                               │
│                                                                                                                  │
│ WizardCard — Main step container                                                                                 │
│ - Styling: rounded-[1.25rem] bg-white border border-mist shadow-sm (matches WizardProgressTile.tsx:38)           │
│ - Step title bar with label and "Step X of Y" badge (matches WizardProgressTile.tsx:40-42 header pattern)        │
│ - GSAP slide animation on step change: content slides out/in with gsap.fromTo on x and opacity                   │
│ - Flex column: header, scrollable conversation area, input area                                                  │
│ - Height: fills available viewport via min-h-[calc(100vh-12rem)]                                                 │
│                                                                                                                  │
│ WizardProgressDots — Horizontal progress indicator                                                               │
│ - Row of dots connected by lines                                                                                 │
│ - Completed: bg-canopy, Current: bg-ember ring-2 ring-ember/30 scale-125 (matches sidebar pulse pattern),        │
│ Pending: bg-mist                                                                                                 │
│ - Connecting lines: bg-canopy for completed, bg-mist for pending                                                 │
│                                                                                                                  │
│ AgentMessage — Agent chat bubble                                                                                 │
│ - Left-aligned with Bot icon in bg-canopy circle                                                                 │
│ - Bubble: bg-mist/30 rounded-2xl rounded-tl-sm px-4 py-3                                                         │
│ - When isStreaming=true: blinking cursor <span className="inline-block w-2 h-4 bg-ember animate-pulse" />        │
│ (matches HeroPanel.tsx:97)                                                                                       │
│ - GSAP entrance: fade-in + slide-up                                                                              │
│                                                                                                                  │
│ UserMessage — User chat bubble                                                                                   │
│ - Right-aligned, bg-canopy text-linen bubble with rounded-2xl rounded-tr-sm                                      │
│                                                                                                                  │
│ ChatInput — Input bar                                                                                            │
│ - Rounded input + circular send button with magnetic-btn class                                                   │
│ - Disabled state while agent is streaming ("Agent is thinking...")                                               │
│ - Enter key sends, Shift+Enter for newline                                                                       │
│                                                                                                                  │
│ ListingRecommendationCard — For step 3 recommendations                                                           │
│ - Project name (serif font), country + type icons, price, "why we picked this" blurb                             │
│ - Expandable "Tell me more" using shadcn Accordion (~/modules/shared/ui/accordion.tsx)                           │
│ - Selectable with border-ember bg-ember/5 highlight state                                                        │
│                                                                                                                  │
│ 4. Presenter & View                                                                                              │
│                                                                                                                  │
│ WizardPresenter orchestrates:                                                                                    │
│ 1. useWizardSession() to create/fetch session on mount                                                           │
│ 2. Local state: messages (conversation history), streamingText (accumulating tokens), currentStep                │
│ 3. handleSend(text): optimistically appends user message, calls mutation, starts SSE stream                      │
│ 4. SSE callbacks: onToken appends to streamingText, onDone moves streamingText into messages, onStepChange       │
│ updates step                                                                                                     │
│ 5. Passes everything to WizardView                                                                               │
│                                                                                                                  │
│ WizardView is pure layout:                                                                                       │
│ - WizardProgressDots at top                                                                                      │
│ - WizardCard containing scrollable message list + step-specific content + ChatInput                              │
│                                                                                                                  │
│ 5. Routing Changes                                                                                               │
│                                                                                                                  │
│ routes.ts — Add wizard route inside DashboardLayout:                                                             │
│ layout("components/layout/DashboardLayout.tsx", [                                                                │
│   route("buyer/dashboard", "routes/dashboard.tsx"),                                                              │
│   route("buyer/wizard", "routes/wizard.tsx"),                                                                    │
│ ]),                                                                                                              │
│                                                                                                                  │
│ HomeView.tsx — Replace <AuthenticatedHome /> with <Navigate to="/buyer/wizard" replace /> from react-router      │
│                                                                                                                  │
│ Sidebar.tsx — Add { label: 'Purchase Wizard', icon: Sparkles, href: '/buyer/wizard' } to navItems                │
│                                                                                                                  │
│ 6. Route Entry (routes/wizard.tsx)                                                                               │
│                                                                                                                  │
│ Follows routes/home.tsx pattern: Suspense wrapper with PageSkeleton fallback around WizardPresenter.             │
│                                                                                                                  │
│ ---                                                                                                              │
│ Reusable Existing Code                                                                                           │
│                                                                                                                  │
│ ┌────────────────────────────┬──────────────────────────────────────────────┐                                    │
│ │            What            │                    Where                     │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ cn() utility               │ ~/lib/utils                                  │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ get(), post() API client   │ @clients/api/client                          │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ useAuth() hook             │ @clients/api/modules/.../AuthContext         │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ useUserResources() pattern │ ~/modules/shared/queries/useUserResources.ts │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ shadcn Accordion           │ ~/modules/shared/ui/accordion.tsx            │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ shadcn ScrollArea          │ ~/modules/shared/ui/scroll-area.tsx          │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ PageSkeleton               │ ~/modules/shared/components/PageSkeleton.tsx │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ GSAP animation pattern     │ WizardProgressTile.tsx, HeroPanel.tsx        │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ Card styling pattern       │ WizardProgressTile.tsx:38                    │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ Streaming cursor pattern   │ HeroPanel.tsx:97                             │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ magnetic-btn utility       │ app.css:96                                   │                                    │
│ ├────────────────────────────┼──────────────────────────────────────────────┤                                    │
│ │ canvas-confetti (step 5)   │ Already in package.json                      │                                    │
│ └────────────────────────────┴──────────────────────────────────────────────┘                                    │
│                                                                                                                  │
│ ---                                                                                                              │
│ Verification                                                                                                     │
│                                                                                                                  │
│ 1. Typecheck: Run bun run typecheck in the web-app container via mcp_polytope_exec                               │
│ 2. Visual: Navigate to http://localhost:8000 → log in with test credentials (jelle/jelle) → should redirect to   │
│ /buyer/wizard                                                                                                    │
│ 3. Sidebar: Wizard entry visible and active-highlighted on /buyer/wizard                                         │
│ 4. UI rendering: Progress dots, WizardCard, chat input all render correctly                                      │
│ 5. Mock conversation: Type a message, see it appear as a user bubble (send mutation will fail without backend,   │
│ but UI should handle gracefully with error toast)   