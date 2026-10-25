# Backend observability milestone

Branch: `feat/observability`, based on `0fe9596`. The shared contracts are unchanged. No frontend, strategy, or evaluation implementation is included.

## Integration

`Agent.decide(observation)` retains its existing decision fields and adds `trace_id` and nullable `langsmith_url`. The optional constructor argument `trace_sink` receives bounded trace snapshots. Direct callers can inspect `agent.last_trace`; worker callers persist every span transition. Call `agent.close()` when disposing an agent with optional telemetry enabled.

Authenticated routes use the existing `CONTROL_TOKEN` gate:

- `GET /api/tables/{table_id}/traces?hand=3&limit=50&cursor=...`
- `GET /api/tables/{table_id}/traces/{trace_id}`

The first route returns `{items, next_cursor}`, newest first. Limits are 1 to 200. Cursors are opaque and scoped to the table and hand filter. A malformed or mismatched cursor returns 400. Unknown tables, unknown traces, and cross-table trace lookups return 404. As with the existing API, an empty token permits loopback development; `WTR_PUBLIC=true` requires a token. This is shared-token access control, not per-user authorization.

Table snapshots include nullable `active_trace_id`. Its transitions update the current snapshot and WebSocket change detection without advancing the poker version or adding duplicate replay frames. Completed decisions link to their root trace. Frontend integration should poll the selected running trace, stop polling when complete, and tolerate historical decisions without trace fields. `langsmith_url` can arrive later on the trace endpoint after asynchronous export. The decision's initial URL remains null. Do not assume a link is available immediately after completion.

The root covers real graph execution. Preparation nodes run concurrently; `choose_action` contains the actual heuristic selection, model call, response validation, and fallback when executed. The heuristic is computed before a model call, preserving the skeleton's RNG behavior and fallback action. There are no model or validation spans when a key or call budget prevents a request. A successfully recovered decision has a completed root and a failed child span. Provider timeout and task cancellation are distinguished.

UTC timestamps support correlation. Durations and offsets use `perf_counter`, including local instrumentation overhead. Root duration is elapsed time, not summed child work. Running durations, unavailable token counts, and unavailable costs stay null. The strategy module is intentionally not wired into this graph yet.

## Local persistence and initialization

`Store.initialize()` is the additive v1 migration: it creates the indexed `wtr_traces` table if missing while leaving existing `wtr_sessions` and `wtr_events` columns intact. It runs once in the API host before workers start. Workers never initialize or mark another table interrupted. PostgreSQL table creation and enabling RLS occur in one transaction.

The trace table has an insertion sequence for stable cursor pagination, a unique root UUID, table and hand correlation fields, status, and a JSON record. In-flight writes use an upsert without changing the original insertion sequence. URL updates only patch existing records, so delayed export cannot resurrect retained-out traces or overwrite newer spans.

Set `TRACE_MAX_PER_TABLE` to the number of completed traces retained per table (default 2000, minimum 1). Retention is independent of hand transitions and does not delete replay. Older trace links can return 404 after retention. This milestone bounds trace payloads and completed records per table, not total sessions or the skeleton's snapshot archive. Each span input/output object is capped at 128 KiB; oversized objects become an explicit truncation marker. Recursive sanitation limits depth, collection size, and string length. The current fixed graph emits at most eight spans per successful model/fallback decision.

Restart marks unfinished sessions interrupted and unfinished trace spans cancelled. Their unknown durations remain null. Dead or forcibly terminated worker processes are detected even without a browser, and running traces are cancelled. Existing replay remains readable. This still does not resume executable tournament state.

The redundant snapshot IPC queue has been removed. The database is the source for current snapshots and replay. Each table retains a separate process and a bounded 32-command queue; saturation returns 409. The API reaps stopped processes and closes queue handles. Shutdown requests stop, waits at most 12 seconds for workers collectively, then terminates or kills workers that exceed that budget. Engine mutation remains sequential within each table.

## Privacy and optional LangSmith

