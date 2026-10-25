# LLM benchmark runner

This small runner uses `TablePlay`, the same per-seat policy and PokerKit game
path as interactive workers. Each independent run gets a fresh spawned process,
opaque table ID, isolated seat memories and bounded execution. It does not use a
second poker engine or the legacy heuristic evaluation policy API. The existing
`wtr.evaluation` runner remains available for PokerTH and heuristic comparisons.

From the repository root, validate without credentials or provider requests:

```sh
PYTHONPATH=apps/api apps/api/.venv/bin/python -m wtr.llmbench benchmarks/llm-smoke.json --dry-run
```

Run the explicitly mocked engineering comparison and preserve its full report:

```sh
PYTHONPATH=apps/api apps/api/.venv/bin/python -m wtr.llmbench benchmarks/llm-smoke.json --mock --output data/llm-benchmark-mock.json
```

Existing output files are never overwritten. There is an explicit `--live` mode
for a separately authorized operator run with `OPENROUTER_API_KEY`; no live or
paid execution was performed for this milestone. Model IDs in the supplied
manifest are intentionally mock IDs. Dry-run validates configuration and expands
conditions, but does not establish a hosted model's current capabilities.

## Conditions and reproducibility

The saved smoke manifest has six seats, three conditions, all six hero rotations,
two development seed sets and two held-out seed sets: 72 games. The conditions
are a shared-model free-play control, the same configuration with chat disabled,
and a hero model swap holding instructions, harness and sampling settings fixed.
The production player supports only neutral `free_play` and `baseline` here.
There is no bluff-directed profile or future strategy harness in the benchmark.

The manifest requires an explicit shared control model. Seat models, temperature,
resolved limits, prompt version/hash and harness version are recorded per run.
Deck and policy seed streams are distinct inputs, stay evaluator-only and cannot
repeat across seed sets or splits. Rotations within a seed set are correlated,
so summaries average hero prizes across rotations before estimating variability
across independent seed sets. The approximate normal interval is omitted with
fewer than two complete provider-only seed sets; even two is a very small sample.
Incomplete or fallback-containing seed sets are counted but excluded from that
provider-only estimate. This conditional estimate must be read alongside the
failure counts, not used to hide them.

Reports contain dependency versions and manifest/source hashes and each run's accepted action sequence and observed legal menus,
public messages, per-seat prizes/places, actual or missing provider usage,
fallback reasons, decision latency and completion status. Tied elimination places
are valid. `outcome_sha256` excludes timing and random trace/table identifiers,
allowing deterministic mocks to be compared. Hosted model outputs are not
claimed to be deterministic. The mock uses artificial check/call actions and
periodic large legal actions to exercise multiple hands, eliminations and
settlement. Mock model names do not select different playing policies.

Human and mixed-control games are rejected by this autonomous runner. Manual
play and takeover are tested through the separate authenticated worker/API path.
A future review of human games must identify them explicitly as human or mixed.

## Limits, failures and accounting

Each run has hand/action/time limits plus the same per-seat and aggregate call,
output-token, request-character, memory and chat limits as interactive play.
Output capacity is reserved before every attempted provider request, including
failures and cancelled requests. Unused reservations are not reclaimed. There
are no client retries. These are conservative output budgets, not input-token or
dollar caps. Provider-reported cost stays nullable, with partial known totals and
missing-attempt counts. In mock reports, all usage values are simulated test
responses, never real spend.

Statuses distinguish `completed`, `completed_with_fallbacks`, `budget_exhausted`,
`action_limit`, `hand_limit`, `timeout`, `error` and `worker_error`. The benchmark
stops when the budget is exhausted; interactive games may continue with explicitly
labeled heuristic fallbacks. An incomplete game has `outcomes: null` and separate
provisional stack/prize/place fields plus unsettled pot. Every attempted run is
retained. CLI execution exits nonzero if any status is not `completed`.

A hard parent deadline protects against a worker that stops yielding. Progress
checkpoints retain started requests and accepted actions. `usage_complete: false`
on an interrupted worker means only the last checkpoint was recovered; more
usage may be unavailable. A normal final checkpoint can have
`usage_complete: true` while individual token/cost fields remain null because the
provider did not supply them. No totals are invented for unknown usage.

`--mock-failure http`, `invalid`, `timeout` or `missing_usage` exercises reporting
without network calls. The first three inject a failure on the first request of
each independent run. A missing-usage scenario omits usage from every response.

## Provider contract

Requests use strict JSON Schema, `provider.require_parameters: true` and local
response validation. Structured-output support varies by endpoint, and strict
mode is not an unconditional guarantee across providers. Unsupported requests
produce an explicit failure and labeled fallback. See the official
[OpenRouter structured-output documentation](https://openrouter.ai/docs/guides/features/structured-outputs).
No tool calling, model-directed LangGraph loop or solver is claimed here.

Regenerate machine-readable fixtures with:

```sh
PYTHONPATH=apps/api apps/api/.venv/bin/python scripts/export_llm_contract.py
```

The JSON schemas cover field shapes. Pydantic runtime validators additionally
check seat coverage, compatible controls, distinct splits and controlled preset
conditions. The stable interactive configuration lives in
`contracts/examples/llm-six-seat-neutral.json` and `/api/config.llm_preset`.

## Reproduce the saved review evidence

Run `PYTHONPATH=apps/api apps/api/.venv/bin/python scripts/run_llm_review.py --output data/llm-review-new` from the repository root. The output directory must be new. This runs the 72-game mock comparison and six explicit failure/usage scenarios, then saves full reports, compact review reports and one complete sample game. Every transport in this script is mocked.
