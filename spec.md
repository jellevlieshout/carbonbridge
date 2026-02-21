# CarbonBridge — Feature Specification
### Voluntary Carbon Credit Marketplace for SMEs
**Version 1.3 — Hackathon Build (30h)**

> **What's new in v1.1:** OffsetsDB integration (section 8), Seller Market Explorer (section 5.7), and Agent Decision Explainer UI (section 5.8).
> **What's new in v1.2:** LLM stack resolved (Pydantic AI + Gemini/Claude), currency changed to EUR, streaming limited to chat interfaces only, LangSmith adopted for agentic tracing.
> **What's new in v1.3:** Database changed from PostgreSQL to Couchbase.

---

## 1. Product Vision

CarbonBridge is a voluntary carbon credit brokerage and marketplace designed for SMEs with little or no prior experience in carbon markets. Where existing platforms overwhelm buyers with technical jargon, registry minutiae, and manual processes, CarbonBridge abstracts all of that complexity away behind an agent-guided conversational interface. Sellers list credits with minimal friction; buyers are guided through a natural wizard experience powered by an AI agent; and an optional autonomous agent can transact on a buyer's behalf entirely hands-free.

Sellers additionally benefit from market-wide intelligence: a live overview of projects drawn from CarbonPlan's OffsetsDB gives them a real-time view of the competitive landscape, and a dedicated explainability panel shows them exactly how their advisory or trading agent reasoned through every decision it made.

---

## 2. User Roles

| Role | Description |
|---|---|
| **Seller** | An organisation or individual holding verified carbon credits who wishes to list and sell them on the marketplace |
| **Buyer** | An SME looking to offset its carbon footprint; assumed to have low knowledge of the voluntary carbon market |
| **Admin** | Internal operator managing listings, disputes, and platform configuration (out of scope for hackathon MVP, but data model should support it) |

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       Next.js Frontend                          │
│   Wizard UI · Seller Dashboard · Market Explorer · Agent Trace  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST / SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                  FastAPI Backend (Python)                        │
│  Auth · Listings API · Orders API · OffsetsDB Sync · Webhooks   │
└───────┬──────────────┬────────────────┬────────────────────────-┘
        │              │                │
┌───────▼──────┐ ┌─────▼──────┐ ┌──────▼──────────────────────┐
│  Couchbase   │ │TigerBeetle │ │     Pydantic AI Agents       │
│  (App Data + │ │  (Ledger)  │ │  Buyer Wizard Agent          │
│   OffsetsDB  │ └────────────┘ │  Autonomous Buy Agent        │
│   cache)     │               │  Seller Advisory Agent       │
└─────────────-┘               └──────────┬──────────────────--┘
                                          │
               ┌──────────────────────────┼─────────────────────┐
               │                          │                      │
    ┌──────────▼──────┐       ┌───────────▼───────┐  ┌─────────▼───────┐
    │  Fake Registry  │       │  CarbonPlan        │  │  Stripe Payment │
    │  API            │       │  OffsetsDB API     │  │  + Agent Wallet │
    └─────────────────┘       │  (external)        │  └─────────────────┘
                              └────────────────────┘
```

---

## 4. Core Data Models

Couchbase is a document database, so each model below corresponds to a **document type** stored in a dedicated collection within a single bucket (e.g. `carbonbridge` bucket). The `type` field on each document doubles as a discriminator for N1QL queries. Indexes should be created on the fields marked as query targets.

### 4.1 User

```
type: "user",
id, email, hashed_password, role (buyer|seller|admin),
company_name, company_size_employees, sector, country,
stripe_customer_id, created_at, updated_at
```
Query indexes: `email` (unique), `role`.

### 4.2 CarbonCreditListing

```
type: "listing",
id, seller_id,
registry_name (e.g. "Verra", "Gold Standard", "ACR"),
registry_project_id, serial_number_range,
project_name, project_type (afforestation|renewable|cookstoves|etc),
project_country, vintage_year,
quantity_tonnes (available),
quantity_reserved, quantity_sold,
price_per_tonne_eur,
verification_status (pending|verified|failed),
methodology, co_benefits (array: biodiversity|community|sdg_goals),
description, supporting_documents (URLs),
status (draft|active|paused|sold_out),
created_at, updated_at
```
Query indexes: `seller_id`, `status`, `project_type`, `project_country`.

### 4.3 Order

```
type: "order",
id, buyer_id, status (pending|confirmed|completed|cancelled|refunded),
line_items (array: [{listing_id, quantity, price_per_tonne, subtotal}]),
total_eur, stripe_payment_intent_id, stripe_payment_status,
retirement_requested (bool), retirement_reference,
created_at, completed_at
```
Query indexes: `buyer_id`, `status`, `stripe_payment_intent_id`.

### 4.4 RegistryVerificationResult

```
type: "registry_verification",
id, listing_id, queried_at, raw_response (object),
is_valid, serial_numbers_available, project_verified,
error_message
```
Query indexes: `listing_id`.

### 4.5 BuyerProfile

Stored as a sub-document on the User document under the key `buyer_profile`, rather than a separate collection, since it has a strict 1:1 relationship with a buyer user and is always fetched together with the user.

```
annual_co2_tonnes_estimate,
primary_offset_motivation (compliance|esg_reporting|brand|personal),
preferred_project_types (array),
preferred_regions (array),
budget_per_tonne_max_eur,
autonomous_agent_enabled,
autonomous_agent_criteria (object),
autonomous_agent_wallet_id
```

### 4.6 OffsetsDBProject

Populated by the nightly OffsetsDB sync (section 8). Read-only from the application's perspective.

```
type: "offsets_db_project",
id (internal), offsets_db_project_id (e.g. "VCS-1234"),
registry (ACR|ART|CAR|GLD|VCS),
name, category (Forest|Renewable Energy|GHG Management|
  Energy Efficiency|Fuel Switching|Agriculture|Other),
