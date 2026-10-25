# Local tournament evaluation

The evaluation runner executes complete six-seat tournaments without frontend pacing. It uses the existing PokerKit engine and its private observation, legal menu, settlement and state-version checks. Each tournament has its own spawned process. The parent collects results and enforces a wall-clock deadline; all poker turns remain sequential inside that table's process. Experiments run one tournament at a time to keep local resource use modest.

## Reproduce a run

From `apps/api`, install this checkout's dependencies with `uv sync --extra test`, then run:

```sh
uv run python -m wtr.evaluation
```

The default smoke experiment has two tournaments: tuning seed 1 and held-out seed 101, the existing heuristic, standard opponents, 10 big-blind stacks and blinds increasing every two hands. It saves `results.json` and `summary.txt` under a new UTC-stamped `data/evaluation/` directory. Output directories are never overwritten. No server, frontend, database, credentials, model calls or telemetry exports are needed by the built-in policies. No runtime ports are used. Evaluation API/web ports, if later needed, remain 8014/5177.

This modest expanded check was used for the milestone:

```sh
uv run python -m wtr.evaluation \
  --tuning-seeds 1,2 --held-out-seeds 101,102 --repeats 2 \
  --scenario standard --scenario repeated-shove \
  --output data/evaluation/milestone-smoke
```

Select additional policies or scenarios by repeating their flags:

```sh
uv run python -m wtr.evaluation \
  --policy heuristic --policy check-call --policy shove \
  --scenario single-shover --tuning-seeds 1 --held-out-seeds 101
```

Larger experiments are opt-in. Total attempts equal the number of seeds multiplied by repeats, policies and scenarios. Defaults bound each tournament to 300 hands, 5,000 committed actions and 120 wall-clock seconds. Override these with `--max-hands`, `--max-actions` and `--timeout-seconds`. The deadline includes child startup and policy initialization. A blocked synchronous or asynchronous policy is terminated with its worker, without blocking following tournaments. A tournament that finishes at a bound counts as complete. Otherwise a bound produces a failure, not a synthetic placement or zero prize.

Other options include `--stack-bb`, `--hands-per-level`, `--payouts` (`70/30` or `winner-take-all`) and `--opponent-profiles` (five comma-separated profiles for seats 1 to 5). Profiles are `tight`, `caller`, `aggressive`, `balanced` and `volatile`. CLI help lists all options. Exit status is 0 when every tournament completes, 1 for any recorded tournament failure, and 2 for invalid CLI configuration.

## Policies and scenarios

| Name | Behavior |
| --- | --- |
| `heuristic` | Calls the existing `assess` and `baseline` functions, with the same seed plus 991 RNG offset as `Agent(mode="heuristic")`. Avoids graph overhead and optional telemetry. Version `skeleton-0fe9596-v1`. |
| `check-call` | Checks when possible, otherwise calls, including an all-in call. Version 1. |
| `shove` | Chooses the largest legal raise-to amount; checks or calls when raising is unavailable. Version 1. |

The heuristic uses its existing 48-sample random-opponent equity estimate and approximate pot odds. It is not a solved tournament policy. Measured policy latency includes calculations and adapter execution, but excludes LangGraph, UI pacing and provider latency.

`standard` uses the five configured baseline profiles. `single-shover` replaces seat 1's action selector with the shove policy and retains the other four profiles. `repeated-shove` replaces all five opponents with the shove policy. These are deliberately artificial pressure environments, not validated models of people. Maximum raises are legal-menu choices; when the engine disallows raising, the adapter cannot force a shove.

Profiles belong to the simulator configuration and appear in the experiment manifest for reproducibility. They are never added to policy input. Each policy receives only a deep copy of `Tournament.observation()`, including its own cards, public actions and legal choices. The harness never passes a tournament object, spectator snapshot, opponent cards, future deck or simulator profile to `decide`.

## Adapter interface

