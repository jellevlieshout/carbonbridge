# CarbonBridge

**An agent-first carbon credit trading exchange for SMEs.**

CarbonBridge is an AI-powered voluntary carbon credit marketplace that makes it effortless for small and medium-sized enterprises to buy, sell, and retire carbon credits. Instead of navigating complex registries and opaque pricing, users interact with intelligent agents that handle everything from footprint estimation to autonomous purchasing.

---

## The Problem

The voluntary carbon credit market is worth billions, yet it remains inaccessible to SMEs. Small companies earning carbon credits (e.g., through EV charger installations) have no easy way to sell them. Buyers face fragmented marketplaces, confusing terminology, and no guidance on what to purchase. The result: a massive vacuum where credits go untraded and emissions go unoffset.

## Our Solution

CarbonBridge bridges this gap with three AI agents that automate the entire carbon credit lifecycle:

1. **Buyer Wizard Agent** (Claude) - A conversational guide that walks buyers through footprint estimation, preference collection, and listing recommendations in plain language. No jargon, no complexity.

2. **Autonomous Buyer Agent** (Gemini) - Runs on a schedule, automatically finding and purchasing carbon credits that match a buyer's criteria and budget. Fully hands-free offsetting.

3. **Seller Advisory Agent** (Gemini) - Analyzes market conditions and a seller's listings to provide pricing recommendations, competitive positioning, and co-benefit highlights.

Every agent decision is fully transparent: scored, traced, and explainable through a Decision Explainer UI with complete provenance logs.

---

## Key Features

### For Buyers
- **Guided Wizard** - Conversational agent walks through footprint estimation, preference selection, and credit purchasing in 5 steps
- **Autonomous Offsetting** - Configure preferences once, let the agent purchase monthly within your budget
- **SSE Streaming** - Real-time token-by-token agent responses for a natural conversational feel
- **Stripe Checkout** - Secure payment processing with quantity reservation (prevents overselling)

### For Sellers
- **Listing Management** - Create and manage carbon credit listings with registry verification
- **Market Explorer** - Panoramic view of the carbon market powered by CarbonPlan OffsetsDB (10,000+ real projects across 5 registries)
- **Advisory Agent** - Get AI-powered pricing and positioning recommendations based on real market data
- **Sales Dashboard** - Track orders, revenue, and tonnage sold

### Platform
- **Agent Decision Explainer** - Full trace of every agent decision with score breakdowns, reasoning steps, and tool calls
- **Double-Entry Ledger** - TigerBeetle distributed ledger for immutable carbon credit accounting
- **Registry Verification** - Automated credit authenticity checks against carbon registries
- **Real Market Data** - Nightly sync with CarbonPlan OffsetsDB covering ACR, ART, CAR, Gold Standard, and Verra

---

## Architecture

```
                    +-----------+
                    |   Kong    |  API Gateway + Phantom Token Auth
                    +-----+-----+
                          |
              +-----------+-----------+
              |                       |
        +-----+-----+          +-----+-----+
        |  React    |          |  FastAPI   |
        |  Frontend |          |  Backend   |
        +-----------+          +-----+-----+
                                     |
              +---------------------+---------------------+
              |                     |                      |
        +-----+-----+        +-----+-----+       +--------+--------+
        | Couchbase  |        |TigerBeetle|       | Pydantic AI     |
        | (Documents)|        | (Ledger)  |       | + LangGraph     |
        +------------+        +-----------+       +---+--------+----+
                                                      |        |
                                              +-------+--+ +---+-------+
                                              |  Claude  | |  Gemini   |
                                              | (Wizard) | |  (Batch)  |
                                              +----------+ +-----------+
```

