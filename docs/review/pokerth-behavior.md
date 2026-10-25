# PokerTH behavior review

Reviewed on 2026-10-25 using application commit `24c8c13`, real native PokerTH opponents and the existing heuristic hero. No provider calls were made and no opponent policy was modified.

The environment is usable for development of this side project. The sample passed mechanical checks and produced varied preflop and postflop play. It does not establish equivalence to human players or solver quality. Rayner clarified that an isolated strange action must not be used to dismiss the simulator. Review recurring conditional behavior, and keep action legality, adapter fidelity and strategic judgment separate. The observations here do not block Stage 2B.

## Sample and mechanical validity

Six separate games started at 100 BB, with 100 hands per blind level. Each was sampled for its first 25 hands. These are 150 hands, not six completed tournaments. Seeds and configurations are recorded in [the compact evidence](pokerth-behavior.json). A rerun to verify the audit script reproduced the same counts and is not an additional sample.

| Observation | Result |
| --- | --- |
| Actions checked against the observed PokerKit legal menu | 1,291 |
| Real native opponent decisions | 1,054 |
| Illegal actions or chip-conservation failures | 0 |
| Native player-hand opportunities with voluntary preflop action | 700 |
| Opportunities with a paid call or raise | 161 / 700, 23.0% |
| Opportunities with a preflop raise | 118 / 700, 16.9% |
| Hands with flop / turn / river decisions | 73 / 65 / 56 |

The game counts and action opportunities are correlated, not independent observations of human behavior. Opponents share one policy family. Starting at six players does not mean every sampled hand stays six-handed. Only 11 sampled flops had three or more active participants at a recorded decision, so multiway judgment is particularly under-sampled. The hero's simple heuristic also influences the situations the bots face.

## A plausible line in the live game

The live review table is `28806ca653e9`, named "PokerTH review · 100 BB". Hand 4 provides a straightforward example visible in replay:

- Player 4 holds A♥7♥ in the small blind and opens to 30 at blinds 5/10. Player 5 calls from the big blind with Q♥9♣.
- Both check the K♠T♥3♣ flop and the 9♥ turn.
- On the 2♥ river, Player 4 has the nut flush and bets 30 into 60. That is a plausible value bet. The UI calls this "raises to 30", although it is the first bet on the street.
- Player 5 calls 30. The required break-even pot share is 30 / 120 = 25%. Judging that bluff-catch requires a belief about the bettor's range; seeing the flush as a spectator is not a valid reason to declare the call wrong.

The screenshot in [hand-4-river.png](../qa/pokerth-behavior/hand-4-river.png) captures the decision before the call. The revealed cards are spectator information and never enter the hero's observations.

## Integration fidelity and observations to revisit

**Bet sizing.** The adapter changed 178 of 198 native bet/raise targets to fit the current discrete legal menu. That exact-match figure alone exaggerates the concern: 19 of 198 targets changed by more than 20%, and none changed by more than 40%. For example, a native bet of 58 into 85 became 42. Both sizes are legal and plausible; they are different policies. Preserving exact legal native sizes is a possible improvement, rather than evidence that PokerTH is unusable.

**Position shortcut and an unusual bluff.** In sampled run 1, hand 8, the small blind held A♣9♥ against A♦K♦ in the big blind. The successive raise-to amounts were 30, 60, 180, 360 and 1,080. The final native target was already 1,080, so menu snapping did not create that large bluff. A rare aggressive bluff can be part of a useful imperfect opponent model. This one example does not measure its frequency, profitability or realism.

The current adapter counts opponents who have not yet acted on the street. PokerTH's `inPosition` shortcut tests whether that count is zero. On the return action in this hand, that classified the small blind as in position. Replaying the two small-blind reraises with the same cards, personality and native random seed, changing only that count from zero to one, produced folds. This demonstrates sensitivity to a simplified position input. It does not prove that folding is optimal or that a global replacement of the field would improve the whole policy. Investigate across comparable spots before changing native behavior.

**Postflop response mix.** Across 67 native decisions facing a postflop bet, the sample contained 40 calls, 26 folds and one raise. This is descriptive evidence to compare in a larger sample. It is not a human-reference verdict. Different board, range, player-count and sizing distributions can substantially change those rates.

## Follow-up approach

Keep using PokerTH for strategy development. Record recurring patterns by position, stack depth, prior aggression, board and bet size rather than labeling isolated losing or unusual plays as defects. Treat deliberate opponent mistakes as potentially useful exploit targets. Consider exact native sizing and clearer bet/raise display labels as separate integration improvements. Stronger realism claims would require representative comparisons or human hand review beyond this small sample.

The reproducible controller-only audit is [scripts/audit_pokerth_behavior.py](../../scripts/audit_pokerth_behavior.py):

```sh
python3 scripts/build_pokerth.py
apps/api/.venv/bin/python scripts/audit_pokerth_behavior.py
```

It writes detailed actor observations and controller configuration to ignored `apps/api/data/pokerth-review-20261025/audit.json`. These research records, native-policy knowledge and spectator cards are not agent tools or retrieval evidence. The live app's SQLite replay is stored separately at `apps/api/data/pokerth-review-20261025.sqlite`.
