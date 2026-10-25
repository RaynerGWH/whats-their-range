# Baseline before agent strategy development

Checkpoint date: 2026-10-25 (Asia/Singapore). Annotated Git tag: `baseline/stage-2a`.

Rayner requested committing and merging all current work into a solid baseline before implementing the fuller poker agent. This checkpoint consolidates that work on local `main`. It is a verified development baseline for Stage 2B.

## Included

- PokerKit tournament state, legal betting, all-ins, side pots, eliminations and payouts.
- Five real PokerTH engine 4 opponents with separate policy randomness, private shuffled personalities and table-local public statistics.
- Independent table workers, observed-state validation, pause/run/step controls and local persistence.
- The spectator UI, public action history, replay and execution trace explorer.
- The existing heuristic hero and bounded optional single-call OpenRouter path.
- The strategy analysis module, available for later tool integration, plus the evaluation harness and behavior audit.
- Shared project decisions, task briefs, pinned native source/build instructions and recorded verification evidence.

## Consolidation

All application deliveries were already integrated through Stage 1 and Stage 2A. The final audit found only uncommitted shared-context notes in four older checkouts. Those notes were committed and their branches merged individually. Duplicate README sections introduced by the identical note additions were consolidated into the current wording.

| Worktree branch | Final delivery or note commit included |
| --- | --- |
| `feat/tournament-skeleton` | `59d70c9` |
| `feat/strategy` | `2a311a1` |
| `feat/trace-explorer` | `380ed06` |
| `feat/evaluation` | `39bed4c` |
| `feat/pokerth-opponents` | `a82a152` |
| `feat/integration` | Consolidated baseline and checkpoint documentation |

All local branch tips are ancestors of the checkpoint, and all six worktrees were checked for a clean Git status. Older worktrees retain their feature branches; their complete histories are preserved. No remote push or deployment is part of this checkpoint. Generated binaries, dependencies, runtime databases and local configuration remain ignored; tracked build scripts and compact evidence reproduce or document the relevant results.

## Verification

The final consolidation changes documentation and merge history. Application implementation, application tests, native sources, manifests and CI configuration are unchanged from the independently verified Stage 2A integration `e99817b`. Checks were not rerun solely for this documentation consolidation.

- Native build and source checksums passed.
- 128 API tests passed; the optional PostgreSQL test was skipped.
- 16 frontend tests, TypeScript checks and the production build passed.
- Real native tournament and worker tests covered legal actions, chip conservation, privacy, isolation, replay and lifecycle controls.
- The subsequent behavior audit sampled 150 hands and 1,054 native decisions without illegal actions or chip-conservation failures. The audit script was executed successfully and its repeated verification was not counted as extra evidence.
- Final Git checks verify branch ancestry, clean worktrees and whitespace consistency.

Detailed evidence is in the [Stage 2A integration review](review/stage-2a-integration.md), [delivery report](stage-2a.md) and [behavior review](review/pokerth-behavior.md).

## Next milestone

Stage 2B implements the model-directed LangGraph tool loop, richer public opponent evidence, competing hypotheses, conditional poker analysis and genuine solver/reference access for supported spots. The LLM remains the final poker decision-maker, with backend legality and state-version enforcement.

No solver is integrated at this checkpoint. Hosted provider operation and strategic playing strength have not been established by these local checks. These are recorded scope limits; the playable environment is available for the next development stage.

New Stage 2B branches should start from `baseline/stage-2a` or a later reviewed `main`, and read [shared project context](project-context.md) before making interface decisions.
