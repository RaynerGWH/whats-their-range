# Stage 2A: Playable PokerTH opponents

Assigned on 2026-10-25 (Asia/Singapore) following Rayner's instruction to give the backend agent the playable game integration, before implementing the fuller strategy layer.

Owner: **Backend: tracing and persistence**, thread `01a1724e-8481-7b11-8ffe-b20ba13aed32`, host `local`.

Execution checkout: `/Users/rayner/.codex/worktrees/1675/whats-their-range`.

Create delivery branch `feat/pokerth-opponents` from the verified Stage 1 delivery `01f3a8120790fbdad4d8589962be6d90fcb7d8b7`. Preserve `feat/baseline-integration` and all other worktrees. If the checkout changed, inspect and preserve its work before proceeding. Make small, meaningful local commits as coherent pieces become complete. The integration chat will review completed work and merge solid milestones into local `main`; do not merge or push from this worker.

## Finish line

A user can start a six-player tournament in our application, watch five actual PokerTH-controlled opponents play against the existing hero agent, inspect hero decisions and public action history, and finish the tournament through eliminations and heads-up play. PokerKit remains authoritative for the game. Two tables run independently. This must exercise the actual native opponent implementation and full action-to-next-state loop, not only mocked bot outputs or isolated example hands.

The existing `Agent.decide(observation)` path remains the hero interface. Preserve its stochastic heuristic and configurable OpenRouter mode, structured decisions, traces, deadlines and labeled fallback. The separately integrated candidate-analysis module is not yet a complete strategy. New qualitative strategy, a model-directed LangGraph tool loop and solver integration are the following milestone, not requirements for this environment task.

## Context and source

Read the live canonical brief, agent direction, roadmap, and [PokerTH assessment](../research/pokerth.md) in `/Users/rayner/Documents/ChatGPT/whats-their-range/docs/`, plus local `docs/stage-1.md`, architecture, contracts and applicable AGENTS.md instructions. Use shared-context revision 11 or later.

Use PokerTH `v2.1.10`, commit `0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba`. The useful interface is `AiEngine4::decide(AiSituation, AiPersonality)`. Four C++ implementation files form the tested core: `aiengine4`, `equitycalculator`, `holecardsrange` and `handevaluator`, with their headers, `game_defs.h` and the `Tools::GetRand` dependency.

An isolated build exists in `/private/tmp/wtr-pokerth-research-a291gfvr`. It passed seven equity checks and 200 synthetic decisions. Its fixed-seed RNG bridge is only a research aid, not a finished runtime design. Recover source from the pinned upstream commit if temporary files are absent. Verify provenance, retain upstream copyright/license notices and document any modifications. Deliver a reproducible build and setup independent of those temporary paths and of the full Qt desktop application.

## Implementation

1. Build a small native or subprocess bridge and a Python opponent-policy adapter. Choose the simpler reliable approach for the existing worker model. Keep runtime inputs and errors bounded, validate native inputs, and clean up resources on worker shutdown. Document build prerequisites and make fresh local setup work. If PokerTH is selected but unavailable, produce a clear setup error; do not silently substitute the legacy bots.
2. Construct native observations from the acting player's permitted observation and public action history. Translate cards, street, pot and committed bets, blind sizes, position, remaining opponents and public statistics explicitly. No opponent hole cards, actual future cards, deck seeds or spectator data may enter a player's policy input. Do not pass the complete mutable Tournament object into the policy.
3. Normalize PokerTH intentions to actual available legal actions and enforce the observed state version through PokerKit. PokerTH's raise value is an increment above the current highest bet, and upstream relies on its own execution layer for final legality. Check stack caps, short all-ins, minimum raises and whether action has reopened. If mapping to our discrete action menu is needed, document and test that approximation rather than claiming exact upstream play.
4. Maintain public opponent statistics across hands and reset them between independent tournaments. Define opportunity counts consistently. Use separate randomness for decks, opponent policy choices and private personality assignments. Make reproducibility explicit without exposing seeds to the hero. Randomize the association of neutral player identities and hidden personalities between tournaments, keeping identities stable within a tournament. Avoid identical fixed RNG streams for every seat or dependence on the deck RNG.
5. Wire the adapter into actual interactive table workers and the evaluation path where appropriate. New demo tables should be able to use PokerTH opponents directly, with a clear explicit legacy mode retained for comparison and historical compatibility. Make necessary compatible API/config/frontend changes in this worktree. Keep UI labels minimal and distinguish opponent policy from the hero's decision mode. Existing saved games/replays must remain readable.
6. Preserve the current hero decision path and make its replacement by the later strategy graph straightforward. Demonstrate a full game using the existing heuristic hero, then exercise the actual `Agent.decide` provider path with mocked responses while real PokerTH opponents act. The user-configured live OpenRouter path must remain usable, but paid/live-provider calls are not authorized by this task. Label mocked tests honestly and do not block local completion on credentials.
7. Keep all opponent personality settings, internal source, private RNG state and private decision inputs outside hero prompts, tools, retrieval and model traces. Preserve Stage 1's opaque identifiers, sanitized public facts, table isolation and local trace persistence. Controller diagnostics must not become agent evidence.

This task authorizes necessary cross-module changes within the delivery checkout, including minimal frontend wiring and build configuration. It supersedes the original backend-only file ownership and Stage 1's prohibition on opponent redesign for this milestone. It does not authorize a new solver, a new hero strategy, deployment, paid services or changes to other checkouts.

## Verification and delivery

- Exercise the real native adapter against representative legal PokerKit observations: each street, multiple player counts, short stacks, all-ins, side pots and restricted raising. Cover malformed native responses, unavailable builds and action normalization.
- Run a modest recorded set of complete tournaments with actual PokerTH opponents, including repeat runs with independent deck/policy seeds. Check completion, chip conservation, non-negative stacks, legal transitions and reproducibility. At least one run must use the real interactive worker and existing hero decision boundary, not just the evaluation harness.
- Test that changing hidden opponent configuration or spectator state cannot change hero inputs when public facts are held fixed. Verify policy RNG does not consume deck RNG, neutral identities do not encode personalities, and memory does not cross tables/runs.
- Verify two independent worker processes, pause/step/resume, termination, replay and cleanup. Inspect the combined UI and its hero traces. Use isolated worktree-local databases and reserved ports 8012/5175, checking availability first; do not disturb other servers.
- Run the combined API suite and applicable frontend type checks, tests and build. Mock external providers and telemetry; distinguish those checks from real native opponent execution.
- Commit implementation in coherent pieces and write `docs/stage-2a.md` with the final revision, upstream revision, setup/demo commands, tests actually run, game counts, representative public hand records, information-boundary evidence and remaining limitations. Report any action-menu approximation and make no solver or human-realism claims.

Do not edit canonical shared planning documents, start more agents or chats, message other chats, create monitors, merge into `main` or push. Report normally in this chat when complete. The integration chat will review the delivery under Rayner's newly authorized local-merge workflow.
