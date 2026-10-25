# Strategy milestone

Branch: `feat/strategy`. Follow `docs/parallel-work.md` for ownership and the `analyze` contract.

Build the first explicit hand and bluff candidate analysis as a separate deterministic module. Inspect legal actions, current hand history, position, effective stacks, number of opponents, pot, board, own cards, and available hand metrics. Consider bluffing as part of the current decision, with conditional response assumptions and alternatives. Distinguish value bets, pure bluffs, and semi-bluffs where the supplied information supports that distinction. Never infer an opponent tendency from a one-off action or present uncalibrated probabilities as measured reads.

Keep the first version small and honest. Do not invent a GTO dataset, calibrated ranges, or an ICM solver. Scope any fold-equity/break-even arithmetic carefully to its assumptions, including side-pot eligibility and future betting. Check primary poker/solver sources when relying on specialized formulas and document those sources. Treat descriptive ICM as a limitation until action values are actually modeled.

Add meaningful tests for legality, input immutability, deterministic output, sparse evidence, multiway and short-stack limitations, and inappropriate certainty. Preserve the existing agent, game engine, and heuristic. Provide an integration example and describe how candidate analysis could later become parallel graph nodes without making multiple speculative LLM calls now.

Read the existing private observation and metrics implementations, but do not edit `agent.py`, `workers.py`, `game.py`, storage, or frontend. Backend owns those files during this milestone. No live model calls or deployment are necessary. Commit the module, tests, and `docs/strategy.md`, then report the commit and integration requirements.
