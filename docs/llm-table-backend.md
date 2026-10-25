# Configurable LLM table backend

Branch: `feat/llm-table`, based on reviewed main
`f73fbe13a72cf535531b75dd12b1a46ec7fa071f`. Shared-context revision **20** was read
and rechecked. Runtime commit: `4cf0caa`. Benchmark commit: `aeed481`. Final evidence is
committed immediately after those changes on the same branch. Stage 2A remains preserved on `feat/pokerth-opponents`.

The six-seat environment is implemented: five stable neutral LLM opponents,
manual hero actions/messages and optional LLM takeover. Fully automated play uses
six per-seat LLM policies. Four-seat configurations remain supported. Only
`free_play` and `baseline` are accepted. There is no bluff-directed prompt,
strategy-frequency target, solver or model-directed tool loop in this slice.

## Frontend contract readiness

The additive contract in `contracts/llm-table-v1.md` is implemented. New fields
remain optional for reading historical sessions. Existing hero `decision`, trace
root schema v1 and legacy/PokerTH configurations remain readable.

- `/api/config.capabilities` exposes `llm_tables`, `public_chat`,
  `per_seat_traces` and `manual_hero`. `llm_limits` gives defaults.
- `/api/config.llm_preset` supplies the stable six-seat neutral interactive
  configuration, with `hero_control: human`. The saved fixture is
  `contracts/examples/llm-six-seat-neutral.json`.
- `opponents: llm` selects individual LLM opponents independently of legacy
  `mode`. API omission of `hero_control` defaults to `llm` for automated clients.
- `seat_configs` must cover each seat exactly once. A blank seat model inherits
  the table model, then the backend default model. Actual resolved models are
  saved. Unresolved models and missing credentials fail before worker creation.
- Each seat has independent model, neutral name, instruction profile, harness,
  chat permission and `temperature` (default 1.0, range 0 to 2). Settings stay
  fixed until a new configuration is deliberately created. Operator names never
  enter model inputs; public identities are reconstructed as `Player N`.
- Snapshots add `decisions_by_player`, `chat`, `chat_sequence`, `active_player`,
  `provider_usage`, nullable `hero_turn` and `control_changes`. `active_trace_id`
  identifies the current sequential turn. `decision` remains the hero's latest
  decision, including manual decisions.
- Decisions carry `player`, frozen `state_version` and input `chat_sequence`.
  Baseline LLM `metrics` is empty because no strategy tool ran. Do not assume the
  legacy graph's metric fields exist for this policy.
- `GET /api/tables/{id}/traces?player=N` filters seat attribution. Old records
  without player metadata are attributed to seat 0. Cursors are bound to table,
  hand and seat filters, and cannot be reused under a different filter.

Machine-readable configuration, manual-action and control schemas live under
`contracts/`. Pydantic runtime validation additionally enforces seat coverage and
conditional control fields that generated JSON Schema does not express.

## Manual actions and takeover

An awaiting hero has `hero_turn: {player, state_version, chat_sequence,
turn_token, observation}`. The observation contains only that seat's permitted
cards, public game state/chat and legal menu. Waiting has no hero model request,
timeout action or automatic fallback. Controls and independent tables remain
responsive.

Authenticated `POST /api/tables/{id}/hero-action` accepts `{turn_token,
state_version, action, public_message?}`. HTTP 202 means the owning worker committed
the action/message together. HTTP 409 means rejection or an unconfirmed worker
acknowledgement; refresh before retrying. Shape or extra-attribution fields fail
HTTP 422. Tokens are single-use. Wrong turns, stale tokens/versions, illegal
choices and disallowed messages change neither chips nor chat.

A valid manual action while paused advances exactly one action without resuming.
Records use `source: human`, `model: null`, `trace_id: null`, with no fictional
model spans. One bounded public message may accompany a valid action, or the
player may remain silent. Chat-disabled seats cannot publish a message.

`POST /api/tables/{id}/control` accepts `{action: set_hero_control, hero_control,
state_version}` and waits for worker acknowledgement. A switch invalidates manual
tokens and cancels pending policy work before changing the observed version.
Already started attempts stay counted, even if their results are discarded.
Switching a paused table leaves it paused. Control changes and actual modes are
preserved in replay. Autonomous benchmarks reject human/mixed control.

Pause and stop also cancel pending policy work. This deliberately replaces the
older pause behavior that allowed the pending action to finish. Tests preserve
both the successful in-flight version guarantee and the new cancellation
contract: cancelled turns cannot apply an action or publish a message afterward.

## Privacy and accounting

`TablePlay` is the shared worker/benchmark seam. Each table owns an independent
process and sequential state writer. Each LLM seat receives a rebuilt permitted
observation, bounded own memory and a chronological chat window frozen at turn
start. Public actions are projected into every seat's memory even after folding.
No other-seat cards, memory, model/profile settings, seeds, future deck, experiment
labels or spectator snapshots are supplied. Public history text is reconstructed
from typed actions. Chat is untrusted game data, never higher-priority instructions.

