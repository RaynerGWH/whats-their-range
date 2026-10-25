# What's Their Range?

A poker environment for building and evaluating an agent harness against other LLM players.

<picture>
  <source media="(prefers-color-scheme: light)" srcset="docs/images/table-light.png">
  <img src="docs/images/table-dark.png" alt="Six-seat poker replay with a terminal-style table, public chat, player decision, action history and standings." width="1440">
</picture>

*The current UI in replay and spectator inspection mode. The game state is recorded from the real engine; model decisions, messages and usage in this preview are mocked. Both dark and light themes are supported.*

The goal is to develop a harness that helps an LLM win more against other LLM poker players. We want to test whether better memory, poker tools and decision workflows improve tournament returns under controlled comparisons. Public table talk gives players another way to make claims, bluff and potentially influence one another.

The table environment is implemented. The stronger hero strategy is currently being designed with the project owner and will be a separate change. Improved playing strength has not yet been demonstrated.

## Current baseline

- **Six seats:** five LLM opponents and a hero you can control manually, choosing legal actions and optional messages. Switch the hero to LLM control for six automated players.
- **Neutral opponents:** each receives the same task and rules, its own permitted game context, recent public chat and bounded private memory. One OpenRouter call selects each automated action. Models are configurable per seat; tactical styles and bluffing are left to the model.
- **Inspectable play:** board and players beside an internally scrolling chat panel, with decisions, evidence, raw inputs, traces, history and standings below. Replay preserves the information visible at each recorded point.
- **Independent tables:** PokerKit owns game rules and legal execution, with a separate worker process for each table. Model contexts and private memories stay isolated per seat.
- **Offline comparison modes:** native PokerTH engine 4 opponents and legacy heuristics remain available, including a heuristic hero that requires no model calls.

The [integration review](docs/review/llm-table-integration.md) records 160 passing backend tests, one optional database test skipped, 48 passing frontend tests, and successful TypeScript/build checks. Provider calls were mocked. Real-model behavior and competitive performance remain to be evaluated. The earlier PokerTH checkpoint is tagged `baseline/stage-2a`, and the first integrated LLM environment/UI checkpoint is tagged `baseline/llm-table`.

## Harness strategy in design

The LLM will own the final poker decision. The proposed harness uses a bounded LangGraph loop to retrieve evidence, request calculations, compare hypotheses and reconsider a spot before acting. The design covers:

- Detailed action and conversation histories, categorized situations and evolving opponent profiles, with supporting hands, contradictions and unknown outcomes retained.
- Cached player reads and targeted retrieval, updated as relevant new evidence arrives rather than repeatedly analyzing the entire history.
- Position, betting lines, board texture, hand ranges, blockers, stack exposure and plans across streets.
- Value extraction, thin value, bluff construction, defensive decisions and sizing under explicit opponent-response assumptions.
- Table talk, our perceived image and how opponents adapt, while treating public claims as uncertain game data.
- Qualified solver/reference use where a result applies, and evidence-based exploitative adjustments. There is no fixed GTO/context percentage or forced bluff quota.
- Same-model comparisons and component-removal experiments to investigate whether the harness actually improves tournament returns, with inference cost, failures and uncertainty reported.

The richer tool loop, searchable categorical memory and solver integration are **not implemented in this baseline**. No solver has been selected. Qualitative reads and proposed tools remain design work, as described in the [harness plan](docs/llm-agent-harness.md) and [agent direction](docs/agent-direction.md).

## Project direction

Before starting or resuming project work, read [shared context access](docs/shared-context.md). It points every local worktree to the same live project brief, decision log and agent direction. That brief separates agreed goals, proposed work and verified implementation. The sections below describe the runnable baseline.

## Run locally

Requires Node 22+, Python 3.11+ and a C++20 compiler (Clang or GCC). Use `uv` for the Python environment.

