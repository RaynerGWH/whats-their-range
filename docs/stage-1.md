# Stage 1 delivery

Engineering milestone complete on `feat/baseline-integration`, 2026-10-25 (Asia/Singapore). Implementation and evidence commit: `d97b465`. This report is committed separately after that implementation. Rayner's strategic review remains pending.

Shared context: started from revision 4, reread revisions 6 and 7 during execution, and used revision 7 for the handoff. The noncommercial research/demo direction is preserved. Stage 2's model-directed tool loop, solver access and opponent redesign are not implemented here.

## Integrated history

| Input or change | Commit | Delivery history |
| --- | --- | --- |
| Backend starting point | `9c63568` | Branch created from this verified commit |
| Pre-existing shared-context documentation | `7683e68` | Preserved and committed separately, not attributed to backend implementation |
| Frontend trace explorer | `5d34afa` | Merge `62f4450` |
| Strategy analysis | `6f44297` | Merge `079f16f` |
| Evaluation | `34c7e2d` | Merge `bbcb16a` |
| Privacy and integration fixes, review pack, QA evidence | `d97b465` | Implementation commit |

All three inputs merged without conflicts. The original milestone branches remain at their audited revisions. Nothing was merged into `feat/integration`, pushed, deployed or changed in another worktree. Shared contracts under `contracts/` are unchanged. The strategy module is available and tested but remains disconnected from live action selection.

## Findings and fixes

- Evaluation table IDs previously exposed split, deck seed, repeat, policy and scenario. They are now random opaque UUIDs. Public event identifiers are table-local `eN` values, without controller metadata. Controller result records retain the reproduction settings. Cross-table consumers must scope evidence IDs by table.
- Policy factories previously received the hidden game seed. Evaluation protocol 2 uses a separately configured policy RNG seed (`--policy-seed`, default 42), unrelated to the deck seed. Interactive workers also use the independent default policy seed 42. The existing heuristic calculations, action weights, legal menu and fallback selection logic remain unchanged. Protocol 2 outcomes can differ from the old seed-coupled protocol, so its `protocol_version` is recorded and included in outcome hashes.
- Both `Tournament.observation()` and the agent boundary reconstruct opponent names as stable `Player N` seat labels and action text from structured public facts. Arbitrary simulator aliases, event prose and legacy ID prefixes cannot enter the actual model messages. Existing stored replay is read without rewriting old records.
- Semantic privacy tests vary hidden configuration, spectator cards, future deck order, names and event prose while keeping public facts fixed. They assert identical permitted observations, outbound mocked-provider messages, tool outputs and local/exported trace payloads. Legitimate public actions and evidence references remain usable. Seed/split/scenario/policy metadata is checked inside the actual spawned evaluation policy boundary, including factory initialization.
- Completed traces can receive a LangSmith link after automatic polling stops. The UI now explicitly says to refresh when the link is unavailable. Refresh fetches the selected completed detail as well as the list. A regression test supplies a delayed link and verifies it appears after refresh.
- Live browser restart testing found an idle WebSocket handler that did not consume disconnect events. It could hold Uvicorn shutdown open when a paused table had no new snapshots. The handler now waits for disconnects alongside snapshot publication and cancels its receiver on exit. The regression test and a real shutdown with a connected browser both pass.

The raw controller state and spectator API still contain seeds and private cards by design. They are not player inputs. No source retrieval, controller-manifest retrieval or spectator API tool is exposed to the model. Local Python policy factories are trusted extension code, not a security sandbox.

## Checks actually run

From the delivery root:

```sh
apps/api/.venv/bin/pytest -q apps/api/tests
npm run check
npm run test -w apps/web
npm run build
git diff --check
```

Final API result: **108 passed, 1 skipped**. The only skip is the opt-in disposable PostgreSQL test. Frontend result: **16 tests passed**, TypeScript passed, production build passed. Ruff's isolated `F` checks passed on changed Python files. Focused privacy, API lifecycle and frontend regressions also passed during development.

The combined tests cover two independent table process IDs and isolated trace roots, legal/stale action rejection, model deadlines/caps, response validation/fallback, actual parallel span timing, in-flight trace IDs, authenticated list/detail routes, cursor pagination, cross-table rejection, trace retention, storage restart, interruption, legacy replay without trace IDs, safe errors, SDK export construction/failure and the new semantic privacy boundary. UI tests cover selection, stale responses, running poll cleanup, legacy/authentication states, pagination and delayed link refresh.

