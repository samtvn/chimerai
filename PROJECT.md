# Chimerai — Wine Sommelier Autonomous Agent

## Project Overview

**Chimerai** is an autonomous agent system designed to help restaurants and wine bars manage their wine inventory, optimize purchasing decisions, and enhance the dining experience through intelligent sommelier assistance.

The system combines computer vision, market intelligence, and agentic AI to automate wine management workflows that traditionally require a human sommelier's expertise and constant manual intervention.

---

## The Problem

Restaurant sommeliers face recurring, time-consuming tasks:

1. **Inventory Management** — Manual tracking of wine stock, valuations, and cellar balance
2. **Purchasing Decisions** — Identifying which bottles to restock, finding the best market prices, and managing supplier relationships
3. **Wine List Optimization** — Ensuring the wine menu is balanced across regions, price points, and pairings; keeping descriptions current as inventory changes
4. **Sales Analysis** — Understanding which wines sell well, which pairings resonate with guests, and profitability per bottle
5. **Alerts & Risk Mitigation** — Catching depleted stock, identifying wines approaching their optimal drinking window, and flagging market opportunities

Today, these tasks are either:
- Done manually (error-prone, time-consuming)
- Done with disconnected spreadsheets (hard to maintain, no real-time sync)
- Partially handled by generic POS systems (limited intelligence)

---

## The Solution: Autonomous Agent

Chimerai introduces an **autonomous agent** that continuously monitors the wine inventory and proactively handles the workflows above. The agent doesn't just answer questions — it observes changes in real time, reasons about their implications, and takes actions autonomously.

### Key Workflows

#### 1. **Inventory Update → Autonomous Rebalancing**

```
Sommelier updates inventory:
  "1 bottle of Lynch-Bages 2018 sold during service"
    ↓
FastAPI validates & persists to database
    ↓
Agent Orchestrator detects the change
    ↓ THOUGHT: "Inventory changed. I should audit the cellar."
    ↓
INVENTORY AUDIT TOOL
  - Analyzes cellar balance across regions, price points, vintages
  - OBSERVATION: "Bordeaux stock down to 12%. No premium Left Bank currently available.
                   Wine list is becoming overly Rhône/Burgundy dominated."
    ↓ THOUGHT: "This imbalance may affect the wine program. I should check sales data."
    ↓
SALES ANALYSIS TOOL
  - Queries sales history for Lynch-Bages performance
  - OBSERVATION: "Lynch-Bages sold 14 bottles in last 60 days.
                   Frequently recommended with ribeye and lamb.
                   High average margin. Strong sommelier recommendation frequency."
    ↓ THOUGHT: "This wine is commercially important. I should research restocking options."
    ↓
PURCHASE AGENT TOOL
  - Queries distributor APIs for market price
  - Analyzes margins and alternatives
  - OBSERVATION: "Current market price €145. Best distributor: €138.
                   Alternative: Château Pontet-Canet 2019 (better value).
                   Resale margin strong on both."
    ↓ THOUGHT: "The wine menu must be updated. I should regenerate it."
    ↓
WINE MENU GENERATOR TOOL
  - Removes Lynch-Bages from active list
  - Inserts Pontet-Canet as replacement
  - Generates new tasting descriptions via LLM
  - Updates food pairing suggestions
  - OBSERVATION: "Wine menu regenerated. 47 bottles active. New descriptions committed."
    ↓
FINAL OUTPUT (presented to sommelier):
  ✓ Inventory updated (1 bottle sold)
  ✓ Cellar rebalanced (detected Bordeaux gap)
  ✓ Buy recommendation: Pontet-Canet 2019 @ €138 (12-bottle lot suggested)
  ✓ Wine menu refreshed (new pairings live)
  ✓ Alerts: Lynch-Bages stock at 0. Recommend restocking Lynch-Bages or Pontet-Canet.
```

#### 2. **Photo-Based Wine Identification & Valuation**

```
Sommelier uploads a bottle photo or scans a barcode:
    ↓
OCR / LABEL RECOGNITION AGENT
  - Extracts wine name, vintage, domain, region from image
  - Queries wine database (Vivino API or custom)
  - OBSERVATION: "Identified: Château Lynch-Bages 2018, Pauillac, Bordeaux.
                   Current market price: €145–160. Critic score: 94 points."
    ↓
WINE VALUATION AGENT
  - Calculates cellar value at current market rates
  - Estimates optimal drinking window (age analysis)
  - Flags underperforming investments vs. market trends
  - OBSERVATION: "Lynch-Bages 2018: Estimated value €150. Peak drinking: 2026–2035.
                   Recommend selling if price peaks before 2026 (current high market demand)."
    ↓
FINAL OUTPUT:
  ✓ Wine identified with confidence
  ✓ Current market value + recommendation (hold/sell/drink)
  ✓ Tasting notes and pairing suggestions ready for the wine list
```