project_type, country, protocol, methodology,
total_credits_issued, total_credits_retired,
first_issuance_date, last_issuance_date,
market_type (compliance|voluntary),
status, offsets_db_url,
raw_data (object — full OffsetsDB response),
synced_at
```
Query indexes: `offsets_db_project_id` (unique), `registry`, `category`, `country`.

### 4.7 AgentRun

Records every execution of either the autonomous buyer agent or the seller advisory agent, with full decision provenance. This is the backing data for the Agent Decision Explainer (section 5.8).

```
type: "agent_run",
id, agent_type (autonomous_buyer|seller_advisory),
owner_id (buyer_id or seller_id),
triggered_at, completed_at,
trigger_reason (scheduled|manual|threshold_exceeded),
status (running|completed|failed|awaiting_approval),

trace_steps: [
  {
    step_index: int,
    step_type: (tool_call|reasoning|decision|output),
    label: str,
    input: any,
    output: any,
    duration_ms: int,
    listings_considered: [listing_id | offsets_db_project_id],
    score_breakdown: {
      project_type_match: float,
      price_score: float,
      vintage_score: float,
      co_benefit_score: float,
      total: float
    }
  }
],

listings_shortlisted (array of IDs),
final_selection_id,
selection_rationale (plain-English string generated by agent),
action_taken (purchased|proposed|skipped|failed),
order_id (nullable),
error_message (nullable)
```
Query indexes: `owner_id`, `agent_type`, `triggered_at`.

### 4.8 WizardSession

Stores multi-turn buyer wizard state so sessions survive browser closes.

```
type: "wizard_session",
id, buyer_id,
current_step (profile_check|onboarding|footprint_estimate|
  preference_elicitation|listing_search|recommendation|order_creation),
