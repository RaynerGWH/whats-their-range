# Stage 1 hand review

Pending Rayner review. No strategic approval or solver answer key.

Legal scripted play for discussion; candidate labels are dormant heuristic hypotheses, not live model decisions.

These are nine decisions from three legally played first hands. Hero is seat 0 (Player 1). The first two hands use scripted check/call play so every street can be reviewed; the third uses legal maximum raises by opponents. These scripts are discussion setups, not realistic-opponent claims.

All cards below belong to hero or the public board. The complete permitted observations, evidence IDs, legal menus and dormant candidate hypotheses are in [the JSON pack](stage-1-hands.json). No opponent cards, deck seeds or scenario labels enter those observations.

Recreate both review files from the repository root with `apps/api/.venv/bin/python scripts/stage1_review_pack.py`. The controller-only recipe is in that script. Byte-identical regeneration is checked. Do not pass the generator or experiment manifests to a playing agent.

There is no solver answer key. Equity assumes uniform random opponent hands; pot odds omit side-pot eligibility and hand-start ICM is descriptive. Candidate intent labels do not select an action, and this module remains disconnected from live play.

## review-01: preflop

Hero: 4d 6c, SB. Board: None. Pot: 55 chips. To call: 5 chips. Big blind: 10 chips.

Legal choices: fold, call, raise:20, raise:40, raise:70, raise:500.

Public action sequence:

- e2 (preflop): Player 3 calls 10.
- e3 (preflop): Player 4 calls 10.
- e4 (preflop): Player 5 calls 10.
- e5 (preflop): Player 6 calls 10.

Discussion:

- Which public actions support a range hypothesis, and which reads remain unsupported?
- Which legal size or passive action would you compare, and what response assumptions does that require?
- What next-street observations would change the plan, without assuming a future card?

## review-02: flop

Hero: 4d 6c, SB. Board: 9d 9s Qs. Pot: 60 chips. To call: 0 chips. Big blind: 10 chips.

Legal choices: check, raise:10, raise:30, raise:60, raise:490.

Public action sequence:

- e2 (preflop): Player 3 calls 10.
- e3 (preflop): Player 4 calls 10.
- e4 (preflop): Player 5 calls 10.
- e5 (preflop): Player 6 calls 10.
- e6 (preflop): Player 1 calls 5.
- e7 (preflop): Player 2 checks.

Discussion:

- Which public actions support a range hypothesis, and which reads remain unsupported?
- Which legal size or passive action would you compare, and what response assumptions does that require?
- What next-street observations would change the plan, without assuming a future card?

## review-03: turn

Hero: 4d 6c, SB. Board: 9d 9s Qs 9c. Pot: 60 chips. To call: 0 chips. Big blind: 10 chips.

Legal choices: check, raise:10, raise:30, raise:60, raise:490.

Public action sequence:

- e2 (preflop): Player 3 calls 10.
- e3 (preflop): Player 4 calls 10.
- e4 (preflop): Player 5 calls 10.
- e5 (preflop): Player 6 calls 10.
- e6 (preflop): Player 1 calls 5.
- e7 (preflop): Player 2 checks.
- e8 (flop): Player 1 checks.
- e9 (flop): Player 2 checks.
- e10 (flop): Player 3 checks.
- e11 (flop): Player 4 checks.
- e12 (flop): Player 5 checks.
- e13 (flop): Player 6 checks.

Discussion:

- Which public actions support a range hypothesis, and which reads remain unsupported?
- Which legal size or passive action would you compare, and what response assumptions does that require?
- What next-street observations would change the plan, without assuming a future card?

## review-04: river

Hero: 4d 6c, SB. Board: 9d 9s Qs 9c 8h. Pot: 60 chips. To call: 0 chips. Big blind: 10 chips.

Legal choices: check, raise:10, raise:30, raise:60, raise:490.

Public action sequence:

- e2 (preflop): Player 3 calls 10.
- e3 (preflop): Player 4 calls 10.
- e4 (preflop): Player 5 calls 10.
- e5 (preflop): Player 6 calls 10.
- e6 (preflop): Player 1 calls 5.
- e7 (preflop): Player 2 checks.
- e8 (flop): Player 1 checks.
- e9 (flop): Player 2 checks.
- e10 (flop): Player 3 checks.
- e11 (flop): Player 4 checks.
- e12 (flop): Player 5 checks.
- e13 (flop): Player 6 checks.
- e14 (turn): Player 1 checks.
- e15 (turn): Player 2 checks.
- e16 (turn): Player 3 checks.
- e17 (turn): Player 4 checks.
- e18 (turn): Player 5 checks.
- e19 (turn): Player 6 checks.