#### 3. **Guest-Specific Wine Recommendations**

```
Guest arrives. Sommelier inputs:
  - Guest preferences (past purchases, described tastes)
  - Dish they've ordered
  - Budget constraints
    ↓
RECOMMENDATION ENGINE AGENT
  - Queries inventory + sales history
  - Analyzes guest profile against past successful pairings
  - Cross-references dish with restaurant's pairing notes
  - Ranks wine suggestions by margin + likelihood of satisfaction
  - OBSERVATION: "Guest ordered ribeye, budget €40–70, prefers bold reds with structure.
                   Ranked: 1) Hermitage 2019 €65 (97% satisfaction), 2) Côtes du Rhône €45 (88%)."
    ↓
FINAL OUTPUT:
  ✓ Top 3 recommendations with tasting notes
  ✓ Margin transparency (for sommelier incentives)
  ✓ Quick links to refill the inventory for bestsellers
```

---

## Agent Architecture

### Design Philosophy

Chimerai is **genuinely agentic**, not a linear automation pipeline. The distinction matters:

| | Automation | Chimerai |
|---|---|---|
| Steps always run | Yes | No — LLM decides |
| Branches on findings | No | Yes |
| Can stop early | Yes (short-circuit) | Yes (reasoned) |
| Fires without user | No | Yes (threshold watcher) |

The orchestrator uses LLM reasoning (ReAct pattern) to decide what to do next based on observations — it does not follow a hardcoded sequence. The same trigger can produce different outcomes depending on what the agent finds.

---

### Structure

```
Orchestrator (ReAct loop, Gemini Flash)
  ├── Inventory Audit Agent
  │     ├── tool: get_inventory()
  │     ├── tool: evaluate_diversity()
  │     └── tool: flag_low_stock()
  ├── Sales Analysis Agent
  │     ├── tool: get_sales_history()
  │     └── tool: get_top_wines()
  ├── Purchase Agent
  │     └── tool: get_mock_distributor_prices()
  └── Menu Generator Agent
        ├── tool: get_current_menu()
        └── tool: update_menu()
```

Each sub-agent is a **LangGraph subgraph** with its own ReAct loop and dedicated tools. The orchestrator calls sub-agents and reasons about their observations to decide next steps.

Sub-agents run **sequentially** (not in parallel) — this keeps the demo reliable and the reasoning trace readable.

---

### Triggers

Two triggers fire the orchestrator:

1. **User action** — sommelier logs a sale or inventory change via the UI → FastAPI emits an event → orchestrator starts immediately. This is the primary demo moment.
2. **Low-stock threshold watcher** — a background task monitors inventory; when any wine hits ≤ 2 bottles, the orchestrator fires automatically without user action. This demonstrates proactive autonomy.

No scheduled/cron tasks for the hackathon — mentioned in presentation as a natural production extension.

---

### Conditional Branching (what makes it agentic)

The orchestrator always starts with Inventory Audit. What happens next depends on its findings:

**Case A — Everything is fine:**
```
Inventory Audit → "Cellar balanced, no low stock"
Orchestrator → "No action needed"
DONE (1 sub-agent ran)
```

**Case B — Imbalance or low stock detected:**
```
Inventory Audit → "Bordeaux at 12%, Lynch-Bages stock at 0"
Orchestrator → "Gap detected, checking sales before recommending restock"
Sales Analysis → "Lynch-Bages sold 14 bottles in 60 days, high margin"
Orchestrator → "Restock makes commercial sense, finding best price"
Purchase Agent → "Pontet-Canet 2019 @ €138 — good alternative"
Menu Generator → updates wine list, generates new descriptions
DONE (all sub-agents ran)
```

**Case C — Low stock but no good replacement:**
```
Inventory Audit → "Grower Champagne stock at 1 bottle"
Sales Analysis → "Slow seller, low margin"
Orchestrator → "Not worth restocking, skip purchase — alert sommelier instead"
Skips Purchase Agent and Menu Generator
Emits alert
DONE (reasoned early exit)
```

The LLM decides these branches — not hardcoded `if/else` logic.

---

### SSE Stream Events

All agent activity is streamed to the frontend via Server-Sent Events. Each event is a flat object:

```ts
type AgentEvent = {
  source: "orchestrator" | "inventory_audit" | "sales_analysis" | "purchase_agent" | "menu_generator"
  type: "thought" | "action" | "observation" | "final" | "alert"
  message: string
  timestamp: string
}
```

The frontend renders these in a chronological feed with color-coded source labels. The navbar shows the currently active agent name.

---

## Technical Architecture

### Frontend (SvelteKit)

Structured UI for:
- **Dashboard** — KPIs (cellar value, total bottles, active alerts), region balance chart, agent activity stream
- **Inventory Management** — Wine table (add/remove/edit), search/filter by region/vintage, quick stock status
- **Wine Menu** — Auto-generated wine card with descriptions and pairings
- **Purchase Recommendations** — Agent-suggested restocks with distributor pricing and margins
- **Agents** — Live status of orchestrator and each sub-agent (idle/running/error)

**Stack:** SvelteKit (Svelte 5 runes), Tailwind CSS v4, DaisyUI v5, structured UI (not chat-based)

### Backend (FastAPI + LangGraph)

Stateless API handling:
- Inventory CRUD endpoints
- Event emission for agent orchestration (when wine is added/removed/sold)
- Background task: low-stock threshold watcher
- SSE endpoint streaming agent events to frontend
- Database integration (PostgreSQL, async SQLAlchemy via SQLModel)
- LLM integration (Gemini Flash via LangChain) for agentic reasoning

**Agent Loop (LangGraph):**
- **Pattern**: ReAct (Reason → Action → Observe → Loop) at both orchestrator and sub-agent level
- **Sub-agents**: Inventory Audit, Sales Analysis, Purchase Agent, Menu Generator
- **LLM**: Gemini Flash (fast, cost-effective inference ~100ms)
- **Execution**: Sequential sub-agents, orchestrator decides which to invoke based on LLM reasoning

**Stack:** FastAPI, SQLModel (async SQLAlchemy), psycopg (PostgreSQL driver), LangGraph + LangChain, Gemini via Google GenAI

### Database (PostgreSQL)

Schema:
- `wines` — inventory table (id, name, vintage, region, quantity, purchase_price, market_price, rating, drinking_window, etc.)
- `sales` — transaction log (wine_id, quantity, timestamp, guest_id, dish_id, margin)
- `pairings` — dish ↔ wine recommendations (dish_id, wine_id, success_rate)
- `menu_items` — current wine list (wine_id, description, pairing_notes, position_on_card)
- `agents_logs` — audit trail of agent actions (agent_name, action_type, input, output, timestamp)

---

## Project Goals (Hackathon Context)

**Evaluation Criteria from Devoteam:**

1. **Innovation & Creativity** ✅
   - Novel agentic workflow: autonomous sommelier assistant that actively manages wine inventory, not just recommends
   - Exploits LLM reasoning to chain tools (inventory audit → sales analysis → purchase recommendation)

2. **Impact & Utility** ✅
   - Real problem: restaurants waste time on wine management
   - Tangible value: reduces manual work, optimizes purchasing, improves profitability

3. **Technical Execution** ✅
   - Clean architecture: frontend/backend separation, clear agent tool boundaries
   - Production-grade stack: async DB access, proper error handling, rate limiting (future)
   - Uses professional tools (LangGraph, Gemini, PostgreSQL)

4. **UX/UI** ✅
   - Structured UI (not generic chatbot) — sommelier-specific workflows
   - Live agent reasoning stream — transparency into what the agent is thinking/doing
   - Accessible design (DaisyUI + accessible form inputs)

5. **Presentation & Storytelling** ✅
   - Live demo: "Bottle sold → watch the agent automatically detect imbalance, research replacements, update the wine menu"
   - Business narrative: relevant to Devoteam's consulting clients (hospitality, luxury, retail)
   - Clear ROI messaging: time savings, margin optimization, better guest experience

---

## MVP Scope (12 Days Remaining)

**Week 1: Core Infrastructure**
- [ ] Frontend: Dashboard + Inventory pages (UI shell)
- [ ] Backend: Database schema, basic CRUD endpoints
- [ ] LangGraph: Orchestrator skeleton, tool definitions

**Week 2: Agent Loop**
- [ ] Inventory Audit tool
- [ ] Sales Analysis tool
- [ ] Purchase Agent tool (mock distributor API)
- [ ] Menu Generator tool (basic text generation)
- [ ] SSE stream to frontend (agent THOUGHT/OBSERVATION/ACTION visible in real time)

