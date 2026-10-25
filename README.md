# What's Their Range?

A local NLH tournament simulator for testing LLM poker agents.

The current baseline is a playable spectator lab: six-player NLH freezeout tournaments, five PokerTH engine 4 opponents (or an explicit legacy heuristic mode), a replaceable agent, independent table workers, replayable decision records and an execution trace explorer. The [Stage 2A delivery](docs/stage-2a.md) records the native opponent integration and game evidence. The fuller LLM strategy and solver are the next milestone.

## Project direction

Before starting or resuming project work, read [shared context access](docs/shared-context.md). It points every local worktree to the same live project brief, decision log and agent direction. That brief separates agreed goals, proposed work and verified implementation. The sections below describe the runnable baseline.

## Project direction

Before starting or resuming project work, read [shared context access](docs/shared-context.md). It points every local worktree to the same live project brief, decision log and agent direction. That brief separates agreed goals, proposed work and verified implementation. The sections below describe the runnable skeleton.

## Project direction

Before starting or resuming project work, read [shared context access](docs/shared-context.md). It points every local worktree to the same live project brief, decision log and agent direction. That brief separates agreed goals, proposed work and verified implementation. The sections below describe the runnable skeleton.

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

Open http://localhost:5173. Create a tournament and press **Run table**. Tables start paused. **Step** advances one action, or deals the next hand after settlement. Two tables can run concurrently in separate processes. Closing the browser does not stop them while the API stays running.

New UI tables select PokerTH opponents by default. Opponent policy and hero mode are separate controls. Missing native builds produce a setup error; selecting Legacy heuristic is explicit. Older clients that omit the opponent field retain legacy mode.

No credentials are required for the heuristic hero. It uses SQLite locally and does not make model calls. Deck, hero policy, opponent policy and private personality assignment randomness are separate. API controller fields `hero_seed`, `opponent_seed` and `personality_seed` can reproduce a run; omitted seeds are independently generated and saved in the spectator configuration, outside player observations.

## OpenRouter agent

Set these in `apps/api/.env`, restart the backend, then select OpenRouter when creating a table:

```dotenv
OPENROUTER_API_KEY=your-server-side-key
OPENROUTER_MODEL=provider/model-id
AGENT_DEADLINE_SECONDS=10
AGENT_MAX_CALLS=100
```

Choose a model/provider supporting structured JSON output. The UI accepts the model ID per table. The graph calculates a small Monte Carlo equity estimate and retrieves bounded public-action evidence in parallel, then makes **one model call**. It validates the returned action and evidence references before execution. Invalid responses, errors, deadline expiry and exhausted budgets produce a visibly labeled heuristic fallback. No automatic retries multiply spend.

The call cap is per table, not a dollar limit. Configure account spending limits in OpenRouter. No production provider call was required to build or test the skeleton.

## What is implemented

- React/TypeScript/Vite spectator UI, responsive table, hidden-card toggle, pause/run/step/speed, two independent sessions, archive and replay.
- PokerKit dealing, arbitrary legal chip accounting within a discrete agent action menu, all-ins, side pots, eliminations, heads-up seating and payout settlement.
- Real native PokerTH engine 4 opponents, legal action normalization, public behavioral statistics and private shuffled personalities, with legacy heuristic comparison mode. Opponent parameters and seeds are never sent to the hero.
- Private observations for the hero, descriptive action counts, bounded evidence, state-version validation, structured OpenRouter adapter and local decision records.
- LangGraph orchestration with optional LangSmith tracing (`LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`). Traces contain only the agent's permitted observation, not the spectator snapshot. View traces in your LangSmith project.
- SQLAlchemy persistence: SQLite locally, PostgreSQL via `DATABASE_URL`, including Supabase session-pooler URLs.
- Descriptive ICM prize-equity display based on hand-start or settled stacks, in 100 prize units. Prize structure is configurable as 70/30 or winner-take-all.

## Scope and limitations

This is an **experimental baseline, not a GTO or ICM strategy solver**. Equity assumes uniform random opponent hands and does not infer ranges. Pot odds are an approximate reference and do not model side-pot eligibility. The ICM display does not drive a solved action-value policy. No solver datasets are bundled.

The planned competing-hypothesis analyses, future-street search, calibrated opponent beliefs and robust exploitation are future strategy work. Every action is recorded, including after hero folds, but off-turn LLM deliberation is not yet implemented. The present preparation graph has parallel calculation/retrieval, not multiple LLM analysts.

Opponent policies have stable biases and use current hand strength, pot and stacks. They are not validated human models or ICM-aware tournament professionals. Blinds increase by 1.5x every configured number of hands; there are no antes or re-entries. The simulator permits any number of contenders from six down to one.

Replay stores full spectator snapshots, including private cards, and must remain behind access control. It stores the last 120 public events in each snapshot plus full current-hand context for decisions. APIs page through older snapshots. This is deliberately simple and will need retention and normalized event storage for long-term scale.

On API restart, unfinished sessions are archived as interrupted. Replay survives; resuming their engine state is not yet supported. Pausing or stopping takes effect after an in-flight decision finishes, bounded by its model deadline. A single backend host/process owns the workers; do not run multiple Uvicorn workers or scale replicas without introducing a table-ownership mechanism.

## Deployment preparation

Templates are included; nothing is deployed automatically.

- **Supabase:** set `DATABASE_URL` to a server-side PostgreSQL connection (`postgresql+psycopg://...`, with `sslmode=require`). Prefer the session pooler for this persistent service. The backend creates its tables and enables RLS on PostgreSQL; no browser policies are granted. Connect as the owner/backend role. Supabase Auth and per-user authorization are not yet integrated.
- **Fly.io:** use repository-root build context with `apps/api/fly.toml`, review app name/region, and set `DATABASE_URL`, `CONTROL_TOKEN`, `ALLOWED_ORIGINS` and optional provider/tracing secrets. The template requires a control token and keeps the machine awake for running tournaments. Use one machine and one Uvicorn worker. SQLite on ephemeral deployment storage is not durable.
- **Vercel:** set root directory to `apps/web`; set `VITE_API_URL` to the API's HTTPS origin. Add the exact Vercel origin to backend `ALLOWED_ORIGINS`. Enter `CONTROL_TOKEN` in the dashboard's Connections panel. Never place provider keys or database credentials in `VITE_*` variables.

The shared access token is a development deployment gate, not a multi-user auth system. Local default binding is loopback. `WTR_PUBLIC=true` refuses startup without a token.

## Checks

```sh
python3 scripts/build_pokerth.py
npm run build
cd apps/api
uv run pytest
```

Tests cover complete seeded tournaments and chip conservation, payout settlement, heads-up order, private observations, stale/illegal actions, provider response validation, deadlines, budgets, independent table processes, replay persistence and access control. OpenRouter calls are mocked; hosted Supabase and LangSmith require your credentials for end-to-end verification.

See [architecture](docs/architecture.md) for the boundaries to preserve while iterating.

## PokerTH source and license

The pinned opponent core is vendored with its AGPL-3.0-or-later license and original notices. See [native setup and source obligations](native/pokerth/README.md) and [Stage 2A delivery](docs/stage-2a.md). The bridge preserves the upstream decision logic, but uses separate seeded randomness and maps sizing to our discrete legal menu. It is not a solver or a verified human model.