```sh
npm install
python3 scripts/build_pokerth.py
cd apps/api
cp .env.example .env
uv sync --extra test
uv run uvicorn wtr.main:app --host 127.0.0.1 --port 8000
```

In another terminal, from the repository root:

```sh
npm run dev
```

Open [the local app](http://localhost:5173). Create a tournament and press **Run table**. Tables start paused. **Step** advances one action, or deals the next hand after settlement. Two tables can run concurrently in separate processes. Closing the browser does not stop them while the API stays running.

With OpenRouter configured and the new capabilities available, the UI defaults to six LLM seats with manual hero control. Without credentials, PokerTH remains the runnable default; Legacy heuristic is also explicit. Missing native builds produce a PokerTH setup error. Older clients that omit the opponent field retain legacy mode.

No credentials are required for the heuristic hero. It uses SQLite locally and does not make model calls. Deck, hero policy, opponent policy and private personality assignment randomness are separate. API controller fields `hero_seed`, `opponent_seed` and `personality_seed` can reproduce a run; omitted seeds are independently generated and saved in the spectator configuration, outside player observations.

## OpenRouter agent

Set these in `apps/api/.env`, restart the backend, then create an LLM table:

```dotenv
OPENROUTER_API_KEY=your-server-side-key
OPENROUTER_MODEL=provider/model-id
```

Choose models supporting the structured JSON parameters requested by the adapter. Use a default model or per-seat overrides. The initial `free_play` instructions supply the objective, rules and optional chat without prescribing tactics or bluff frequency. Each automated turn makes one bounded model call using the acting seat's permitted observation, own memory and public chat. Manual turns wait for a selected legal action and optional message, with no hero call or timeout action. The saved opponent preset remains unchanged when the hero switches control.

Per-seat and total-table call/output limits, deadlines and message limits are available through `llm_limits` and `/api/config`. Invalid responses, provider errors and exhausted budgets produce a visibly labeled heuristic fallback without invented chat. Pause, stop and takeover cancel pending work and prevent obsolete results from applying. Started attempts still count. Call/output caps are not a dollar limit; configure account spending limits separately.

The older hero-only OpenRouter option with PokerTH/legacy opponents still uses the fixed assessment/retrieval graph and `AGENT_DEADLINE_SECONDS` / `AGENT_MAX_CALLS`. Neither path implements the future model-directed strategy harness or solver. No paid provider calls were made during baseline verification.

For a completely offline walkthrough of the combined UI and worker flow, use the explicitly mocked [integration preview](docs/review/llm-table-integration.md#reproduce-the-offline-browser-check). It does not demonstrate real-model poker behavior.

## What is implemented

- Six-seat LLM tables, manual hero action/chat entry, LLM takeover, stable neutral opponent presets, isolated per-seat memory and public table talk. Four seats are also supported.
- Dark/light terminal workspace, capability-aware configuration, per-seat trace selection and explicit play/spectator views.
- Bounded [LLM benchmark runner](docs/llm-benchmark.md), using the same game/player path, seat rotation, held-out configuration, and retained failure/usage records. Mock reports are engineering evidence only.
- React/TypeScript/Vite spectator UI, responsive table, hidden-card toggle, pause/run/step/speed, two independent sessions, archive and replay.
- PokerKit dealing, arbitrary legal chip accounting within a discrete agent action menu, all-ins, side pots, eliminations, heads-up seating and payout settlement.
- Real native PokerTH engine 4 opponents, legal action normalization, public behavioral statistics and private shuffled personalities, with legacy heuristic comparison mode. Opponent parameters and seeds are never sent to the hero.
- Private observations for the hero, descriptive action counts, bounded evidence, state-version validation, structured OpenRouter adapter and local decision records.
- Fixed LangGraph orchestration for the older hero-only path, with optional LangSmith tracing (`LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`). The new per-seat LLM path makes one direct bounded call. Model traces contain only the acting player's permitted observation, not the spectator snapshot.
- SQLAlchemy persistence: SQLite locally, PostgreSQL via `DATABASE_URL`, including Supabase session-pooler URLs.
- Descriptive ICM prize-equity display based on hand-start or settled stacks, in 100 prize units. Prize structure is configurable as 70/30 or winner-take-all.

## Scope and limitations

This is an **experimental baseline, not a GTO or ICM strategy solver**. Equity assumes uniform random opponent hands and does not infer ranges. Pot odds are an approximate reference and do not model side-pot eligibility. The ICM display does not drive a solved action-value policy. No solver datasets are bundled.

The planned competing-hypothesis analyses, future-street search, calibrated opponent beliefs and robust exploitation are future strategy work. Every action is recorded, including after hero folds, but off-turn LLM deliberation is not implemented. The old hero graph has parallel calculation/retrieval; the new per-seat baseline uses one direct model decision. Neither path has multiple LLM analysts or a model-directed tool loop.

PokerTH and legacy heuristic opponents have stable biases and use current hand strength, pot and stacks. They are not validated human models or ICM-aware tournament professionals. Neutral LLM opponents receive permitted game context and choose their own actions; their poker behavior remains unverified with real models. Blinds increase by 1.5x every configured number of hands; there are no antes or re-entries. The simulator permits any number of contenders from six down to one.

Replay stores full spectator snapshots, including private cards, and must remain behind access control. It stores the last 120 public events in each snapshot plus full current-hand context for decisions. APIs page through older snapshots. This is deliberately simple and will need retention and normalized event storage for long-term scale.

On API restart, unfinished sessions are archived as interrupted. Replay survives; resuming their engine state is not yet supported. Pause and stop cancel in-flight policy work, preserving a cancelled trace and preventing that result from changing the game. A single backend host/process owns the workers; do not run multiple Uvicorn workers or scale replicas without introducing a table-ownership mechanism.

## Deployment preparation

Templates are included; nothing is deployed automatically.

- **Supabase:** set `DATABASE_URL` to a server-side PostgreSQL connection (`postgresql+psycopg://...`, with `sslmode=require`). Prefer the session pooler for this persistent service. The backend creates its tables and enables RLS on PostgreSQL; no browser policies are granted. Connect as the owner/backend role. Supabase Auth and per-user authorization are not yet integrated.
- **Fly.io:** use repository-root build context with `apps/api/fly.toml`, review app name/region, and set `DATABASE_URL`, `CONTROL_TOKEN`, `ALLOWED_ORIGINS` and optional provider/tracing secrets. The template requires a control token and keeps the machine awake for running tournaments. Use one machine and one Uvicorn worker. SQLite on ephemeral deployment storage is not durable.
- **Vercel:** set root directory to `apps/web`; set `VITE_API_URL` to the API's HTTPS origin. Add the exact Vercel origin to backend `ALLOWED_ORIGINS`. Enter `CONTROL_TOKEN` in the dashboard's Connections panel. Never place provider keys or database credentials in `VITE_*` variables.

The shared access token is a development deployment gate, not a multi-user auth system. Local default binding is loopback. `WTR_PUBLIC=true` refuses startup without a token.

## Checks

```sh
python3 scripts/build_pokerth.py
npm run check
npm run test -w apps/web
npm run build
cd apps/api
uv run pytest
```

Tests cover complete seeded tournaments and chip conservation, payout settlement, heads-up order, private observations, stale/illegal actions, provider response validation, deadlines, budgets, independent table processes, replay persistence and access control. OpenRouter calls are mocked; hosted Supabase and LangSmith require your credentials for end-to-end verification.

See [architecture](docs/architecture.md) for the boundaries to preserve while iterating.

## PokerTH source and license

The pinned opponent core is vendored with its AGPL-3.0-or-later license and original notices. See [native setup and source obligations](native/pokerth/README.md) and [Stage 2A delivery](docs/stage-2a.md). The bridge preserves the upstream decision logic, but uses separate seeded randomness and maps sizing to our discrete legal menu. It is not a solver or a verified human model.