**Week 3 (Days 15–20): Polish & Demo**
- [ ] End-to-end workflow test (add wine → observe agent reasoning → see results)
- [ ] UI refinement (warm earthy design, responsive)
- [ ] Demo data & scripts
- [ ] Presentation deck + walkthrough script

**Out of Scope (Post-Hackathon):**
- OCR label recognition (hard to demo convincingly; stub with manual wine selection)
- Real distributor API integration (mock data + mock API)
- Pairing Engine ML model (simple rule-based heuristics for now)
- Production DevOps (no K8s, no monitoring — local Docker only)

---

## Team & Responsibilities

**Team:** 3 people
- **Frontend Lead** — SvelteKit dashboard, UI components, SSE stream display
- **Backend Lead** — FastAPI, database schema, LangGraph orchestrator, tool implementations
- **Full-Stack / DevOps** — Monorepo setup, deployment scripts, demo environment, presentation

---

## How to Run (Local Dev)

### Prerequisites

- Python 3.13+
- Node 18+ (pnpm 10.32.1)
- Docker Desktop (for PostgreSQL)

### Setup

```bash
# Clone and enter repo
cd chimerai

# Start database
pnpm db:up

# Install Python deps
uv sync

# Install Node deps
pnpm install

# Generate auth schema (SvelteKit)
pnpm --filter web auth:schema

# Set env vars
cp apps/web/.env.example apps/web/.env
cp apps/api/.env.example apps/api/.env

# Edit .env files with:
# DATABASE_URL=postgres://chimerai:chimerai@localhost:5432/chimerai
# ORIGIN=http://localhost:5173
# BETTER_AUTH_SECRET=<generate a 32-char secret>
# GOOGLE_API_KEY=<get from Google Cloud>

# Run both apps
pnpm dev
```

Frontend: http://localhost:5173  
Backend API: http://localhost:8000  
API Docs: http://localhost:8000/docs

### Common Commands

```bash
# Frontend only
pnpm dev:web

# Backend only
pnpm dev:api

# Typecheck
pnpm run typecheck

# Database
pnpm db:up / pnpm db:down

# Add Python dep
uv add --project apps/api <package>

# Add Node dep (frontend)
pnpm add -F web <package>
```

---

## Key Decisions & Rationale

| Decision | Rationale |
|----------|-----------|
| **SvelteKit (not React)** | Smaller bundle, faster dev, Svelte 5 runes are elegant for this UI |
| **Tailwind v4 + DaisyUI v5** | Fast styling, pre-built components, warm aesthetic suits wine domain |
| **FastAPI (not Django)** | Lightweight, async-first, excellent for agent loops + LLM calls |
| **LangGraph (not custom agent loop)** | Battle-tested ReAct pattern, built for tool-use workflows, easy to debug |
| **Gemini Flash 3.1 (not Claude/GPT-4)** | Fast inference (~100ms), low cost, sufficient reasoning for sommelier tasks |
| **PostgreSQL + SQLModel** | Relational queries (sales trends, pairing analysis), async-friendly, JSON support for flexible schemas |
| **SSE for agent stream** | Real-time transparency into agent reasoning; simpler than WebSockets for one-way push |
| **Monorepo (pnpm + uv)** | Shared types package, clear separation of concerns, parallel dev/CI possible |

---

## Success Criteria (Demo Day)

**Technical:**
- [ ] Full workflow executes end-to-end without errors (add wine → agent reasons → menu updates)
- [ ] Agent reasoning visible in UI (THOUGHT/OBSERVATION/ACTION stream)
- [ ] Database persists state correctly

**UX/Demo:**
- [ ] Dashboard loads quickly, is visually polished, navigation is intuitive
- [ ] Sommelier can see wine inventory and agent alerts at a glance
- [ ] Demo script walks from inventory change → automatic rebalancing → results visible in UI

**Business:**
- [ ] Clear narrative: what problem does this solve? Who benefits? What's the ROI?
- [ ] Jury understands the **agentic** nature — this is not a chatbot, it's an autonomous assistant

---

## Resources & References

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SvelteKit Docs**: https://kit.svelte.dev/docs
- **DaisyUI Docs**: https://daisyui.com/
- **Devoteam Hackathon Brief**: (original prompt provided by organizers)

---

## Contact & Notes

- **Hackathon:** Devoteam Agentic AI Hackathon
- **Duration:** 20 days (12 remaining at project kickoff)
- **Repository:** https://github.com/samtvn/chimerai
- **Demo Environment:** Local dev stack (Docker + pnpm + uv)

---

**Last Updated:** May 16, 2026
