# QuantPlay assessment

Researched on 2026-10-25 for Rayner's noncommercial GitHub and LinkedIn demo. Source inspected and smoke-tested at `d1b4ca20052ed7443b00ded263925e72e1a8e099` on the upstream `poker-core` branch.

## Recommendation

Update after the [PokerTH assessment](pokerth.md): PokerTH is now the recommended first adapter trial based on stronger community evidence and a successful isolated build of its newer decision module. QuantPlay remains an alternative opponent family. The original assessment below is retained as evidence.

QuantPlay is a promising source of experimental opponent policies. The research did not establish a community reputation or independent validation of human-like six-player behavior. Basic local execution succeeded, which supports a small adapter trial. Adoption into the application has not happened, and this recommendation does not change the active Stage 1 assignment.

## External evidence

| Check | Finding | Interpretation |
| --- | --- | --- |
| GitHub activity | Public API reported 5 stars, 1 fork, one commit-author identity with 408 contributions, no issues or pull requests, no releases, and a latest push on 2026-09-24. | Small, single-author project with limited public adoption evidence. A quiet issue tracker does not prove reliability. |
| Hacker News | The launch post had 3 points. Its only surviving comment was the author's link to the trainer; another comment was deleted. | No independent endorsement in that discussion. |
| Upstream CI | The latest two test runs succeeded. An earlier failure was followed by a dependency-fix commit. The workflow runs trainer, table, ICM and tournament checks plus the browser build. | Useful evidence of basic maintenance and execution checks, with limited CI history. |
| External benchmark | GTO Wizard's retrieved leaderboard includes Quantplay and Quantplay v8 entries with negative win rates against its agent. The published format is heads-up, 200 big blinds, with stacks reset each hand. | External performance evidence exists, but it does not validate the specific six-player opponent module, its current commit or human realism. |

Sources: [repository metadata](https://api.github.com/repos/aeneassoft/QuantPlay), [author history](https://api.github.com/repos/aeneassoft/QuantPlay/contributors?anon=1), [Hacker News discussion](https://news.ycombinator.com/item?id=49829613), [latest successful CI run](https://github.com/aeneassoft/QuantPlay/actions/runs/36003429194), [CI workflow](https://github.com/aeneassoft/QuantPlay/blob/d1b4ca20052ed7443b00ded263925e72e1a8e099/.github/workflows/tests.yml), [GTO Wizard benchmark](https://benchmark.gtowizard.com/).

Targeted searches for QuantPlay, its repository and its domain across Reddit, Hacker News and poker discussions did not locate substantive independent user reviews. Search results included copies of the author's description and repository directories; those are not testimonials. This is a search finding, not proof that no reviews exist anywhere.

## Suitability for our opponents

The source exposes `SixMaxBot(seat, knobs, seed)`, with `new_hand`, `observe` and `decide` methods. Profiles vary opening width, aggression, calling and bluffing. Each bot keeps its own opponent statistics from public actions and can adjust its behavior. This is a practical integration surface for our existing game.

The implementation remains heuristic. For example, multiway spots narrow an assumed opponent range, but the equity routine still evaluates against one opponent at a time. It is not a full multiway solver. The returned rationale includes the bot's hand and hidden profile, so an adapter must keep it out of hero observations, retrieval and model traces. Only public actions should reach the hero agent.

Sources: [six-player policy](https://github.com/aeneassoft/QuantPlay/blob/d1b4ca20052ed7443b00ded263925e72e1a8e099/pokerbot/arena/sixmax.py), [equity calculation](https://github.com/aeneassoft/QuantPlay/blob/d1b4ca20052ed7443b00ded263925e72e1a8e099/pokerbot/engine/equity.py).

The project's [license](https://github.com/aeneassoft/QuantPlay/blob/d1b4ca20052ed7443b00ded263925e72e1a8e099/LICENSE.md) is PolyForm Noncommercial. Its published usage description includes hobby and research projects. Retain the upstream license and [NOTICE](https://github.com/aeneassoft/QuantPlay/blob/d1b4ca20052ed7443b00ded263925e72e1a8e099/NOTICE) with any copied code.

## Checks actually run locally

The pinned source was downloaded into a temporary directory. A separate Python 3.12.14 environment installed only `treys==0.1.8`. Tests ran with an explicit minimal environment, without provider credentials.

| Command | Observed result |
| --- | --- |
| `python -m tests.test_table` | Passed 500 six-player hands using the upstream randomized legal-action policy. Verified chip conservation and non-negative stacks; reported 374 hands with side pots. This checks the upstream engine, not bot realism. |
| `python -m tests.test_sixmax_seed` | All four checks passed: reproducibility with matching seeds, different sequences with different seeds, randomized default initialization and seedable stateless RNG. The sequence checks use the actual six-player bots. |

Sources: [table check](https://github.com/aeneassoft/QuantPlay/blob/d1b4ca20052ed7443b00ded263925e72e1a8e099/tests/test_table.py), [bot checks](https://github.com/aeneassoft/QuantPlay/blob/d1b4ca20052ed7443b00ded263925e72e1a8e099/tests/test_sixmax_seed.py).

These runs did not exercise a PokerKit adapter, validate tournament strategy or compare behavior with human hand histories. No application dependency or runtime behavior was changed. Temporary evidence is in `/private/tmp/wtr-quantplay-research-96rerykb/smoke-results.json`; the results above are retained here because temporary files are not durable project artifacts.

## Proposed integration trial

Keep PokerKit authoritative for cards, pots and legal actions. Adapt the pinned QuantPlay policy to permitted player observations and public action events. Check raise-to units, the application's available action sizes, shrinking tables, short stacks, independent policy randomness and memory isolation. Review example hands before using it as the default opponent pool. The hero LLM and genuine solver/reference tool remain separate components.