conversation_history (array of {role, content, timestamp}),
extracted_preferences (object: project_types, regions, max_price_eur, co_benefits),
created_at, last_active_at, expires_at
```
Query indexes: `buyer_id`, `expires_at` (for TTL cleanup).

### 4.9 TigerBeetle Accounts (Ledger)

Each user has two TigerBeetle accounts: a **pending** account and a **settled** account. Credits move from pending to settled upon payment confirmation. Account IDs are stored on the User document as `tigerbeetle_pending_account_id` and `tigerbeetle_settled_account_id`. TigerBeetle is a separate process and is not a Couchbase collection.

---

## 5. Feature Areas

---

### 5.1 Authentication & Onboarding

**Scope: MVP**

Both buyers and sellers register with email and password. On first login they are directed to a short onboarding flow appropriate to their role.

Seller onboarding collects: company name, company registration number, country, and bank/payout details (Stripe Connect onboarding).

Buyer onboarding feeds directly into the buyer profile (section 5.3 wizard step 0). The role is selected during registration; it is not changeable via the UI in the hackathon build.

Tech notes: JWT-based auth stored in httpOnly cookies. FastAPI dependency injection for route-level auth guards. User documents are looked up by email using the Couchbase N1QL index on `email`.

---

### 5.2 Seller: Listing Management

**Scope: MVP**

Sellers access a clean dashboard showing their active listings, pending verifications, and recent sales.

#### 5.2.1 Create a Listing

A multi-step form collects:

**Step 1 — Registry Details**
Registry name (dropdown: Verra, Gold Standard, American Carbon Registry, Climate Action Reserve, or "Other"), project ID, serial number range, and vintage year. On submission, the system calls the Fake Registry API to verify the credit batch (see section 9). A spinner shows while verification runs. Results are displayed inline: a green confirmed badge or a red rejection reason.

**Step 2 — Project Details**
Project name (auto-populated from registry lookup where available), project type, country, methodology, description, co-benefits checkboxes, and optional document uploads (PDFs, images).

**Step 3 — Pricing & Quantity**
Price per tonne (EUR), quantity to list, minimum order quantity (default 1), and optional expiry date for the listing.

**Step 4 — Review & Publish**
Summary card. Seller can save as draft or publish immediately. Published listings appear on the marketplace within seconds.

#### 5.2.2 Listing Management

Sellers can pause, unpause, edit pricing/quantity, or archive listings. Editing registry details on an active listing triggers a re-verification. The system tracks reserved quantity separately from available quantity so that in-flight buyer sessions do not oversell. Quantity updates use Couchbase's **sub-document API** (`MutateIn`) to atomically increment/decrement `quantity_reserved` and `quantity_tonnes` without loading and rewriting the full listing document, avoiding race conditions under concurrent buyer sessions.

#### 5.2.3 Sales History

A table of completed orders showing buyer (anonymised to company name only), quantity, total value, and date. CSV export available.

---

### 5.3 Buyer: Guided Wizard

**Scope: MVP (core)**

This is the primary buyer experience. The wizard is conversational, agent-assisted, and deliberately simple. Each step is rendered as a clean card. The buyer does not see a listing catalogue; they tell the agent what they need, and the agent surfaces appropriate options.

The Pydantic AI wizard agent runs server-side. The frontend communicates with it via an SSE endpoint (this is one of the two chat-style interfaces in the system that warrant streaming — see section 6.2). Agent responses stream token-by-token for a natural conversational feel. Session state is persisted in Couchbase (WizardSession document, section 4.8) so a buyer can close the browser and resume where they left off.

The agent has access to the following tools:

- `search_listings(filters)` — queries active, verified listing documents from Couchbase
- `get_listing_detail(listing_id)` — retrieves a single listing document
- `estimate_footprint(sector, employees, country)` — returns a rough tonne estimate using a lookup table (seeded data)
- `create_order_draft(buyer_id, line_items)` — creates a pending order document
- `get_buyer_profile(buyer_id)` — reads the buyer_profile sub-document from the User document

#### Wizard Steps

**Step 0 — "Let's understand your situation"**
If the buyer has no saved profile, the agent asks two or three simple questions:
- "What does your company do?" (free text, agent infers sector)
- "Roughly how many people work there?"
- "Why are you looking to offset — is it for a report, a client, personal values, or something else?"

The agent confirms its understanding in a short plain-English summary. The buyer can correct it before proceeding. This data is saved to the `buyer_profile` sub-document on the User document.

**Step 1 — "How much do you need to offset?"**
The agent presents a plain-language estimate based on sector and headcount ("Companies like yours typically emit around X–Y tonnes per year"). The buyer can accept the estimate, enter their own number, or say "I'm not sure" to proceed with the estimate. The agent explains what a tonne of CO2 means in terms the buyer will recognise (e.g. "roughly equivalent to three return flights London to New York").

**Step 2 — "What matters to you?"**
The agent presents three or four project-type cards with plain descriptions, no jargon. For example: "Plant trees in the Amazon — protects biodiversity and local communities", "Replace old cookstoves in Ghana — cuts indoor air pollution and improves health", "Wind energy in India — displaces coal-fired power". The buyer selects one or more that resonate. They can also optionally set a budget per tonne.

**Step 3 — "Here are your options"**
The agent calls `search_listings` using the buyer's preferences and returns two or three curated recommendations. Each card shows:
- Project name and a one-sentence plain description
- Country and project type icon
- Price per tonne and total for the buyer's quantity
- A short "why we picked this" blurb generated by the agent
- A "Tell me more" expandable section

The buyer selects one option or asks the agent to "show me something different" (the agent re-queries with loosened filters).

**Step 4 — "Confirm & Pay"**
Order summary card showing: project, quantity, price per tonne, total. Stripe Payment Element embedded inline. On payment confirmation, the order document is updated to `completed` status, TigerBeetle ledger entries are created, and an email confirmation is sent. If the buyer wants a retirement certificate, they check a box; the system sets `retirement_requested: true` on the order document (manually processed post-hackathon).

**Step 5 — "You're done"**
Confirmation screen with a plain-English summary: "You've offset X tonnes of CO2 — equivalent to Y flights or Z years of home energy use." A shareable badge (SVG) is generated on the fly for the buyer to post on LinkedIn or their website. The buyer's dashboard shows the purchase history and their total offset to date.

---

### 5.4 Buyer: Dashboard

**Scope: MVP (light)**

A simple overview page for returning buyers showing total tonnes offset, a list of past orders, and a prompt to "offset more". If the autonomous agent is enabled, its status is shown here.

---

### 5.5 Autonomous Purchasing Agent (Nice to Have)

**Scope: Nice to have — implement after core wizard**

An opt-in feature for buyers who want CarbonBridge to automatically purchase offsets on their behalf.

#### 5.5.1 Setup Flow

Accessible from the buyer dashboard via "Set up automatic offsetting". The buyer configures:

- **Trigger**: monthly on a set date, or when their estimated footprint for the year exceeds a threshold
- **Criteria**: preferred project types, preferred regions, maximum price per tonne
- **Budget cap**: maximum spend per transaction and per year
- **Approval mode**: auto-approve (fully autonomous) or "notify me first" (agent proposes, buyer approves within 48 hours or it auto-approves)

On saving, a Stripe Agent Wallet is provisioned and the `autonomous_agent_criteria` sub-document on the buyer's User document is updated.

#### 5.5.2 Agent Execution

A scheduled Pydantic AI workflow runs nightly. For each buyer with `autonomous_agent_enabled: true`, the workflow:

1. Checks if a purchase trigger condition is met
2. Calls `search_listings` with the buyer's stored criteria
3. Scores results and selects the best match
4. If approval mode is "auto-approve": creates an order document and executes payment via the Stripe Agent Wallet
5. If approval mode is "notify first": creates an order document with status `awaiting_approval` and sends an email with a one-click approve/reject link
6. Writes a full AgentRun document (section 4.7) including the complete `trace_steps` array

#### 5.5.3 Stripe Agent Wallet Integration

The Stripe Agent Wallet is scoped to this application. The wallet's spending limit is enforced server-side and must not exceed the buyer's configured budget cap. All wallet transactions are mirrored in TigerBeetle.

---

### 5.6 Marketplace Browse (Nice to Have)

**Scope: Nice to have**

A secondary, optional entry point for buyers who prefer to browse rather than use the wizard. Filterable by project type, country, price range, vintage year, and co-benefits. Each listing card links to a detail page. Buyers can add to a basket and check out directly. This bypasses the agent wizard but still uses the same order and payment flow.

---

### 5.7 Seller: Market Explorer

**Scope: P1 (implement after seller listing management)**

A dedicated section of the seller dashboard giving sellers a panoramic view of the broader carbon market, drawing on both CarbonBridge's own listing documents and the CarbonPlan OffsetsDB dataset cached in Couchbase (section 8).

The page is read-only. Sellers cannot transact from this view.

#### 5.7.1 Layout

The Market Explorer has two tabs: **Projects** and **Insights**.

#### 5.7.2 Projects Tab

A filterable, searchable table of projects drawn from the merged dataset (section 8.3). Each row shows:

| Column | Source |
|---|---|
| Project ID | OffsetsDB or CarbonBridge listing |
| Name | OffsetsDB or listing |
| Registry | OffsetsDB or listing |
| Category / Type | OffsetsDB category + type |
| Country | OffsetsDB or listing |
| Vintage | Listing only |
| Credits Issued | OffsetsDB |
| Credits Retired | OffsetsDB |
| Retirement % | Derived |
| On CarbonBridge? | Badge: yes (with link to listing) or no |
| Price / tonne | CarbonBridge listings only; "—" for OffsetsDB-only projects |

Filter controls: Registry (multi-select), Category (multi-select), Country (multi-select), Programme (compliance / voluntary / all). Results are paginated server-side (50 per page), driven by N1QL queries against the `offsets_db_project` collection.

Clicking any row opens a slide-over panel with full project detail, a chart of issuances and retirements over time, and — if the project has a CarbonBridge listing — the current price, available quantity, and a link to the listing.

#### 5.7.3 Insights Tab

Pre-computed summary charts, refreshed nightly by the OffsetsDB sync and cached as a single `market_insights` document in Couchbase. Charts:

- Credits issued vs retired by registry (stacked bar)
- Top 10 project categories by issued volume (horizontal bar)
- Country heat map (choropleth, SVG world map)
- CarbonBridge coverage by category (donut chart)

The seller's own listings are highlighted in each chart where relevant.

---

### 5.8 Seller: Agent Decision Explainer

**Scope: P1**

Every agent execution writes a structured AgentRun document to Couchbase (section 4.7). The Agent Decision Explainer surfaces this as a human-readable timeline.

Accessible from the seller dashboard ("View agent activity") and the autonomous agent status widget on the buyer dashboard.

#### 5.8.1 Run List

A chronological list of AgentRun documents for the current user, queried by `owner_id`. Each row shows: date/time, agent type, trigger reason, action taken, and status badge. Clicking a row opens the Run Detail view.

#### 5.8.2 Run Detail View

A vertical timeline of steps from `trace_steps`, rendered top to bottom. Each step is a card with a distinct visual treatment:

**Tool Call step** — tool name and inputs as human-readable filter chips, response expandable. Search steps show result count and a preview list.

**Reasoning step** — agent chain-of-thought in a light grey italic block. Omitted if reasoning was not captured.

**Scoring step** — comparison table of shortlisted listings with columns per scoring dimension. Winning row highlighted. Column tooltips explain each score in plain English.

**Decision step** — highlighted card showing final selection and `selection_rationale`.

**Output step** — action taken: purchase details, approval sent, no match found, or error.

#### 5.8.3 Contextual Annotations

Inline badges throughout the timeline:

- **"Market reference"** — agent used OffsetsDB context in its reasoning
- **"Criteria miss"** — search returned zero results before filters were widened
- **"Budget boundary"** — listing excluded due to price ceiling

#### 5.8.4 Export

"Download trace" exports the full AgentRun document as JSON.

---

## 6. Agent Architecture (Pydantic AI)

### 6.1 Library & Model Choice

All agents are built with **Pydantic AI** rather than LangGraph. Pydantic AI provides structured tool-calling, typed inputs/outputs, and first-class support for both Anthropic Claude and Google Gemini. The split:

- **Claude** (e.g. `claude-sonnet-4-5`) — buyer wizard agent. Stronger conversational tone, better instruction-following for the plain-language constraints.
- **Gemini** (e.g. `gemini-2.0-flash`) — autonomous buyer agent and seller advisory agent. Faster and cheaper for batch workloads where warmth is less important than throughput.

The model provider is injected at construction time in Pydantic AI and can be switched with a one-line config change. Multi-step flows are implemented as sequential async function calls within a FastAPI route, or as a lightweight state machine for the wizard's multi-turn case. All agent runs are traced via LangSmith (section 6.5).

### 6.2 Buyer Wizard Agent

A multi-turn Pydantic AI agent. Each user message hits `POST /wizard/session/{id}/message`, which loads the WizardSession document from Couchbase, runs the next agent step, updates the session document, and streams the response via SSE. **SSE is used only for this endpoint** (and any other chat-style interfaces) because token-by-token streaming is central to the conversational feel. All other agent invocations return complete JSON.

Logical flow (implemented as a `current_step` field on the WizardSession document):

```
profile_check
  ├── (missing) → onboarding_conversation
  └── (exists)  → footprint_estimate
                      └── preference_elicitation
                                └── listing_search
                                          └── recommendation_presentation
                                                    └── order_creation
