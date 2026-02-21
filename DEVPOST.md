# DevPost Submission - CarbonBridge

---

## Elevator Pitch (200 chars max)

AI agents that autonomously trade carbon credits for SMEs - turning the voluntary carbon market from an impenetrable maze into a hands-free climate action tool.

(157 characters)

---

## About the Project

### Inspiration

It started with a conversation about EV chargers. We learned that smaller companies installing EV charging stations earn carbon credits - but have absolutely no practical way to sell them. The voluntary carbon market is dominated by large brokers and opaque platforms designed for enterprises with dedicated sustainability teams.

When we dug into existing carbon credit marketplaces, we found a massive vacuum: SMEs on both sides of the market - sellers with credits they can't monetize and buyers who want to offset but don't know where to start - are completely underserved. The terminology is confusing, the registries are fragmented across Verra, Gold Standard, ACR, and others, and pricing is a black box.

We asked ourselves: what if AI agents could simply handle all of this? What if a buyer could describe their company in plain English and have an agent estimate their footprint, find matching credits, and purchase them - all in one conversation? What if that agent could then keep doing it autonomously, every month, within a set budget?

That's how CarbonBridge was born: an agent-first carbon credit exchange where AI does the brokering.

### What We Learned

- The voluntary carbon credit market is surprisingly fragmented - five major registries, dozens of project types, and no standardized pricing. We integrated CarbonPlan's OffsetsDB (10,000+ real projects) to ground our agents in actual market data rather than hallucinated numbers.
- Multi-turn conversational agents are hard to get right. We built a LangGraph state machine with deterministic guard rails on top of Pydantic AI to prevent the wizard from going off-track, while still feeling natural.
- Choosing the right model for the right task matters enormously. Claude excels at warm, conversational guidance (our wizard), while Gemini Flash is perfect for fast, cheap batch operations (autonomous purchasing, seller advisory). Using both keeps costs down and quality up.
- Agent explainability isn't optional - it's the feature. Buyers trusting an AI to spend their money need to see exactly why it chose a specific listing. Our Decision Explainer with full score breakdowns and reasoning traces turned out to be one of the most compelling parts of the demo.
- Financial-grade atomicity matters even in a hackathon. We used Couchbase sub-document mutations and TigerBeetle's distributed ledger to prevent double-selling credits under concurrent checkout - a real problem in carbon markets.

### How We Built It