All services are orchestrated by [Polytope](https://polytope.com), running in Docker containers with hot-reload for development.

---

## Technology Deep Dive

### [Polytope](https://polytope.com) - Container Orchestration & Development
Polytope orchestrates all CarbonBridge services as Docker containers with a single `pt run stack` command. It handles networking, volume mounts, environment variable injection, and hot-reload across the entire stack. During development, Polytope's MCP server integration lets AI coding agents directly inspect containers, execute commands, and manage services - making it our primary development environment.

### [LangGraph](https://langchain-ai.github.io/langgraph/) - Agent State Machines
The buyer wizard agent runs as a LangGraph state machine that manages multi-turn conversation flow across 7 steps. LangGraph gives us deterministic state transitions on top of LLM-driven reasoning: after each agent response, guard rails check whether extracted data warrants advancing to the next step, overriding the model if needed. This ensures the wizard reliably progresses while still feeling natural and conversational.

### [Stripe](https://stripe.com) API & [Stripe Agent Wallet](https://docs.stripe.com/agent-toolkit) - Payments & Autonomous Transactions
Standard buyer checkout uses the [Stripe API](https://docs.stripe.com/api) with Payment Elements for secure card-present transactions. For the autonomous buyer agent, [Stripe Agent Wallet](https://docs.stripe.com/agent-toolkit) enables AI-initiated payments without human intervention - the agent can independently execute purchases within a buyer's configured budget ceiling, with full audit trail and per-transaction caps.

### [TigerBeetle](https://tigerbeetle.com) - Financial Ledger
TigerBeetle serves as our distributed double-entry ledger for carbon credit accounting. Every user has two ledger accounts (pending and settled). When a buyer checks out, credits move to pending; on payment confirmation, they atomically transfer to settled. This provides immutable, auditable financial records with the consistency guarantees that carbon credit trading demands - no double-spending, no phantom credits.

### [Curity](https://curity.io) - Financial-Grade Security
Authentication and authorization use the [Curity Identity Server](https://curity.io/product/identity-server/) implementing the [Phantom Token pattern](https://curity.io/resources/learn/phantom-token-pattern/). The frontend obtains opaque tokens from Curity's token handler; [Kong](https://konghq.com) (API gateway) intercepts requests, exchanges the opaque token for a signed JWT via Curity's introspection endpoint, and forwards verified claims to the backend. This provides financial-grade security without exposing sensitive token content to the browser.

### [Kong](https://konghq.com) - API Gateway
Kong sits in front of all services, handling request routing, Phantom Token exchange with Curity, rate limiting, and CORS. It's the single entry point for the application, ensuring all traffic is authenticated and authorized before reaching the backend.

---

## Built With

**Backend**
- [Python 3.13](https://python.org), [FastAPI](https://fastapi.tiangolo.com), [Uvicorn](https://uvicorn.org)
- [Pydantic AI](https://ai.pydantic.dev) - Structured LLM agent framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) - State machine for multi-turn agent orchestration
- [APScheduler](https://apscheduler.readthedocs.io) - Job scheduling for autonomous agents and data sync

**Frontend**
- [React 19](https://react.dev), [React Router v7](https://reactrouter.com), [TypeScript](https://typescriptlang.org)
- [Tailwind CSS 4](https://tailwindcss.com), [shadcn/ui](https://ui.shadcn.com) ([Radix UI](https://radix-ui.com) primitives)
- [TanStack Query](https://tanstack.com/query) & [TanStack Table](https://tanstack.com/table)
- [GSAP](https://gsap.com) - Animations
- [Stripe Elements](https://docs.stripe.com/payments/elements) - Payment UI

**AI / LLM**
- [Claude](https://anthropic.com) (Anthropic) - Conversational wizard agent
- [Gemini](https://ai.google.dev) (Google) - Autonomous buyer and seller advisory agents
- [LangSmith](https://smith.langchain.com) + [OpenTelemetry](https://opentelemetry.io) - Agent observability and tracing

**Infrastructure**
- [Polytope](https://polytope.com) - Container orchestration and development environment
- [Kong](https://konghq.com) - API gateway with Phantom Token pattern
- [Curity](https://curity.io) - Financial-grade OpenID Connect identity provider

**Databases**
- [Couchbase](https://couchbase.com) - Document store (users, listings, orders, sessions, agent runs)
- [TigerBeetle](https://tigerbeetle.com) - Distributed financial ledger (double-entry carbon credit accounting)

**Payments**
- [Stripe API](https://docs.stripe.com/api) - Payment processing for buyer checkout
- [Stripe Agent Wallet](https://docs.stripe.com/agent-toolkit) - Autonomous agentic transactions for the buyer agent

**Data**
- [CarbonPlan OffsetsDB](https://carbonplan.org/research/offsets-db) - Real-world carbon credit market data (5 registries, 10,000+ projects)

---

## Project Structure

```
carbonbridge/
  models/           # Shared Pydantic data models and DB operations
  services/
    api/            # FastAPI backend (routes, agents, sync jobs)
    web-app/        # React Router frontend
    couchbase/      # Document database
    tigerbeetle/    # Distributed ledger
    curity/         # Identity provider
    kong/           # API gateway
  clients/          # Generated API clients
  config/           # Database schema definitions
  polytope.yml      # Stack orchestration config
```

---

## Getting Started

### Prerequisites
- [Polytope CLI](https://polytope.com) installed
- API keys for Stripe, Google (Gemini), and optionally Anthropic (Claude)

### Running Locally

```bash
# Clone the repository
git clone https://github.com/jellevlieshout/carbonbridge.git
cd carbonbridge

# Start all services via Polytope
pt run stack

# Seed the database with demo data
# (run inside the api container)
python src/seed.py --scenario demo

# Access the app
open http://localhost:8000
```


---

## How It Fits the Track

> *Build a tool that makes AI development more energy-efficient and sustainable.*

CarbonBridge tackles AI sustainability from the demand side. Rather than optimizing model training efficiency directly, we make it trivially easy for AI companies and their infrastructure providers to offset their carbon footprint through the voluntary carbon market.

Our AI agents themselves are designed with efficiency in mind:
- **Dual-model strategy**: Claude (capable but heavier) only for the interactive wizard; Gemini Flash (fast, lightweight) for all batch and autonomous operations
- **Scheduled batch processing**: Autonomous agents run at off-peak hours (2:00 UTC), reducing energy demand during peak grid load
- **Cached market data**: Nightly OffsetsDB sync avoids redundant API calls; pre-computed aggregates eliminate repeated heavy queries
- **Minimal inference**: Deterministic guard rails and pre-checks reduce unnecessary LLM calls; the agent only reasons when it needs to

By lowering the barrier for SMEs to participate in carbon markets, CarbonBridge channels more funding toward verified climate projects - reforestation, renewable energy, methane capture - that directly counterbalance the energy demands of AI infrastructure.

---

## GitHub

[github.com/jellevlieshout/carbonbridge](https://github.com/jellevlieshout/carbonbridge)

---

## License

This project was built during a hackathon. All rights reserved.

---

*Project data sourced from [CarbonPlan OffsetsDB](https://carbonplan.org/research/offsets-db).*