```

System prompt constraints: no jargon, short responses (max three sentences unless asked), warm but not sycophantic, no competitor names in recommendations.

### 6.3 Autonomous Purchase Agent (Buyer-side)

A Pydantic AI agent invoked by the nightly scheduler as a plain async function — no streaming. Runs to completion and returns a result object written to an AgentRun document in Couchbase.

```
load_buyer_criteria
  └── check_trigger_condition
        ├── (not triggered) → write_agent_run(skipped)
        └── (triggered) → search_and_score_listings
                              └── select_best_match
                                    └── create_draft_order
                                          ├── (auto-approve) → execute_payment → write_agent_run
                                          └── (notify-first) → send_approval_email → write_agent_run
```

Each step appends to a running `trace_steps` list flushed to the AgentRun document at completion.

### 6.4 Seller Advisory Agent

A Pydantic AI agent triggered on demand or automatically on listing publication. No streaming; returns a complete JSON recommendation report stored in an AgentRun document and surfaced via the Decision Explainer.

```
load_seller_listing(s)
  └── fetch_market_context      ← N1QL query against offsets_db_project collection
        └── score_competitive_position
              └── generate_recommendations
                    └── write_agent_run
```

### 6.5 LangSmith Tracing

LangSmith is used as the observability layer for all three agents via Pydantic AI's OpenTelemetry-compatible tracing interface. Every agent invocation emits a trace automatically when `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT` are set.

LangSmith traces are the raw developer-facing view (token usage, latency, tool call I/O). The AgentRun `trace_steps` stored in Couchbase is the separate, human-readable application-level record that powers the Decision Explainer UI. These are complementary, not duplicates.

### 6.6 Tool Definitions (FastAPI endpoints consumed by agents)

All agent tools are backed by internal FastAPI endpoints with a shared API key, not exposed publicly.

| Tool | Endpoint | Notes |
|---|---|---|
| `search_listings` | `POST /internal/listings/search` | N1QL query on listing collection; filters: project_type, country, max_price, min_quantity, vintage_year |
| `get_listing_detail` | `GET /internal/listings/{id}` | Single document fetch by key |
| `estimate_footprint` | `POST /internal/footprint/estimate` | Sector + employees → tonne range |
| `create_order_draft` | `POST /internal/orders/draft` | Inserts order document with status pending |
| `execute_payment` | `POST /internal/orders/{id}/pay` | Charges Stripe Agent Wallet |
| `get_buyer_profile` | `GET /internal/buyers/{id}/profile` | Sub-document fetch of buyer_profile from User document |
| `get_market_context` | `POST /internal/offsets-db/market-context` | N1QL query on offsets_db_project collection for comparable projects and category trends |

---

## 7. Fake Registry API

A self-contained FastAPI router at `/fake-registry/` that mimics the response shape of real carbon credit registries.

### 7.1 Endpoints

```
GET  /fake-registry/projects/{project_id}
     → Returns project metadata: name, type, country, methodology, status

