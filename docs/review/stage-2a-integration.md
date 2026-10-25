# Stage 2A integration review

Reviewed on 2026-10-25 (Asia/Singapore) under Rayner's authorization to commit and merge completed, validated milestones into local `main`.

Backend delivery: `a82a15265b9355f7f4e2884babec1d0bcc3eafa1` on `feat/pokerth-opponents`. The reviewed integration commit is `e99817bc0a11c444380f82c96e26cc21e74a0f59`. Local `main` was fast-forwarded from `580c9ce` to this commit after the checks below. Documentation-only follow-ups may advance it further. No remote push or deployment was made.

The review inspected the native bridge and reproducible build, observation reconstruction, public statistics, RNG separation, action normalization, worker and evaluation integration, configuration/UI changes and native regression tests. No blocking issue was found. The only merge conflict was in README.md; the resolution retained current baseline wording and database documentation while incorporating the native setup and repository-root container build context. Application code, native sources, scripts, contracts, manifests and CI configuration match the backend delivery exactly.

Independent checks in `/Users/rayner/Documents/ChatGPT/whats-their-range`:

| Check | Result |
| --- | --- |
| `python3 scripts/build_pokerth.py` | Passed with pinned vendored checksums and matching native version |
| `apps/api/.venv/bin/pytest -q apps/api/tests` with external tracing disabled | 128 passed, 1 skipped in 25.93 seconds |
| `npm run check` | Passed |
| `npm run test -w apps/web` | 16 passed |
| `npm run build` | Passed |
| `git diff --cached --check` | Passed before the merge commit |

The API suite independently exercised real native opponents, complete reproducible tournaments, two independent production workers, controls, legal actions, side pots, privacy boundaries and saved traces/replay. The external model transport was mocked. The skipped test is the opt-in PostgreSQL check. The compiler emitted the documented warning about adjacent string literals in the unchanged upstream preflop chart.

The backend's recorded 20-tournament smoke set, ten matching repeat pairs and browser evidence were inspected in the [delivery report](../stage-2a.md) and supporting files. That full recorded set and manual browser checks were not repeated during integration. Test reruns are not additional independent poker-performance evidence. Docker/Linux builds, hosted providers and deployment were not exercised.

This accepts Stage 2A as the playable opponent environment: PokerKit owns the game, real PokerTH engine 4 opponents act through the permitted observation and legal menu, and the existing hero interface can play alongside them. Human realism and playing strength remain unverified. The hero still uses its fixed preparation graph and optional single model call or heuristic mode. The fuller LLM strategy, model-directed tools, competing hypotheses and genuine solver access remain Stage 2B.
