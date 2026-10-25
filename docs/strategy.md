# Strategy candidate analysis

The first milestone adds `wtr.strategy.analyze(observation, metrics)` as a pure,
deterministic function. It proposes conditional candidates and does not choose an
action, mutate a tournament, access storage or the network, or change the existing
agent. Its only dependency beyond the standard library is the already installed
PokerKit hand evaluator. No new dependency or shared contract change is required.

## Input and output

Pass the result of `Tournament.observation()` and the `metrics` dictionary from
`wtr.agent.assess()`. A spectator snapshot is not a valid input. Core observation
fields, including legal actions, player stacks, own cards, board and version, are
required. Missing evidence and metrics are supported. Malformed or duplicate
cards suppress raise classification. This function is not a substitute for the
engine's schema, legal-action or version validation.

The output follows strategy contract v1 in `docs/parallel-work.md`:

- `schema_version` is 1 and `state_version` copies `observation.version`.
- Each candidate uses an existing legal action key and one permitted intent.
- Each includes a concise rationale, supplied evidence IDs, explicit assumptions,
  limitations, estimates and a conditional continuation.
- `uncertainty` contains limitations shared by the current analysis.

Candidates follow legal-menu order. Order is not a ranking, and candidate counts
are not policy probabilities. Supported raises produce one hypothesis per legal
size. Legal checks, calls and folds remain alternatives. Unsupported raise
classifications are omitted with a limitation. An empty legal menu returns no
candidates. The caller must never treat the first candidate as a selected action.

Each entry in `estimates` has `value`, `unit`, `basis` and `assumptions`. Pairwise
effective commitment is an array of `{seat, chips}` values with unit `chips`.
These nested fields are local module output within the contract's open estimates
object. They do not add or rename shared trace fields.

## Hand hypotheses

PokerKit evaluates the current best made hand. Private-card features support a
limited, deliberately unsolved classification:

- Preflop value hypotheses are restricted to QQ or better and AK. Other preflop
  raises are unclassified. This cutoff is a reproducible feature rule, not an
  opening chart or a claim about profitable tournament ranges.
- Postflop value hypotheses use top pair, an overpair, or two pair or better when
  private cards improve the public hand. They assume worse hands continue at the
  proposed size. The module does not estimate that frequency.
- Semi-bluff hypotheses require a direct flush or straight completion using a
  private card or rank on the flop or turn, without the preceding value feature.
  Backdoor draws, board-only draws, and missed river draws do not qualify. Draw
  completions are not counted as clean winning outs. A wheel uses the ace as low.
- Other postflop raises are bluff hypotheses. A weak made hand can still have
  showdown value. The optional zero-equity comparison does not assert that the
  actual hand has zero equity or that turning it into a bluff is best.

These categories are alternatives for review, not exclusive poker truths. For
example, a hand with both top pair and a flush draw is labeled as a conditional
value hypothesis by this first version. Board texture, blockers, range advantage,
thin value, and mixed strategies are not solved.

The analysis inspects position, current-hand history, active opponents, pot,
stacks, street bets, board, private cards, and the supplied equity metrics.
Position remains a seat label. The module does not reconstruct players left to
act or claim the button always closes the action. Current-street opponent raises
are cited as events, without inferring strength or an opponent tendency. At most
10 IDs appear in a candidate. Counts deduplicate public event IDs across history
and recent evidence. Zero or one observed action is explicitly called sparse;
even larger bounded counts are not calibrated reads or matched opportunities.
Archetypes, arbitrary event text, raw metric prose, credentials, and unknown
fields are ignored rather than copied. Integration must still pass only the
private observation, including when tracing inputs.

## Conditional calculations