CarbonBridge runs as a microservice architecture orchestrated by [Polytope](https://polytope.com), which manages all our Docker containers, networking, and hot-reload with a single command. Polytope's MCP server integration also served as our AI-assisted development environment, letting coding agents directly inspect and manage running services.

**Three AI Agents ([Pydantic AI](https://ai.pydantic.dev) + [LangGraph](https://langchain-ai.github.io/langgraph/)):**
1. A conversational **Buyer Wizard** (Claude) orchestrated by a [LangGraph](https://langchain-ai.github.io/langgraph/) state machine - manages multi-turn conversation flow across 7 steps with deterministic guard rails that override the LLM when extracted data warrants step progression. Streamed via SSE for real-time chat.
2. An **Autonomous Buyer Agent** (Gemini Flash) that runs on a schedule, searching, scoring, and purchasing credits matching a buyer's saved criteria. Executes payments autonomously via [Stripe Agent Wallet](https://docs.stripe.com/agent-toolkit) with per-transaction caps and budget ceilings.
3. A **Seller Advisory Agent** (Gemini Flash) that analyzes market conditions and provides pricing and positioning recommendations grounded in real OffsetsDB data.

**Backend:** [FastAPI](https://fastapi.tiangolo.com) (Python 3.13) with LangGraph for multi-turn state management, APScheduler for autonomous agent scheduling, and a fake registry API for credit verification demos.

**Payments:** The [Stripe API](https://docs.stripe.com/api) handles standard buyer checkout via Payment Elements. For the autonomous buyer agent, [Stripe Agent Wallet](https://docs.stripe.com/agent-toolkit) enables AI-initiated transactions without human intervention - the agent independently executes purchases within configured budget limits, with full audit trail.

**Frontend:** React 19 with React Router v7, Tailwind CSS, shadcn/ui components, and custom SSE streaming hooks for real-time agent interaction. [Stripe Elements](https://docs.stripe.com/payments/elements) for payment.

**Data Layer:** [Couchbase](https://couchbase.com) for document storage (users, listings, orders, agent runs with full decision traces). [TigerBeetle](https://tigerbeetle.com) as a distributed double-entry financial ledger for carbon credit accounting - each user has pending and settled accounts, with atomic transfers on payment confirmation. This gives us immutable, auditable records with the consistency guarantees that carbon credit trading demands.

**Auth & Security:** [Curity Identity Server](https://curity.io) provides financial-grade authentication via the [Phantom Token pattern](https://curity.io/resources/learn/phantom-token-pattern/). [Kong API Gateway](https://konghq.com) intercepts all requests, exchanges opaque tokens for signed JWTs via Curity's introspection endpoint, and forwards verified claims to the backend. Sensitive token content never reaches the browser.

**Market Data:** Nightly sync with [CarbonPlan OffsetsDB](https://carbonplan.org/research/offsets-db) (10,000+ real projects across 5 registries) grounds all agent recommendations in actual market data.

### Challenges We Faced

- **Agent determinism vs. flexibility:** The wizard agent needs to feel conversational but also reliably advance through steps. We solved this with a [LangGraph](https://langchain-ai.github.io/langgraph/) state machine that applies deterministic guard rails post-LLM - if the data indicates progression, we force the step transition regardless of what the model says.
- **Autonomous payments without humans in the loop:** Letting an AI agent spend real money requires serious guardrails. [Stripe Agent Wallet](https://docs.stripe.com/agent-toolkit) gave us the foundation for autonomous agentic transactions, but we still had to layer on per-transaction caps, monthly budget ceilings, and idempotency checks to prevent duplicate purchases if the scheduler fires twice.
- **Concurrent quantity management:** When multiple buyers check out simultaneously, credits can be oversold. We implemented atomic sub-document mutations in [Couchbase](https://couchbase.com) to reserve quantities at checkout and release them on timeout - no race conditions. [TigerBeetle](https://tigerbeetle.com)'s double-entry ledger ensures the financial side is equally bulletproof.
- **SSE streaming through Phantom Token auth:** Standard EventSource doesn't support custom headers, but [Curity](https://curity.io)'s Phantom Token pattern (via [Kong](https://konghq.com)) requires an Authorization header on every request. We built a custom streaming hook using fetch + ReadableStream instead.
- **Grounding agents in real data:** LLMs love to make up numbers. We integrated [CarbonPlan's OffsetsDB](https://carbonplan.org/research/offsets-db) (synced nightly, 10,000+ projects) so agents reference real market prices, project types, and registry distributions when making recommendations.
- **Balancing model cost vs. quality:** Running Claude for every agent operation would be expensive. We split across two models - Claude for the high-touch wizard experience, Gemini Flash for batch operations - keeping the total inference cost manageable for a marketplace that needs to scale.

---

## Built With

- [Python](https://python.org)
- [TypeScript](https://typescriptlang.org)
- [FastAPI](https://fastapi.tiangolo.com)
- [React](https://react.dev)
- [React Router](https://reactrouter.com)
- [Tailwind CSS](https://tailwindcss.com)
- [Pydantic AI](https://ai.pydantic.dev)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Claude (Anthropic)](https://anthropic.com)
- [Gemini (Google)](https://ai.google.dev)
- [LangSmith](https://smith.langchain.com)
- [OpenTelemetry](https://opentelemetry.io)
- [Couchbase](https://couchbase.com)
- [TigerBeetle](https://tigerbeetle.com)
- [Stripe API](https://docs.stripe.com/api)
- [Stripe Agent Wallet](https://docs.stripe.com/agent-toolkit)
- [Kong](https://konghq.com)
- [Curity](https://curity.io)
- [Polytope](https://polytope.com)
- [Docker](https://docker.com)
- [Vite](https://vite.dev)
- [Radix UI](https://radix-ui.com)
- [TanStack Query](https://tanstack.com/query)
- [CarbonPlan OffsetsDB](https://carbonplan.org/research/offsets-db)

---

## GitHub Link

https://github.com/jellevlieshout/carbonbridge

---

## How Our Project Fits the Track

> **Track:** Build a tool that makes AI development more energy-efficient and sustainable.

CarbonBridge attacks AI sustainability from the demand side of the carbon equation. While Crusoe and others optimize the supply side (cleaner energy for data centres), we make it trivially easy for the companies *using* AI infrastructure to offset their carbon footprint through the voluntary carbon market.

**Direct track alignment:**

1. **Making carbon offsetting accessible to AI companies of all sizes.** Training a frontier model consumes as much electricity as a small town uses in a year - but offsetting that footprint through the voluntary carbon market currently requires enterprise-scale sustainability teams. CarbonBridge's AI agents reduce this to a single conversation or a fully autonomous monthly purchase.

2. **Energy-efficient AI by design.** Our agents themselves demonstrate efficient AI development:
   - **Right-sized models**: Claude only where conversational quality matters (wizard); Gemini Flash for all batch operations (10x cheaper, faster)
   - **Scheduled off-peak processing**: Autonomous agents run at 2:00 UTC to reduce peak grid demand
   - **Cached intelligence**: Nightly OffsetsDB sync and pre-computed aggregates eliminate redundant API calls and repeated heavy computation
   - **Deterministic guard rails**: Pre-checks and state machines reduce unnecessary LLM inference - the agent only reasons when it genuinely needs to

3. **Scaling climate finance.** By lowering the barrier for SMEs to participate in carbon markets, CarbonBridge channels more funding toward verified climate projects - reforestation, renewable energy, methane capture, clean cookstoves - that directly counterbalance the growing energy demands of AI infrastructure. As data centre energy demands double by 2030, the voluntary carbon market needs to scale with it. CarbonBridge makes that possible.

In short: we're building the financial infrastructure that lets the AI industry take responsibility for its energy footprint, powered by AI agents that are themselves designed to be lean and efficient.
