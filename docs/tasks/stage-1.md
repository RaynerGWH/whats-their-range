# Stage 1: Trustworthy development baseline

Assigned on 2026-10-25 (Asia/Singapore) following Rayner's request to direct Stage 1 to an existing worktree.

Owner: the existing chat **Backend: tracing and persistence**, thread `01a1724e-8481-7b11-8ffe-b20ba13aed32`, host `local`.

Execution checkout: `/Users/rayner/.codex/worktrees/1675/whats-their-range`.

Delivery branch: create `feat/baseline-integration` from the audited backend milestone `9c63568`, after verifying the actual checkout. Keep `feat/observability` and the other milestone branches intact. Do not modify the original preview checkout or the integration chat's checkout. This assignment authorizes local integration and necessary cross-module fixes in the delivery branch, superseding the original backend milestone's no-merge and narrow file-ownership restrictions for this work only.

## Read first

Read the live [shared project context](../project-context.md), [agent direction](../agent-direction.md), [roadmap](../roadmap.md), existing architecture and contracts, and the workstream integration notes. The canonical shared documents are in `/Users/rayner/Documents/ChatGPT/whats-their-range/docs/`; use that absolute location when a local copy is absent.

The backend checkout already has intentional, uncommitted shared-context changes to `AGENTS.md`, `README.md` and new `docs/shared-context.md`. Preserve them. After creating the delivery branch, verify and commit these coordination-only edits separately if needed to obtain a clean integration starting point. Do not reset, discard or attribute them to the original backend milestone.

## Implementation scope

1. Review and integrate the first-milestone commits one at a time in the delivery branch. Backend `9c63568` is the starting point; frontend `5d34afa`, strategy `6f44297` and evaluation `34c7e2d` are the audited inputs. Verify their current refs and record the exact revisions integrated. Resolve compatibility issues deliberately. Preserve existing contracts and legacy replay compatibility; document any necessary compatible extension.
2. Fix the confirmed evaluation metadata leak. `runner.py` currently encodes split, deck seed, repeat, policy and scenario in `table_id`, which reaches observations and event IDs. Use opaque agent-visible identifiers, keeping reproducibility metadata in evaluator-owned records. Audit indirect leakage through evidence IDs, policy initialization seeds, names/profile aliases, messages, tool outputs and traces. Treat raw controller state separately from player inputs. Check whether the same game seed supplied to policy factories exposes the hidden deck and separate those concerns as needed. Preserve reproducibility without requiring opaque identifiers to match across runs; version any changed evaluation protocol.
3. Verify the combined privacy boundary. Backend allowlisting and safe error handling must protect actual outbound model payloads and stored/exported traces, not only field names. Tests should show that forbidden metadata or spectator-only changes cannot alter the permitted context when public information is held constant. Preserve legitimate public evidence and within-tournament opponent identity.
4. Verify the real trace backend with the trace explorer. Cover running and completed traces, recorded errors/fallback, authentication, historical decisions without trace IDs, pagination, cross-table selection, replay and unavailable data. Resolve the delayed LangSmith URL behavior: completion currently stops frontend polling although export can update the link later. Either implement a bounded refresh approach or make manual refresh behavior explicit and tested. Keep local records independent of export availability.
5. Preserve the existing heuristic and action-selection behavior. Integrate strategy as a tested available module; Stage 1 does not activate a new strategy policy or implement the Stage 2 model-directed tool loop. Keep legality and state-version enforcement, per-table ownership, deadlines and call budgets.
6. Prepare a small reproducible hand-review pack for Rayner, with permitted observations, public action sequences and clearly identified discussion points. Do not assert strategic approval or create fabricated solver answer keys. User review of that pack can remain pending while engineering work completes.

Do not expand this into solver selection/integration, realistic-opponent redesign, broader paid model evaluation or deployment. Record genuine follow-up needs instead.

## Validation and isolation

- Run the combined API suite, frontend type checks/tests/production build, and focused regressions for the leakage and interface fixes.
- Run a modest reproducible evaluation smoke set and verify completion reporting, chip conservation and repeat outcome comparability. Do not run hours of simulations.
- Exercise two independent table processes, real local trace endpoints, replay and restart/interruption behavior using isolated temporary databases. Keep other chats' databases and servers untouched.
- Inspect the combined UI at desktop and narrow widths using supported browser tools where available. If unavailable, report the missing check explicitly rather than claiming it passed.
- Use backend worktree ports 8012/5175 with matching origins and worktree-local dependencies/data. Check for occupied ports; never stop another chat's server. Keep original ports 8000/5173 and frontend worktree ports 8013/5176 undisturbed.
- Mock OpenRouter and LangSmith. Hosted verification, paid calls, pushes, deployment and cloud-resource creation are outside this assignment. Local disposable PostgreSQL is optional and must be reported separately.

## Delivery

Commit the work locally on `feat/baseline-integration`. Report the final commit, integrated input revisions, tests actually run, smoke counts, privacy findings/fixes, UI evidence, remaining risks and the hand-review pack path. Write a concise `docs/stage-1.md` integration report in the delivery checkout. Distinguish engineering completion from pending strategic hand review.

Do not merge the result into `feat/integration`; the integration chat will review it. Do not edit the canonical shared brief, start other agents/chats, message other chats or create recurring monitors. Your normal completion report is available for the integration chat to inspect. Include the shared-context revision used.
