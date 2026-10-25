# Active delivery: configurable LLM tables

Active task on `feat/llm-table`, based on reviewed main
`f73fbe13a72cf535531b75dd12b1a46ec7fa071f`. Shared context revision 20 applies.
Stage 2A is complete and preserved. Continue this implementation through production
workers, shared benchmark execution, mock evidence and coherent local commits.
Do not revert to the earlier leakage or API-key questions after compaction.

## Contract readiness

Implementation is in progress. The corrected canonical `llm-table-v1` contract is
accepted: **only `free_play` is supported**. The earlier bluff-directed profile is
removed, not an alias. `baseline` is the only implemented harness. Unsupported
profiles/harnesses fail configuration validation.

Additive refinements for frontend consumers:

- `opponents: "llm"` selects all-LLM play independently of legacy `mode`.
- `player_count` defaults to 6 and accepts 4 or 6. `hero_seat` defaults to 0.
- `seat_configs` contains one entry per seat. Blank seat `model` inherits the table
  `model`, then backend default model; unresolved models are rejected before play.
- Optional `llm_limits` supplies bounded call, output, deadline, chat and memory
  settings. Defaults and schema will be exposed with server capabilities.
- New snapshots retain hero `decision` and add `decisions_by_player`, `chat`,
  `chat_sequence`, `active_player` and `provider_usage`. `active_trace_id` remains
  the current sequential turn's trace. Missing fields on old records remain valid.
- New decisions carry `player` and the input `chat_sequence`. A message's
  `state_version` is the observed version of its accepted action. Chat IDs are
  table-local `cN`; snapshots contain only chat published at that replay point.
- `GET /api/tables/{id}/traces?player=N` filters metadata attribution. Unattributed
  historical traces are treated as player 0. Other query parameters remain valid.
- Provider failures and exhausted budgets produce labeled legal fallback actions,
  no public message. Benchmark reports distinguish completion with fallbacks or
  exhausted budgets from successful provider-only completion.

No frontend files or canonical direction documents are owned by this task.
Integration services on ports 8012/5175 must remain untouched. Use a disposable
worktree-local database and alternate port 8015 only if a server is needed.
Provider requests in verification must use explicit mocks. No paid calls, push,
main merge, deployment, extra agents or cross-chat messages are authorized.

## Revision 20 correction and manual API

Six seats are the primary baseline; optional four-seat support remains. Add
`hero_control: "human" | "llm"` (API default `llm`, creation UI should select
`human`). Five opponents retain their saved resolved seat settings without any
prompt/personality rotation. The hero model stays configured for takeover.

Manual API is implemented in the current working tree:

- `capabilities.manual_hero: true` accompanies the other capability flags.
- Snapshot `hero_turn` is nullable. While awaiting the hero it holds `player`,
  `state_version`, `chat_sequence`, opaque `turn_token`, and permitted `observation`.
- Authenticated `POST /api/tables/{id}/hero-action` accepts `{turn_token,
  state_version, action, public_message?}`. HTTP 202 means the owning worker
  committed the action/message. HTTP 409 means rejected or acknowledgement could
  not be confirmed; refresh state before retrying. Tokens are single-use.
- `POST /api/tables/{id}/control` accepts `{action:"set_hero_control",
  hero_control:"human"|"llm", state_version}` with worker acknowledgement.
- A human turn can be submitted while paused and advances exactly one action.
  Waiting has no model call, deadline action or automatic fallback. Pause/stop
  remain responsive. Switch/pause/stop cancel pending policy work before applying
  further results; started attempts stay counted. Resume is explicit.
- Manual records use `source:"human"`, `trace_id:null`, `model:null`; no fictitious
  spans. Snapshot `control_changes` records recent accepted switches with their
  committed versions. Replay snapshots also preserve the actual configuration.

Initial limits are represented by `LLMLimits` and exposed under server config
`llm_limits`. Output-token budgets reserve the requested maximum before an
attempt; unused capacity is not reclaimed. They are conservative output caps,
not total input-token or dollar caps. LLM baseline decisions have empty `metrics`
(no strategy tool was invoked); consumers should not assume legacy metric fields
exist. Actual provider usage includes nullable fields and partial known totals.

## Interface readiness update

Shared-context revision 20 is the active scope. Core worker/API verification has
passed, including authenticated manual actions, invalid and consumed tokens,
paused one-action commits, waiting responsiveness, independent table processes,
in-flight takeover cancellation, both control directions and mixed replay.
The full backend suite before benchmark additions passed 143 tests, with one
optional PostgreSQL test skipped. Final benchmark verification is in progress.

`GET /api/config` also supplies `llm_preset`, a stable six-seat neutral manual
configuration. Its blank per-seat models inherit the configured table model.
The checked-in example is `contracts/examples/llm-six-seat-neutral.json`.
`SeatConfig.temperature` defaults to 1.0 and accepts 0 to 2; the actual value is
submitted and traced per seat. No sampling setting changes automatically.
Machine-readable configuration, manual-action and control schemas are under
`contracts/`. Runtime validation additionally enforces complete unique seats and
conditional control fields that JSON Schema alone does not express.