Discussion:

- Which public actions support a range hypothesis, and which reads remain unsupported?
- Which legal size or passive action would you compare, and what response assumptions does that require?

## review-05: preflop

Hero: 3c 6h, SB. Board: None. Pot: 55 chips. To call: 5 chips. Big blind: 10 chips.

Legal choices: fold, call, raise:20, raise:40, raise:70, raise:500.

Public action sequence:

- e2 (preflop): Player 3 calls 10.
- e3 (preflop): Player 4 calls 10.
- e4 (preflop): Player 5 calls 10.
- e5 (preflop): Player 6 calls 10.

Discussion:

- Which public actions support a range hypothesis, and which reads remain unsupported?
- Which legal size or passive action would you compare, and what response assumptions does that require?
- What next-street observations would change the plan, without assuming a future card?

## review-06: flop

Hero: 3c 6h, SB. Board: Td 4d 7c. Pot: 60 chips. To call: 0 chips. Big blind: 10 chips.

Legal choices: check, raise:10, raise:30, raise:60, raise:490.

Public action sequence:

- e2 (preflop): Player 3 calls 10.
- e3 (preflop): Player 4 calls 10.
- e4 (preflop): Player 5 calls 10.
- e5 (preflop): Player 6 calls 10.
- e6 (preflop): Player 1 calls 5.
- e7 (preflop): Player 2 checks.

Discussion:

- Which public actions support a range hypothesis, and which reads remain unsupported?
- Which legal size or passive action would you compare, and what response assumptions does that require?
- What next-street observations would change the plan, without assuming a future card?

## review-07: turn

Hero: 3c 6h, SB. Board: Td 4d 7c 6s. Pot: 60 chips. To call: 0 chips. Big blind: 10 chips.

Legal choices: check, raise:10, raise:30, raise:60, raise:490.

Public action sequence:

- e2 (preflop): Player 3 calls 10.
- e3 (preflop): Player 4 calls 10.
- e4 (preflop): Player 5 calls 10.
- e5 (preflop): Player 6 calls 10.
- e6 (preflop): Player 1 calls 5.
- e7 (preflop): Player 2 checks.
- e8 (flop): Player 1 checks.
- e9 (flop): Player 2 checks.
- e10 (flop): Player 3 checks.
- e11 (flop): Player 4 checks.
- e12 (flop): Player 5 checks.
- e13 (flop): Player 6 checks.

Discussion:

- Which public actions support a range hypothesis, and which reads remain unsupported?
- Which legal size or passive action would you compare, and what response assumptions does that require?
- What next-street observations would change the plan, without assuming a future card?

## review-08: river

Hero: 3c 6h, SB. Board: Td 4d 7c 6s 2s. Pot: 60 chips. To call: 0 chips. Big blind: 10 chips.

Legal choices: check, raise:10, raise:30, raise:60, raise:490.

Public action sequence:

- e2 (preflop): Player 3 calls 10.
- e3 (preflop): Player 4 calls 10.
- e4 (preflop): Player 5 calls 10.
- e5 (preflop): Player 6 calls 10.
- e6 (preflop): Player 1 calls 5.
- e7 (preflop): Player 2 checks.
- e8 (flop): Player 1 checks.
- e9 (flop): Player 2 checks.
- e10 (flop): Player 3 checks.
- e11 (flop): Player 4 checks.
- e12 (flop): Player 5 checks.
- e13 (flop): Player 6 checks.
- e14 (turn): Player 1 checks.
- e15 (turn): Player 2 checks.
- e16 (turn): Player 3 checks.
- e17 (turn): Player 4 checks.
- e18 (turn): Player 5 checks.
- e19 (turn): Player 6 checks.

Discussion:

- Which public actions support a range hypothesis, and which reads remain unsupported?
- Which legal size or passive action would you compare, and what response assumptions does that require?

## review-09: preflop

Hero: 6d 2c, SB. Board: None. Pot: 415 chips. To call: 95 chips. Big blind: 10 chips.

Legal choices: fold, call.

Public action sequence:

- e2 (preflop): Player 3 raises to 100.
- e3 (preflop): Player 4 calls 100.
- e4 (preflop): Player 5 calls 100.
- e5 (preflop): Player 6 calls 100.

Discussion:

- Which public actions support a range hypothesis, and which reads remain unsupported?
- Which legal size or passive action would you compare, and what response assumptions does that require?
- What next-street observations would change the plan, without assuming a future card?
- How should side-pot eligibility and tournament payouts limit the equity reference?