Action legality, seat, state version, chat cutoff and message permission/length
are checked before game or chat mutation. Memory is committed only after an
accepted action. Public talk and private justifications are distinct outputs.
Local traces and optional asynchronous LangSmith exports receive permitted
inputs; model errors never copy raw upstream bodies or credentials into records.

Calls and output reservations have per-seat and table caps. Every attempt counts,
including timeout, malformed response and cancellation. Output-token capacity is
reserved before a request and is not refunded for shorter output. Requests also
have deadlines, bounded response bytes/context characters, chat length/history
limits and bounded private memory. There are no client retries. These bounds
are not total input-token or dollar spending caps.

Actual provider usage is retained even when a returned decision is rejected.
Unknown usage/cost stays null; summaries expose known partial totals and missing
attempt counts. Exhaustion or provider failure yields an explicitly labeled
heuristic fallback without fabricated public chat. A cancelled request yields no
action. No fallback is presented as a model decision or as GTO.

The strict JSON Schema request and `require_parameters` routing follow official
[OpenRouter structured-output guidance](https://openrouter.ai/docs/guides/features/structured-outputs).
Local validation remains mandatory because endpoint capabilities and strictness
vary. Real provider compatibility is not established by these mock tests.

## Benchmark and evidence

See [runner instructions](llm-benchmark.md). The runner uses the same game and
player policies, creates a fresh process/memory set per run, rotates seats and
keeps development/held-out seed sets separate. It records versions/hashes,
resolved configuration, legal action menus, public messages, outcomes, usage,
latency and explicit failures. Incomplete outcomes remain separate from completed
tournament results. Summaries treat rotations sharing seeds as correlated.

The saved smoke manifest has 72 six-seat games across shared-model, chat-disabled
and model-swap conditions. Failure fixtures cover HTTP rejection, invalid output,
request timeout, missing usage, budget exhaustion and whole-run timeout. The
mock uses artificial legal actions solely to test the environment.

Verification completed on 2026-10-25:

- `apps/api/.venv/bin/pytest -q apps/api/tests`: **160 passed, 1 skipped**.
  The skipped test is optional PostgreSQL integration. The passing suite includes
  native PokerTH regressions, side pots, heads-up behavior, chip/payout
  conservation, legacy tracing/evaluation, complete four-seat and six-seat LLM
  worker games, per-seat tracing, privacy and all manual-control scenarios.
- The formerly failing in-flight trace test now checks successful completion
  against the frozen version and deterministic cancellation without a committed
  action. Separate spawned-worker tests cover takeover, pause and stop.
- All **72 mock benchmark games completed**, with **5,382 accepted legal actions**,
  zero rejected actions, zero fallbacks and conserved chips/payouts.
- Six saved failure/usage scenarios behaved as intended: HTTP, invalid response
  and request timeout completed with one labeled fallback; missing usage stayed
  null; a one-call cap produced `budget_exhausted`; a whole-run deadline produced
  an incomplete `timeout`. Parent crash and blocked-worker checkpoint recovery
  are also tested. Repeated seeded mock runs have identical outcome hashes.
- Ruff's Python error/undefined-name checks passed (`E4,E7,E9,F`, excluding the
  existing intentional post-dotenv `E402` imports). `git diff --check` and
  `uv lock --check --offline --directory apps/api` passed.
- Current source files match the saved report SHA-256:
  `f32a915169532ba57095e97238c46fa3b990ff95348e3708927067ec1cafcc8f`.

Committed review artifacts:

- [72-game mock report](review/llm-table-mock.json), a compact derivative retaining
  every run, outcome, usage total, per-seat attempt/fallback counts, legal-action
  checks and hashes. The manifest reconstructs each resolved configuration.
- [Failure and usage examples](review/llm-table-failures.json), including incomplete
  outcomes and missing usage.
- [Complete sample mock game](review/llm-table-game.json), with accepted actions,
  observed legal menus and public chat.

Full per-action and per-seat usage reports are saved locally in the ignored
`data/llm-review-final/` directory. Regenerate them using the documented review
script and a new output directory. All provider responses and usage/cost values
in these artifacts are explicit mocks. No real API key or provider spend was
used, and mock prizes are tournament prize units, not monetary returns.

## Remaining limits

No paid requests, real-model strategic evaluation, live LangSmith export or
PostgreSQL deployment was performed. The optional PostgreSQL test requires a
separate test database. This is the environment and benchmark milestone, not the
future LangGraph strategy harness, solver or proof of poker ability. A configured
live model must support the required parameters at an available OpenRouter
endpoint. Human operator spectator access is not an anti-cheat boundary.

No frontend files, canonical decision log or integration services on 8012/5175
were changed. There was no push, merge or deployment.