For an eligible heads-up bluff comparison, let `P` be the current pot and `R` the
additional commitment, `raise_to - hero_current_street_bet`. Assuming a fold wins
`P` and every continuation loses `R`, the chip payoff is
`f * P - (1 - f) * R`. Setting it to zero gives the required fold rate
`R / (P + R)`. This risk/reward interpretation and the distinction between a bet
and a raise follow [GTO Wizard's MDF and Alpha](https://blog.gtowizard.com/mdf-alpha/).

For example, a pot of 100, hero street bet of 20, and raise-to of 50 imply an
additional commitment of 30 and a conditional threshold of `30 / 130`. Using
the raise-to amount, or subtracting the call again, would answer a different
question. The threshold compares with surrendering the pot. It does not compare
with the value of checking or calling, predict folds, or prescribe bluff frequency.

This comparison assumes the whole pot is eligible, no side pots, no unreturned
excess bets, no future investment, and zero showdown return on continuation.
Thresholds are withheld for multiway pots, any active player already all-in,
raises beyond the sole opponent's total remaining street capacity, or nonpositive
pot/risk. The observation does not prove full-pot eligibility even in the
remaining cases, so eligibility remains an explicit assumption. An all-in bet
that the sole opponent can fully match may retain this conditional comparison;
it does not become an ICM all-in evaluator.

For a heads-up call without a visible active all-in player, the optional checkdown
reference is `call / (pot + call)`. It assumes full-pot eligibility and no further
wagers. Raw equity does not establish the value of a call, and a bluff threshold
does not account for future streets. These limitations follow
[GTO Wizard's Mathematical Misconceptions in Poker](https://blog.gtowizard.com/mathematical-misconceptions-in-poker/).
Both sources were checked on 2026-10-25. No solver outputs or datasets were used.

Pairwise additional matched exposure is
`min(hero_stack, max(0, opponent_stack + opponent_bet - hero_bet))`. It describes
remaining commitment from this decision, not the whole hand's effective starting
stack. At most 10 big blinds triggers a short-stack limitation. This diagnostic
cutoff is heuristic. Multiway responses are never obtained by multiplying
invented independent fold probabilities.

Finite baseline equity and standard error within zero to one are retained only
as labeled references. They assume uniform random opponent hands, not a range
that calls or raises. Sampling error excludes range-model error. These numbers
never decide the value/bluff classification. Missing or invalid metrics do not
produce guessed estimates. Hand-start ICM remains descriptive and is never used
as an action value or tournament risk premium.

## Integration example

Run this from `apps/api` with its installed environment:

```python
from wtr.agent import assess
from wtr.game import Tournament
from wtr.models import TournamentConfig
from wtr.strategy import analyze

game = Tournament("strategy-example", TournamentConfig(seed=42).model_dump())
observation = game.observation()
metrics = assess({"observation": observation})["metrics"]
analysis = analyze(observation, metrics)
assert analysis["state_version"] == observation["version"]
assert all(c["action"] in {a["key"] for a in observation["legal"]}
           for c in analysis["candidates"])
```

This milestone intentionally leaves graph wiring to integration. Add an optional
`strategy_analysis` field to graph state and an analysis node after `assess_hand`.
Join it with evidence retrieval before the existing action-selection node. Keep
the existing heuristic as the unchanged comparison policy. Do not require the
chosen action to appear in this partial candidate list; validate against the
original full legal menu and apply with the original observed state version.
Preserve the model deadline, call cap, and independent table worker processes.

Later deterministic hand, response-scenario and critique nodes could share the
same immutable observation and join into candidate analysis. Each would need
explicit assumptions and measured execution spans. No additional speculative
LLM calls are needed now. The backend can record one actual `analyze` tool span,
with bounded permitted inputs and this output. It must not emit completed spans
for hypothetical future nodes or treat these rationales as private reasoning.
The existing trace schema's object inputs and outputs already accommodate this.

## Verification and remaining work

`apps/api/tests/test_strategy.py` covers legal contract output, incremental
raise-to arithmetic, intent counterexamples, sparse and duplicate evidence,
multiway/all-in/short-stack limitations, invalid metrics, lack of inappropriate
certainty, immutable independent results, concurrent determinism, and three
complete seeded tournaments using real observations and the existing assessor.
The first hand of each integration tournament checks/calls through every street;
later random legal actions exercise elimination and settlement.

Run focused tests with `.venv/bin/python -m pytest tests/test_strategy.py -q` and
the API regression suite with `.venv/bin/python -m pytest -q`, from `apps/api`.
Disable LangSmith tracing when running local tests. Provider tests in the existing
suite use mocked transports; this module makes no provider calls. Hosted
OpenRouter, LangSmith, PostgreSQL and Supabase are not verified by this milestone.
Candidate quality, calibration, graph integration and combined-branch behavior
still require evaluation. Passing tournament tests establishes compatibility and
chip accounting, not playing strength.

On 2026-10-25 the complete API suite passed: 59 tests, including 40 strategy
tests, with `LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false
.venv/bin/python -m pytest -q`. Dependencies were installed using
`uv sync --extra test` in this worktree. No live provider or hosted-service calls
were made. No server ports, UI build, or shared contract changes were needed.