Agent input is reconstructed from the permitted observation schema before graph invocation. Opponent cards, simulator profiles, deck state, arbitrary added fields, credentials, headers, raw provider errors, and reasoning fields are excluded. Traces store submitted model messages and the returned structured action/summary/uncertainty/evidence fields. Usage is allowlisted to non-negative input/output token counts and provider-reported USD cost. Costs are not estimated locally.

Set `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT` on the backend to enable export. Without a key, local tracing remains fully functional. Automatic graph tracing is explicitly disabled so it cannot bypass the same filtered records or create a second root tree.

The adapter uses the installed SDK's `RunTree`, `post()`, and `get_url()` support with the local root/span UUIDs and actual parents. Model runs use chat messages, structured assistant output, `usage_metadata`, and `ls_provider`/`ls_model_name` metadata. Usage conventions follow the [LangSmith usage schema](https://reference.langchain.com/python/langsmith/schemas/UsageMetadata). It does not call a public sharing API.

Each table has one daemon export thread and a bounded 16-record queue. SDK batching is disabled, network timeouts are two seconds, and HTTP retries are disabled. A full queue drops external exports rather than blocking a decision; local records remain. `close()` waits only 250 ms for best-effort telemetry completion, so pending uploads can be lost on process exit. There is no durable external retry outbox in this milestone. SDK error logging from the exporter thread is filtered to avoid exposing raw HTTP details. Missing credentials, failed ingestion, failed URL resolution, and local trace-sink exceptions do not alter the selected action.

## PostgreSQL and Supabase preparation

Use a server-only connection, for example:

```dotenv
DATABASE_URL=postgresql+psycopg://BACKEND_ROLE:URL_ENCODED_PASSWORD@SESSION_POOLER_HOST:5432/postgres?sslmode=require&connect_timeout=10
CONTROL_TOKEN=SET_A_PRIVATE_TOKEN
WTR_PUBLIC=true
TRACE_MAX_PER_TABLE=2000
```

Use the Supabase session pooler or a direct PostgreSQL connection for this persistent service. The backend database role needs schema creation and table ownership for initialization, and owner/BYPASSRLS access to its private tables. RLS is enabled for sessions, events, and traces, with no browser policies. An ordinary role cannot read rows even if it has SELECT grants. Keep database credentials out of `VITE_*` variables and use one API host with one Uvicorn worker. Hosted Supabase, multi-user Supabase Auth, and production migration rollout are not verified or implemented here.

For this worktree, start the API on port 8012 and use `ALLOWED_ORIGINS=http://localhost:5175,http://127.0.0.1:5175`. No runtime server is left running by this milestone.

## Verification

From `apps/api`:

```sh
uv sync --extra test
uv run pytest -q
```

The default suite covers existing game invariants plus trace schema validation, parent/root IDs, real preparation overlap, in-flight snapshots, mocked model requests and errors, cancellation, budgets, privacy, pagination/authentication, retention/restart, SDK run construction, blocked/failed telemetry, and independent workers without a WebSocket connection.

An opt-in test requires a disposable PostgreSQL database where the test user can create a temporary role. Never point it at a production database:

```sh
WTR_TEST_POSTGRES_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:PORT/TEST_DB' uv run pytest -q tests/test_postgres.py
```

Local verification used PostgreSQL 16 in a temporary Docker container and checked table initialization, JSON upsert, pagination, retention, link updates, restart/replay, and RLS against a non-owner role. OpenRouter and LangSmith were mocked. No paid model request, hosted Supabase connection, or hosted LangSmith ingestion was verified. Combined frontend/strategy/evaluation integration remains a separate check after merging the workstreams.

Final milestone checks on 2026-10-25: 37 backend tests passed with the disposable PostgreSQL test enabled. The default run passed 36 tests and skipped only that opt-in database test. `git diff --check` and Ruff's `F` checks passed on the changed Python files. The temporary PostgreSQL container was stopped and removed after verification.