GET  /fake-registry/credits/{serial_range}
     → Returns: is_valid, available_quantity, vintage_year, retirement_status

POST /fake-registry/retire
     → Marks credits as retired; returns retirement reference number
```

### 7.2 Behaviour

- Project IDs beginning with `V-`, `GS-`, `ACR-` are treated as valid
- Serial ranges are validated against a seeded lookup table (section 10)
- Configurable failure rate (default 10%) for realistic error responses
- Simulated latency: 800ms–2000ms with jitter
- Deterministic responses given the same input (hash-based), so demos are reproducible

---

## 8. CarbonPlan OffsetsDB Integration

### 8.1 Overview

CarbonPlan's OffsetsDB is a publicly accessible, daily-updated database of carbon offset projects and credit transactions drawn from five registries: ACR, ART, CAR, Gold Standard, and Verra. The data is subject to CarbonPlan's Terms of Data Access, which permit research and transparency use. Attribution must be included in the UI wherever OffsetsDB data is shown: "Project data sourced from CarbonPlan OffsetsDB."

The integration uses a **nightly bulk sync** approach rather than live per-request API calls. This keeps seller-facing pages fast and degrades gracefully if the OffsetsDB API is temporarily unavailable.

### 8.2 Sync Architecture

A scheduled background task runs at 02:00 UTC daily.

```
1. Download latest bulk CSV from S3:
   https://carbonplan-offsets-db.s3.us-west-2.amazonaws.com/production/latest/offsets-db.csv.zip