No hosted OpenRouter, LangSmith or Supabase connection was used. Provider and telemetry tests are mocked. Local PostgreSQL was verified in the prior backend milestone, but was **not rerun for Stage 1**. This delivery's persistence and live app checks use isolated SQLite files.

## Evaluation smoke evidence

From `apps/api`:

```sh
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false .venv/bin/python -m wtr.evaluation \
  --tuning-seeds 1,2 --held-out-seeds 101,102 --repeats 2 \
  --scenario standard --scenario repeated-shove \
  --output data/stage1/evaluation-final
```

The 16-tournament set was run twice during integration (32 executions, still only four unique seeds). All corresponding outcome hashes matched across those runs. The final set completed **16 of 16**, with all **8 repeat pairs matching**, **68 hands**, **646 committed actions**, **112 hero decisions**, and all chip-conservation checks passing. No failures were counted as zero prizes. These are execution/reproducibility checks, not a strategy ranking.

[Committed smoke summary and runtime/source fingerprints](review/stage-1-smoke.json). The complete controller-owned action logs remain in this worktree's ignored `apps/api/data/stage1/evaluation-final/results.json`; rerunning the command reproduces outcome hashes, not timing or opaque IDs. Use a new output directory because the runner refuses overwrites.

## Browser and lifecycle evidence

Supported in-app browser checks used API `8012`, web `5175`, matching origins, a private test control token and worktree-local dependencies/database. The test-only bootstrap `apps/api/tests/stage1_preview.py` intercepts every provider call, including spawned workers, and disables external tracing. It simulates three-second provider latency and a safe failure on even hands. It is never imported by the production API.

Verified in the combined app:

- Access denied before entering the test token, followed by authenticated session and trace access.
- Two independent tables: one heuristic and one clearly labeled mocked-provider table. Pausing and switching tables preserved the other table's state and showed the correct trace root.
- Recorded running and completed traces, model inputs/structured outputs, token counts, null cost, actual timing, safe provider failure and the executed fallback.
- Hand selection with no records, replay navigation to a state without a linked decision, return to live, and archived trace access after restarting the API.
- Desktop 1440 x 1000 and narrow 390 x 844 inspection. Narrow document width equalled the viewport width (390), with no horizontal page overflow. Browser console inspection returned no warning/error entries during the checked flows.
- After the WebSocket fix, the API completed graceful shutdown with the browser connected, without a second interrupt. Temporary viewport changes were reset and the QA browser and servers were closed. Ports 8012/5175 are no longer listening.

Screenshots: [desktop](qa/stage-1/desktop.png), [narrow](qa/stage-1/narrow.png), [running trace](qa/stage-1/running.png), [provider error and fallback](qa/stage-1/fallback.png), [replay](qa/stage-1/replay.png), [persisted trace after restart](qa/stage-1/restarted.png). Pagination and delayed LangSmith linking were exercised by integration/unit tests rather than live external telemetry.

## Review pack and remaining gaps

[Read the nine-decision hand-review pack](review/stage-1-hands.md), with [complete permitted observations](review/stage-1-hands.json). The pack is generated through legal scripted play, with public action sequences, legal choices, explicitly unsolved candidate hypotheses and discussion questions. It includes paired-board multiway decisions, a direct draw hypothesis and short-stack all-in pressure. A test regenerates both pack files identically. It does not contain opponent cards, fabricated solver answers or a claim of Rayner's approval.

Engineering integration is complete within Stage 1. Remaining work is explicit:

- Rayner has not reviewed or approved the strategic decisions or tradeoffs in the pack.
- Opponent behavior remains the original coarse scripts with known fixed seat/profile assignments. Neutral labels remove direct name aliases but do not establish generalization to unknown opponents. Held-out splits still vary seeds only, hero remains seat 0, and engine RNG draws are shared across deck/opponent sampling. Opponent randomization/redesign, broader holdouts and balanced seats are later work.
- The live agent still uses the fixed preparation graph and optional single model call. Strategy candidates are not activated as a policy. There is no solver integration or Stage 2 tool loop.
- External telemetry remains best effort and bounded, without a durable retry outbox. Hosted service verification and broader performance evaluation remain unverified.
- The integration chat must review this delivery before merging into `feat/integration`. No such merge was performed here.
