# PokerTH assessment

Researched on 2026-10-25 following Rayner's request to assess PokerTH as an alternative to QuantPlay. Source inspected and exercised from release `v2.1.10`, commit `0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba`.

## Recommendation

Prioritize PokerTH's AI engine 4 for the first opponent-adapter trial. Its community and maintenance evidence are stronger than QuantPlay's, and an isolated build demonstrated that the current decision module can run without the desktop application. This supersedes the earlier provisional recommendation to trial QuantPlay first. QuantPlay remains a useful alternative opponent family.

Neither has been integrated into our application. This is a technical recommendation, not a claim of proven human realism or an expansion of the active Stage 1 assignment.

## Community and maintenance

The public GitHub API reported 690 stars, 263 forks and 33 listed contributors. The latest push was 2026-10-19, and the latest release was `v2.1.10`, published on 2026-10-05 UTC with a changelog dated 2026-10-06. Recent Windows and Android build workflows succeeded. These are stronger maintenance signals than a small single-author prototype, but do not measure poker quality.

Sources: [repository](https://github.com/pokerth/pokerth), [contributors](https://api.github.com/repos/pokerth/pokerth/contributors?per_page=100), [release](https://github.com/pokerth/pokerth/releases/tag/v2.1.10), [build history](https://github.com/pokerth/pokerth/actions).

SourceForge reports 4.8/5 across 59 user reviews. The visible reviews largely concern enjoyment, usability and the overall game, and many predate the current AI. On Reddit, users describe returning to a long-running game; a maintainer said in March 2026 that AI improvements had received less attention than the community. That comment predates engine 4, introduced in September's `v2.1.9` release, so it should not be treated as a review of the new engine. Targeted searches did not establish independent playing-strength or human-realism validation of engine 4.

Sources: [user reviews](https://sourceforge.net/projects/pokerth/reviews/), [March discussion](https://www.reddit.com/r/poker/comments/1rrxliz/we_just_released_pokerth_206_a_free_opensource/), [engine 4 release](https://github.com/pokerth/pokerth/releases/tag/v2.1.9).

## Reuse findings

`AiEngine4::decide(AiSituation, AiPersonality)` accepts a snapshot and returns an action intention. Inputs include the acting player's cards, public board and betting state, position-related counts and aggregate observed opponent tendencies. Personality controls looseness, aggression and bluffing. Unlike a full desktop-game integration, this small interface can be wrapped directly.

The implementation includes position-based preflop charts, short-stack push/fold rules, pot-odds decisions, randomized bluffs and Monte Carlo equity against all remaining opponents. Its equity routine samples multiple opponent hands and shares ties proportionally. This directly addresses the multiway-equity limitation identified in the inspected QuantPlay policy.

It remains heuristic. The decision module uses coarse opponent ranges and aggregate statistics, and its snapshot has no tournament payout input. It does not provide a verified GTO or ICM strategy. An intention may require stack clamping or adjustment for raise reopening; upstream explicitly delegates legality to its game engine. Our adapter must perform equivalent validation against PokerKit and the observed state version.

Sources: [decision interface](https://github.com/pokerth/pokerth/blob/0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba/src/engine/local_engine/aiengine4.h), [decision implementation](https://github.com/pokerth/pokerth/blob/0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba/src/engine/local_engine/aiengine4.cpp), [equity implementation](https://github.com/pokerth/pokerth/blob/0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba/src/engine/local_engine/equitycalculator.cpp).

## Local feasibility check

Built four unmodified upstream implementation files with `clang++ -std=c++20 -O2`: the AI engine, equity calculator, hole-card range parser and hand evaluator. A research-only `Tools::GetRand` bridge supplied deterministic standard-library randomness instead of the application's OpenSSL randomness helper. This avoided desktop, GUI, server and network dependencies. It is not a build or validation of the complete PokerTH application.

Observed results:

- Seven equity checks passed: proportional splits on a royal-flush board against one, two and five opponents; certain wins with an exclusive royal flush against one and five opponents; duplicate-card rejection; and lower pocket-aces equity against five random opponents than against one.
- All 200 synthetic decision cases passed basic output checks across preflop, flop, turn and river, one to five opponents, short/deep stacks and varied personality and observation settings. These checked action categories and check/call consistency, not complete game legality or strategic correctness.
- The aces sanity check returned approximately 85.6% against one random opponent and 50.3% against five. These are sampled test results, not solver references.

The harness and raw output are in `/private/tmp/wtr-pokerth-research-a291gfvr/smoke.cpp` and `/private/tmp/wtr-pokerth-research-a291gfvr/smoke-results.json`. The durable findings are recorded here because temporary files may be removed. No application dependency, opponent policy or worker behavior changed.

## Integration route

Retain PokerKit as the authority for cards, pots and legality. Wrap the pinned C++ decision module with a small native or subprocess interface. Translate card encoding, chip units, position and public statistics; normalize the returned intention to an available legal action. Keep policy randomness separate from deck randomness, and simulator personalities outside hero observations and model traces. Review complete hands after the adapter works, including shrinking tables and short stacks.

The source declares AGPL version 3 or later. Preserve its copyright notices and [license](https://github.com/pokerth/pokerth/blob/0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba/COPYING) when incorporating code and carry the applicable source-sharing terms into the public project. The LLM hero and genuine solver/reference integration remain separate work.