2. Parse and normalise with pandas / polars:
   - Map OffsetsDB registry codes → CarbonBridge canonical names
   - Normalise category and project_type strings
   - Parse date fields to ISO 8601
   - Compute derived field: retirement_rate = total_credits_retired / total_credits_issued

3. Upsert into Couchbase offsets_db_project collection:
   - Match on offsets_db_project_id (used as the Couchbase document key)
   - Set synced_at = now()

4. Recompute Insights Tab aggregates and write as a single
   market_insights document in Couchbase (overwrite on each sync):
   - credits_by_registry, credits_by_category, credits_by_country, coverage_by_category

5. Log sync result to a sync_log document: rows_processed, rows_upserted, rows_failed, duration_ms
```

The sync is idempotent. The OffsetsDB FastAPI at `https://offsets-db-api.fly.dev` is available as a fallback for real-time per-project enrichment when a new listing is published, with a 5-second timeout.

### 8.3 Merged Dataset Logic

The Market Explorer presents a unified view of OffsetsDB project documents and CarbonBridge listing documents. The merge happens at query time in the backend:

```python
def build_merged_project_view(filters):
    offsets_db_rows = couchbase_n1ql(
        "SELECT * FROM carbonbridge WHERE type='offsets_db_project' AND ...",
        filters
    )
    cb_listings = couchbase_n1ql(
        "SELECT * FROM carbonbridge WHERE type='listing' AND status='active'"
    )

    cb_index = {l['registry_project_id']: l for l in cb_listings}

    results = []
    for project in offsets_db_rows:
        row = dict(project)
        listing = cb_index.get(project['offsets_db_project_id'])
        row['on_carbonbridge'] = listing is not None
        row['cb_listing_id'] = listing['id'] if listing else None
        row['cb_price_per_tonne_eur'] = listing['price_per_tonne_eur'] if listing else None
        row['cb_quantity_available'] = listing['quantity_tonnes'] if listing else None
        results.append(row)

    return results
```

CarbonBridge-only listings not yet in OffsetsDB are appended at the end with OffsetsDB fields set to null.

### 8.4 Data Fields Mapping

| OffsetsDB field | CarbonBridge mapping |
|---|---|
| `project_id` | `offsets_db_project_id` (Couchbase document key) |
| `name` | `name` |
| `registry` | Normalised to CarbonBridge registry enum |
| `category` | `category` |
| `project_type` | `project_type` |
| `country` | `country` |
| `protocol` | `methodology` (partial overlap) |
| `issued` | `total_credits_issued` |
| `retired` | `total_credits_retired` |
| `status` | `status` |

Fields not yet modelled (e.g. per-transaction retirement user data) are stored in `raw_data` and accessible via the slide-over panel.

### 8.5 Attribution Requirement

Every UI surface presenting OffsetsDB data must include:

> Project data sourced from [CarbonPlan OffsetsDB](https://carbonplan.org/research/offsets-db)

This appears as a footnote on the Market Explorer, the project slide-over panel, and any agent reasoning that references OffsetsDB market context.

---

## 9. Payment Architecture

### 9.1 Standard Buyer Checkout

1. Frontend calls `POST /orders` — backend inserts a pending order document in Couchbase and reserves quantity via sub-document `MutateIn`
2. Backend creates a Stripe PaymentIntent and returns `client_secret`
3. Frontend renders Stripe Payment Element
4. On payment success, Stripe webhook fires `payment_intent.succeeded` to `POST /webhooks/stripe`
5. Backend updates the order document to `completed`, creates TigerBeetle ledger entries
6. Seller settlement runs on a daily batch (ledger entries exist; disbursement out of scope for hackathon)

Order reservations expire after 15 minutes. A background task releases reserved quantity using sub-document `MutateIn` on the listing document.

### 9.2 Stripe Agent Wallet

The autonomous agent charges via Stripe's Treasury / Issuing API. The implementation degrades gracefully to a standard saved payment method charge if the specific wallet product is unavailable in sandbox, with the wallet being a logical concept in the application layer only.

---

## 10. Data Seeding

```bash
python scripts/seed.py --scenario demo
```

### 10.1 Seed Scenarios

**`demo`**: Curated dataset for a live walkthrough.
**`stress`**: 500 listings, 1000 buyers, 5000 orders.
**`empty`**: Collections and indexes only, no documents.

### 10.2 Demo Seed Contents

**Sellers (3):** GreenForest Ltd (UK), SolarPath GmbH (Germany), EarthWorks Co (Kenya).

**Listings (9):** afforestation (Brazil, Kenya), renewable energy (India, Morocco), cookstoves (Ghana, Uganda), methane capture (USA). Prices €8–€28/t. One listing seeded with 3 tonnes remaining to demo sold-out edge case.

**Buyers (5):** 12-person marketing agency (London), 45-person manufacturing SME (Birmingham), 3-person law firm (Edinburgh), 200-person logistics company (Manchester), one buyer with autonomous agent enabled.

**Orders (12):** Mix of completed, pending, and one cancelled.

**WizardSessions (2):** One completed, one mid-flow (step: preference_elicitation), to demo session resume.

**OffsetsDB Cache (200 documents):** Curated subset covering all five registries and six categories, inserted directly into the `offsets_db_project` collection. Accepts `--live-sync` flag to pull real OffsetsDB data instead.

**AgentRun documents (6):** Two autonomous buyer runs (one completed, one awaiting approval), two seller advisory runs, two failed runs. Cover all step types and annotation types for the Decision Explainer demo.

**market_insights document (1):** Pre-computed Insights Tab aggregates matching the seeded OffsetsDB documents.

**Fake Registry Seed Data:** 50 project records and 200 serial number ranges matching the seeded listings.

### 10.3 Seeder Implementation Notes

Python script using the Couchbase Python SDK (`couchbase` package) directly against the collections. Uses upsert semantics on natural document keys (e.g. listing ID, `offsets_db_project_id`) so running the seeder twice does not duplicate documents. Also seeds TigerBeetle accounts using the TigerBeetle Python client.

---

## 11. Frontend Architecture (Next.js)

### 11.1 Pages & Routes

```
/                          → Marketing landing / role selector
/auth/register             → Registration
/auth/login

/seller/dashboard          → Listing overview + sales stats
/seller/listings/new       → Create listing wizard
/seller/listings/[id]      → Edit listing
/seller/market             → Market Explorer
/seller/agent              → Agent Decision Explainer (run list)
/seller/agent/[run_id]     → Agent Run Detail (step timeline)

/buyer/wizard              → Guided purchase wizard
/buyer/dashboard           → Purchase history + autonomous agent status
/buyer/agent               → Buyer's autonomous agent run history
/buyer/agent/[run_id]      → Agent Run Detail (read-only, buyer view)
/buyer/agent/setup         → Autonomous agent configuration

/marketplace               → Browse all listings (nice to have)
/listings/[id]             → Listing detail (nice to have)
```

### 11.2 State Management

TanStack Query manages all server state. Key query keys:

- `['listings', filters]` — marketplace browse
- `['listing', id]` — single listing detail
- `['orders', buyerId]` — buyer order history
- `['wizard-session', sessionId]` — wizard agent state (SSE for streaming turns)
- `['seller-stats', sellerId]` — seller dashboard aggregates
- `['market-explorer', filters]` — merged OffsetsDB + CarbonBridge project list
- `['market-insights']` — pre-computed Insights Tab aggregates (1-hour cache TTL)
- `['agent-runs', {ownerId, agentType}]` — run list for Decision Explainer
- `['agent-run', runId]` — single AgentRun document with full trace_steps

### 11.3 Component Highlights

**WizardCard**: Core wizard step container with slide animation and dot progress indicator.

**AgentMessage**: Renders streaming agent text with a typing cursor. Markdown rendered inline.

**ListingRecommendationCard**: Recommendation card with lazy-loaded "Tell me more" section.

**StripePaymentWrapper**: Wraps Stripe Payment Element; handles loading, error, and success states.

**FootprintBadge**: SVG/canvas badge showing buyer's total offset. Downloadable as PNG.

**MarketProjectTable**: Paginated, filterable table for the Market Explorer. Handles merged dataset, source badges (OffsetsDB / CarbonBridge / both), row click → slide-over, and OffsetsDB attribution footnote.

**AgentRunTimeline**: Renders the Decision Explainer step timeline from a single AgentRun document's `trace_steps`. Contains the Export button.

**TraceStepCard**: Single step in the agent timeline. Handles all four step types with distinct visual treatments. Renders contextual annotation badges (Market Reference, Criteria Miss, Budget Boundary).

---

## 12. API Endpoints Summary (FastAPI)

### Auth
```
POST /auth/register
POST /auth/login
POST /auth/logout
GET  /auth/me
```

### Listings
```
GET  /listings                      (public, filterable — N1QL on listing collection)
GET  /listings/{id}                 (public — document fetch by key)
POST /listings                      (seller auth)
PUT  /listings/{id}                 (seller auth)
DELETE /listings/{id}               (seller auth, soft delete)
POST /listings/{id}/verify          (seller auth, triggers registry check)
```

### Orders
```
POST /orders                        (buyer auth)
GET  /orders                        (buyer auth)
GET  /orders/{id}                   (buyer/seller auth)
POST /orders/{id}/cancel            (buyer auth, pending only)
```

### Wizard / Agent
```
POST /wizard/session                (buyer auth)
GET  /wizard/session/{id}/stream    (SSE, buyer auth)
POST /wizard/session/{id}/message   (buyer auth)
```

### Buyer Profile
```
GET  /buyers/me/profile
PUT  /buyers/me/profile
POST /buyers/me/agent/enable
POST /buyers/me/agent/disable
PUT  /buyers/me/agent/criteria
```

### Market Explorer (seller)
```
GET  /market/projects               (seller auth, paginated N1QL)
GET  /market/projects/{id}          (seller auth)
GET  /market/insights               (seller auth, reads market_insights document)
```

### Agent Runs
```
GET  /agent-runs                    (auth, own runs)
GET  /agent-runs/{id}               (auth, own runs only)
GET  /agent-runs/{id}/export        (auth, returns raw AgentRun document as JSON)
POST /agent-runs/trigger-advisory   (seller auth)
```

### Webhooks
```
POST /webhooks/stripe
```

### Internal (agent tools only)
```
POST /internal/listings/search
GET  /internal/listings/{id}
POST /internal/footprint/estimate
POST /internal/orders/draft
POST /internal/orders/{id}/pay
GET  /internal/buyers/{id}/profile
POST /internal/offsets-db/market-context
```

### Fake Registry
```
GET  /fake-registry/projects/{id}
GET  /fake-registry/credits/{serial_range}
POST /fake-registry/retire
```

### Admin / Ops
```
POST /dev/seed?scenario=demo
DELETE /dev/seed
POST /admin/offsets-db/sync
GET  /admin/offsets-db/sync-log     (reads sync_log documents)
```

---

## 13. Environment Variables

```
# Couchbase
COUCHBASE_CONNECTION_STRING=couchbases://...
COUCHBASE_USERNAME=
COUCHBASE_PASSWORD=
COUCHBASE_BUCKET=carbonbridge

# TigerBeetle
TIGERBEETLE_ADDRESS=127.0.0.1:3000

# Auth
JWT_SECRET=
JWT_EXPIRY_MINUTES=1440

# Stripe
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

# Pydantic AI / LLM
ANTHROPIC_API_KEY=       (buyer wizard agent — Claude)
GOOGLE_API_KEY=          (autonomous + advisory agents — Gemini)

# LangSmith
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=carbonbridge

# Internal agent auth
INTERNAL_AGENT_API_KEY=

# Fake Registry
FAKE_REGISTRY_FAILURE_RATE=0.1
FAKE_REGISTRY_MIN_LATENCY_MS=800
FAKE_REGISTRY_MAX_LATENCY_MS=2000

# OffsetsDB
OFFSETS_DB_S3_URL=https://carbonplan-offsets-db.s3.us-west-2.amazonaws.com/production/latest/offsets-db.csv.zip
OFFSETS_DB_API_URL=https://offsets-db-api.fly.dev
OFFSETS_DB_SYNC_CRON=0 2 * * *
OFFSETS_DB_SYNC_TIMEOUT_SECONDS=120

# App
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000
```

---

## 14. Hackathon Build Priority

| Priority | Feature |
|---|---|
| P0 | Auth, Seller listing creation, Fake Registry API, Couchbase schema + indexes, Seeder |
| P0 | Buyer Wizard (Steps 0–4), Stripe payment checkout |
| P0 | Order confirmation, basic buyer and seller dashboards |
| P1 | SSE streaming for wizard agent |
| P1 | Agent tool integrations (search, estimate, recommend) |
| P1 | TigerBeetle ledger integration |
| P1 | OffsetsDB nightly sync + Couchbase offsets_db_project collection |
| P1 | Seller Market Explorer — Projects tab |
| P1 | Agent Decision Explainer — run list + step timeline |
| P2 | Seller Market Explorer — Insights tab (charts) |
| P2 | Seller Advisory Agent + trigger endpoint |
| P2 | Autonomous agent setup UI |
| P2 | Autonomous agent scheduler + Stripe Agent Wallet |
| P3 | Marketplace browse page |
| P3 | Footprint badge / share feature |
| P3 | CSV export for sellers |

---

## 15. Open Questions / Decisions Needed

1. **Couchbase tier**: Confirm whether the hackathon environment uses Couchbase Capella (managed cloud) or a self-hosted instance. Capella is faster to get running; self-hosted gives more control over index configuration. Connection strings and SDK initialisation differ slightly between the two.

2. **OffsetsDB Terms compliance**: Confirm planned usage (caching, display in a commercial marketplace, attribution) is consistent with CarbonPlan's Terms of Data Access before going live.

3. **Stripe Agent Wallet specifics**: Confirm available sandbox features before building section 5.5.2 so the implementation can degrade gracefully if needed.

4. **Non-Eurozone seller payouts**: EUR is the platform currency. Confirm whether sellers in non-Eurozone countries (e.g. GreenForest Ltd in the UK) need a secondary payout currency option in Stripe Connect.

5. **Retirement certificates**: Is it sufficient to show a mock certificate in the demo UI, or should this be skipped entirely?

6. **Email delivery**: Resend/SendGrid or console-logged mocks for the hackathon?

7. **Agent reasoning visibility**: For Claude, extended thinking blocks can be stored in `trace_steps` and shown in the Decision Explainer. For Gemini, reasoning token visibility depends on the model tier. Decide per-agent early as it affects the trace schema.