An importable local factory accepts one integer seed and returns an object with `decide(observation)`. The method may be synchronous or asynchronous. It returns a dictionary with `action` (a legal menu key) and `state_version` (the supplied observation's integer `version`). Extra decision fields are ignored and not saved. For example:

```python
class CandidatePolicy:
    def __init__(self, seed):
        self.seed = seed

    def decide(self, observation):
        action = next(a for a in observation["legal"] if a["kind"] == "call")
        return {"action": action["key"], "state_version": observation["version"]}
```

Put this in an importable module and select it with:

```sh
uv run python -m wtr.evaluation \
  --adapter my_policy:CandidatePolicy --policy-name candidate --policy-version experiment-1
```

A fresh policy instance is constructed for each tournament. For programmatic use, export `EvaluationConfig`, `PolicySpec`, `evaluate`, `run_tournament` and `save_report` from `wtr.evaluation`. Multiprocessing callers must use an `if __name__ == "__main__":` guard and a real importable module, not a REPL-defined factory. Adapter authors must use deterministic, private RNG state if they want repeated outcomes. Explicitly version and retain custom adapter source: the manifest hashes built-in evaluation and engine source, not arbitrary third-party adapter dependencies.

This is a trusted local Python extension seam, not a security sandbox for hostile code. A custom adapter can perform arbitrary Python I/O; only the supplied built-ins guarantee no network calls. Do not configure paid or live provider adapters for this milestone. The strategy module can later be called from a local factory that selects a legal candidate and returns the observed version. The harness does not silently pick a strategy candidate or change `Agent.decide`.

The harness checks output shape, the original observed version and the original legal menu before calling `Tournament.apply`, which independently validates legality and version. Copy mutation cannot change those checks. Invalid adapters stop the affected tournament; there is no silent fallback that could disguise which policy was evaluated.

## Results and interpretation

The evaluation report has its own `schema_version: 1`; it is not a shared `TraceRecord`. The existing trace contracts and synthetic development fixture are unchanged.

`results.json` contains:

- Experiment configuration, policy names/versions/factory references, tuning and held-out seed lists, repeats, opponent setup and limits.
- UTC report creation time, Python and PokerKit versions, SHA-256 hashes of engine, agent and evaluation source files.
- Per-attempt seed, split, repeat index, scenario, table ID, hero seat (0), worker PID, completion status, hands begun, committed actions and final observed state version.
- Completed-tournament hero finishing position and prize units, all six placements and prizes, chip totals and conservation status. Incomplete tournaments have null hero placement and prize, even if the hero was already eliminated.
- Every committed action's hand, observed version, acting seat, original legal keys, selected action and measured policy latency in milliseconds. There are no cards or raw policy responses in the saved action log.
- Total measured duration, committed hero-decision count and total/mean/maximum hero latency. There is no latency estimate for an unreturned or rejected decision. Mean/maximum latency are null if no hero action committed.
- A deterministic outcome hash excluding timestamps, elapsed times, PIDs and repeat identity. Exact repeats of the same seeded setup should match; timestamps and timings are expected to differ.
- Failures with safe codes and stages. Raw exception text and upstream responses are not persisted. `policy_initialization_error` identifies an unimportable/missing factory, constructor failure or missing `decide`; `policy_decision_error` identifies a raised adapter error. Dedicated codes include `invalid_policy_response`, `stale_policy_response`, `illegal_policy_action`, `hand_limit`, `action_limit`, `timeout`, `worker_exit`, `chip_conservation` and `payout_conservation`.

Chip conservation is checked after initialization, each action and each new hand. The flag is null before the first check, true when every received check passed, and false if any check failed. On timeout or crash, counters and chip totals reflect the last received checkpoint, not an invented final state. The action log includes any committed action received before that checkpoint. No partial result is counted as completed.

Summary groups keep split, policy and scenario separate and show attempts, completions, failures, unique seeds, completed unique seeds, mean prize units and mean finishing position. Means use only completed tournaments; failures must be inspected because excluding them can bias a comparison. No confidence interval is asserted for this small smoke run. Prize units are the configured share of 100 tournament prize units, not money, cash profit or monetary ROI. Simultaneous eliminations can share a place and split prizes according to the existing engine.

Tuning and held-out seeds must be disjoint. Duplicate seed entries are rejected; `--repeats` deliberately reruns the same setup and does not create independent samples. The harness labels held-out runs but cannot prevent a researcher from tuning after inspecting them. Freeze policy versions and configurations before interpreting a held-out result. The current split holds out seeds only, not opponents or policy families.

Reproducibility requires unchanged source, dependencies, configuration, adapter and seed. The engine shares its RNG between deck shuffling and standard-opponent action sampling. Different policies can change the number/order of actions, random draws and eliminations. Therefore equal seeds across different policies do not guarantee identical future deals. Pausing or other interactive controls also increment versions and can change the seeded equity estimates; this runner defines a fixed action/new-hand version schedule without those controls.

Hero remains seat 0, the initial button is fixed, and opponent seat assignments remain fixed. Natural button movement over a tournament is not balanced seat rotation. Results are specific to those assignments, shallow default stacks, blind schedule, profiles and action abstraction. A few wins, or a difference between sample means, cannot establish strong or unexploitable play.

## Checks and measured milestone evidence

Executed locally on this branch:

```sh
cd apps/api
.venv/bin/python -m pytest tests/test_evaluation.py -q
.venv/bin/python -m pytest -q
```

The initial focused evaluation suite passed 23 tests. After adding edge cases, the final complete API suite passed 45 tests, including 26 evaluation tests. Coverage includes repeat outcomes, saved reports, private observation fields, mutated inputs, stale/illegal/malformed responses, safe adapter failures, async policies, hard timeout cleanup, action/hand bounds, split validation, pressure-action legality, comparison with the existing heuristic agent, and CLI failure output. Existing API tests also exercised independent interactive table processes and local persistence. Existing provider tests use mocks; the new built-in evaluation path makes no provider requests.

The expanded smoke command above completed 16 of 16 tournaments, with four unique seeds (two tuning and two held-out), two scenarios and two exact repeats. All eight repeat pairs matched their outcome hashes. Across attempts there were 96 hands, 774 committed actions and 68 hero decisions; every chip-conservation check passed. Measured total tournament duration was about 14.09 seconds on this machine and is not a performance guarantee. Standard-scenario mean hero awards were 0 prize units in both splits; repeated-shove means were 18 tuning and 6 held-out prize units. Each group has only two unique seeds. These numbers establish a working measurement path, not a meaningful strategy ranking. Machine-readable results are retained in this checkout's ignored `apps/api/data/evaluation/milestone-smoke/` directory and can be regenerated with the command above.

OpenRouter, hosted LangSmith and Supabase were not verified. No external resources were created and no paid calls were made.

## Integration requests

No engine, API dependency, shared contract, frontend or interactive worker changes are required. Integrate the evaluation package, its tests and this document, then rerun the combined API suite after the other workstreams merge. Existing `assess`, `baseline`, `Tournament.observation`, `legal` and `apply` semantics are dependencies. Their source hashes in results help identify baseline drift.

Future engine extensions should be reviewed separately: configurable hero seat and opponent permutations for balanced seat rotations; separate RNG streams or explicit per-hand deck schedules for stronger cross-policy comparisons; public-state fixture construction for exact bubble, short-stack and side-pot pressure cases; and a stable engine revision identifier. Until those interfaces exist, this milestone uses complete real tournaments and action-selector scenarios without mutating private engine state. It does not modify trace contracts or connect the separate strategy branch automatically.

## Stage 1 protocol 2 correction

The integrated delivery supersedes protocol 1 results for future comparisons. Reports retain `schema_version: 1` for structural compatibility and add `protocol_version: 2`. Attempt table IDs are random opaque UUIDs; public evidence uses table-local `eN` identifiers, which must be scoped to the tournament. Split, deck seed, repeat, policy name and scenario remain in controller-owned result records only. IDs differ across exact repeats and are excluded from outcome hashes.

Policy constructors now receive `EvaluationConfig.policy_seed` (CLI `--policy-seed`, default 42), independently of the hidden deck seed. This is not a hash or reversible transformation of the deck seed. The same configured policy seed is used across deck seeds and repeats; it is recorded in the report and outcome hash. Changing this protocol can change tournament outcomes relative to protocol 1 even though the heuristic calculation and action weights are unchanged. Interactive workers also use the independent default policy seed 42.

Permitted observations normalize opponent names to stable within-table seat labels and reconstruct action text from public structured facts. They do not copy simulator display aliases or arbitrary event prose. Known seat-to-profile assignments, shared engine RNG streams and seed-only held-out splits remain experimental limitations; opponent-policy randomization and realistic redesign are outside Stage 1. Trusted Python adapters still are not an OS sandbox. They must not be given controller files, spectator APIs, source-retrieval tools or manifests as playing-agent inputs.
