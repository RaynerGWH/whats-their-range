# Parallel work plan

Four Codex chats start from the same committed skeleton. This file is the shared integration agreement for their first milestones. These are coding agents working on the repository, separate from the poker agents simulated by the application.

For current project direction and decisions, read [shared context access](shared-context.md) before using the original assignments below. Keep these first-milestone contracts and ownership boundaries intact until an explicit integration change is agreed.

## Ownership

| Chat | Branch | Owns | First milestone |
| --- | --- | --- | --- |
| Strategy | `feat/strategy` | New `apps/api/wtr/strategy/`, `tests/test_strategy*.py`, `docs/strategy.md` | Tested hand and bluff candidate analysis with explicit assumptions |
| Backend | `feat/observability` | Existing API modules, new tracing/persistence modules, migrations, backend tests, API dependencies | Real execution spans, trace API, LangSmith linking, durable local storage and PostgreSQL preparation |
| Frontend | `feat/trace-explorer` | `apps/web/`, web dependencies and root npm lockfile | Clickable trace explorer using the shared trace contract |
| Evaluation | `feat/evaluation` | New `apps/api/wtr/evaluation/`, `tests/test_evaluation*.py`, `docs/evaluation.md` | Reproducible policy evaluation and saved results |

Each chat may add a short progress or integration note in its own documentation. Shared contracts and this plan are fixed for the first milestone. If a contract is insufficient, document a proposed change and keep existing consumers working. Do not silently rename shared fields. Do not modify another workstream's files merely for formatting or convenience.

Read `AGENTS.md`, `README.md`, `docs/architecture.md`, and the task brief in `docs/tasks/` before editing. Create the assigned branch from your worktree's initial commit. Use `feat/`, never `codex/`. Work only inside your own checkout. Do not merge, push, deploy, or edit the original checkout as part of these milestones. Commit tested changes and report the commit, checks, and integration needs.

## Existing boundaries

- `Agent.decide(observation)` remains compatible with the existing worker. Preserve the current decision fields, legal-action checks, state-version checks, model deadline, and call cap.
- `Tournament.observation()` is the allowed poker-agent input. Spectator snapshots, opponent archetypes, hidden cards, future cards, and outcomes are excluded.
- Every table retains an independent process and sequential mutation of game state. No central poker turn scheduler.
- Keep the current heuristic available as a named, reproducible comparison policy. It is not GTO.
- Cloud keys are not a prerequisite for local progress. Mock provider/telemetry calls in tests, keep local tracing functional, and report hosted verification separately.

## Trace contract v1

The machine-readable record is `contracts/trace-v1.schema.json`. `contracts/trace-v1.example.json` is an explicitly synthetic development fixture, never live gameplay data.

One `TraceRecord` describes one decision. `trace_id` is its root run UUID; every child has a unique `span_id`, the root uses `span_id == trace_id`, and children identify their actual parent with `parent_span_id`. Correlate to `table_id`, `hand`, and the observed `state_version`. Traces from different tables must not share a root.

Spans are actual recorded execution, including failures and fallback when they occur. Do not generate placeholder completed spans for steps that were not executed. UTC timestamps support correlation. `start_offset_ms` and `duration_ms` come from a monotonic clock relative to the root, so the UI can show parallel overlap. Root duration measures elapsed time and is not the sum of child durations. Running durations and unavailable token/cost information are null, never invented zero values.

Span `inputs` and `outputs` are bounded JSON objects from the agent's permitted data. Redact credentials, headers, raw provider error bodies, and hidden simulator state before local storage or external export. Capture the actual submitted model messages and returned structured decision, not a transcript of private internal reasoning. Record model identifiers and safe error messages. Match the installed LangSmith SDK's supported message/usage conventions.

### API

Preserve existing session REST routes and WebSocket messages. Add authenticated routes:

- `GET /api/tables/{table_id}/traces?hand=3&limit=50&cursor=...` returns `{items: TraceRecord[], next_cursor: string | null}`. `hand` and `cursor` are optional; default limit 50, maximum 200. Order newest first. Cursors are opaque, and unknown tables return 404.
- `GET /api/tables/{table_id}/traces/{trace_id}` returns `TraceRecord`; unknown or mismatched IDs return 404.

Decision records may add nullable `trace_id` and `langsmith_url` fields. Existing records without them remain valid. A table snapshot may add nullable `active_trace_id` so the UI can inspect an in-flight decision. Emit updated snapshots when that ID changes, without pretending a poker action was taken. The frontend can poll the selected running trace at a modest interval and stop when complete or unmounted. Keep this first milestone transport simple. Additional live trace messages are a later compatible enhancement.

`langsmith_url` is optional and should be obtained through supported SDK functionality. Keep the normal authenticated LangSmith link; do not automatically share traces publicly. Upload asynchronously, tolerate unavailable credentials or ingestion failures, and never make a poker action wait for telemetry network completion. Local trace persistence should still work when LangSmith is disabled.

## Strategy contract v1

Add a pure `analyze(observation: dict, metrics: dict) -> dict` entrypoint exported from `wtr.strategy`. It returns:

```json
{
  "schema_version": 1,
  "state_version": 12,
  "candidates": [
    {
      "action": "raise:40",
      "intent": "bluff",
      "rationale": "Concise, testable explanation tied to the supplied state.",
      "evidence_ids": [],
      "assumptions": ["Any assumed opponent response is explicit."],
      "limitations": ["No calibrated range model is available yet."],
      "estimates": {},
      "continuation": "Describe the contingency without asserting future cards or actions."
    }
  ],
  "uncertainty": ["Current known limitations"]
}
```

Candidate actions must be keys in the supplied legal menu. Intents are `value`, `bluff`, `semi_bluff`, `check`, `call`, or `fold`. Evidence IDs must exist in the observation. Estimates are labeled conditional calculations with units and assumptions, not claimed solver values. Keep the module deterministic, free of network/database calls, and free of mutable shared state. It proposes candidates, not authoritative game actions. The integration chat will connect it to LangGraph after review; the backend should not invent a strategy implementation while that module is being built.

## Local runtime isolation

Each checkout installs its own dependencies. Do not share `.venv`, `node_modules`, writable SQLite files, or generated output folders. Do not copy live secrets by default. Use the worktree-local `apps/api/data/` and leave it ignored.

| Chat | API port | Web port |
| --- | --- | --- |
| Strategy | 8011 | 5174 |
| Backend | 8012 | 5175 |
| Frontend | 8013 | 5176 |
| Evaluation | 8014 | 5177 |

Ports 8000 and 5173 belong to the original preview. If starting a worktree API, override `ALLOWED_ORIGINS` to its web port. For a worktree web server, set `VITE_API_URL` to its API origin and pass the assigned Vite port explicitly. Do not kill another chat's processes. Use `uv sync --extra test` in `apps/api` and `npm ci` at repository root when those dependencies are needed.

## Integration and evidence

Backend trace contract and frontend fixtures can progress concurrently. Strategy and evaluation use the unchanged observation/policy boundary. After review, merge backend, frontend, strategy, and evaluation one at a time into an integration branch, wire the strategy module explicitly, and run combined checks. A passing isolated branch does not establish that the combined application works.

Report tests actually run, whether provider calls were mocked, and any unverified hosted connections. A few tournament wins are not evidence of strong or unexploitable play.
