# Active task: Stage 2A

Implement actual PokerTH engine 4 opponents in the PokerKit application on
`feat/pokerth-opponents`, based on Stage 1 commit
`01f3a8120790fbdad4d8589962be6d90fcb7d8b7`.

The earlier leakage question is resolved. Continue implementation through native
build, permitted-observation adapter, workers, evaluation, minimal UI wiring,
complete real games, tests and `docs/stage-2a.md`. Preserve the existing hero
`Agent.decide` interface. Do not stop at an explanation or plan.

Canonical brief: `/Users/rayner/Documents/ChatGPT/whats-their-range/docs/tasks/stage-2a.md`.
Shared context revision: 12. PokerTH revision:
`0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba` (v2.1.10).

No paid calls, remote pushes, deployments, other-checkout edits, main merges,
extra agents, cross-chat messages or automation. Use isolated ports 8012/5175.

Progress: branch created; inspecting native source and application contracts.

Native milestone committed as `6f3b965`. Worker/evaluation adapter and UI selector
implemented. Nineteen native tests pass, including complete two-worker games with
heuristic and mocked-provider heroes, real PokerTH opponents, controls and replay.
Remaining: combined checks, recorded smoke set, browser QA and final delivery report.

Stage 2A is complete. Final implementation/evidence revision: `c2131d4`.
Final checks: 128 API tests passed, one optional PostgreSQL skip; 16 frontend
tests, TypeScript and production build passed. Recorded 20 native tournaments,
all complete, all ten repeat pairs matching. Two additional UI-created games
completed and replay/traces survived restart. Both QA servers and browser closed.
See `docs/stage-2a.md` for the full delivery. Stage 2B is not implemented here.
