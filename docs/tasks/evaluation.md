# Simulation and evaluation milestone

Branch: `feat/evaluation`. Follow `docs/parallel-work.md` and preserve the existing simulator and policy interfaces.

Build a repeatable local evaluation runner under `wtr.evaluation`. It should run seeded complete tournaments without frontend pacing, keep the existing heuristic as a named baseline, support a replaceable policy adapter using permitted observations, and save machine-readable results plus a concise summary. Record configuration, policy/version identifiers, seeds, hands, actions, finishing position, prize units, chip conservation, failures, and measured latency. Keep prize outcomes distinct from cash profit or monetary ROI.

Support repeated seeds and an explicit training/tuning versus held-out split. Preserve reproducibility; do not assume a common seed gives identical future deals when policies consume randomness differently. Document that limitation and any seat-rotation limitations without changing the core engine during parallel work. Provide a small smoke run by default and configurable larger runs. Do not launch hours of simulation or paid provider calls automatically.

Add targeted scenarios/adapters for pressure such as repeated shoving, and tests showing the harness records results and exposes legal actions without leaking hidden cards or opponent profiles. Opponent profiles may be configured by the simulation harness but never forwarded into policy input. Support clear errors for invalid policies and bounded execution to catch stalled tournaments. A separate strategy branch is being built, so leave an adapter seam and test it with the existing baseline or a simple legal test policy.

Do not edit `game.py`, `agent.py`, `workers.py`, shared contracts, or frontend. Record requested engine extensions in `docs/evaluation.md` for integration. Test the runner on a modest seed set and report sample counts honestly. Commit code, tests and documentation, with reproducible commands. No live API credentials are needed.
