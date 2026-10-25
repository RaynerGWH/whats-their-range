# Project roadmap

Prepared on 2026-10-25 (Asia/Singapore) following Rayner's request for the remaining project roadmap. Stage 1 and [Stage 2A](tasks/stage-2a.md) are complete and reviewed into local main. The [Stage 2A integration review](review/stage-2a-integration.md) verifies playable PokerTH opponents within PokerKit, using the existing hero decision path. Stage 2B is next, with fuller strategy and the initial genuine solver/reference integration. Stage 2B and later expansion remain unassigned. Accepted direction and current implementation status remain in [shared project context](project-context.md).

Rayner subsequently pivoted Stage 2B toward an all-LLM table with public chat and a hero harness intended to outperform comparable AI opponents. The [harness plan](llm-agent-harness.md) proposes three slices: a four-player LLM/chat environment, the hero's tools and strategy loop including initial solver access, and controlled comparisons. The existing PokerTH environment remains the tagged baseline and comparison mode. New runtime work is not implemented or assigned by this roadmap.

## Intended outcome

Rayner intends to share this noncommercial research demo publicly on GitHub and LinkedIn. The release should make the architecture, setup, observed behavior and limitations easy to inspect and reproduce. Commercial product requirements are outside scope; a hosted demo remains an optional presentation route.

An LLM agent can examine permitted public player history, form competing hypotheses, choose useful calculations and strategy references, and make a legal poker decision with an inspectable justification. It performs meaningfully better than the existing heuristic and an otherwise comparable LLM without the additional tools on agreed evaluations. Results include uncertainty, failures, latency and cost. Human-like opponent behavior and professional-level agent strength require evidence beyond winning against our own scripts.

## Milestones and completion evidence

| Milestone | Work | Evidence required before advancing |
| --- | --- | --- |
| 1. Establish a trustworthy development baseline | Review and integrate the four committed workstreams deliberately. Fix the evaluation seed/scenario leak, audit tool and trace boundaries, preserve the heuristic comparison and independent workers. Agree a small set of hands with Rayner. | Combined checks pass; agent-visible identifiers are opaque; hidden metadata and spectator state cannot affect model inputs; local decision traces can be inspected and replayed. |
| 2A. Deliver a playable opponent environment | Keep PokerKit authoritative and integrate actual PokerTH opponent decisions. Preserve the existing hero `Agent.decide` path, public history and trace UI, with a clear extension point for the later strategy graph. | Complete tournaments with real native opponents and the existing hero, legal/state-version checks, chip conservation, privacy, independent tables and working UI/replay. Provider-path tests may use clearly labeled mocks; opponent execution must be real. |
| 2B. Implement the LLM table and hero harness | Add LLM players with isolated private contexts and shared public chat. Backend and strategy jointly define tools, claim/evidence memory and final output. Implement the model-directed loop and a genuine solver/reference source for supported spots. Preserve the Stage 2A comparison mode. | Complete LLM games with attributable chat, per-seat records, legal actions and information boundaries. On reviewed hands, real tools and a supported solver query inform decisions. Controlled baseline/harness and chat comparisons report outcomes, uncertainty, latency and cost. Mocks alone do not complete this milestone. |
| 3. Expand and qualify solver coverage | Extend the initial Stage 2 adapter or add providers for more stack depths, preflop/postflop situations, multiway and tournament needs. Improve applicability checks, caching, asynchronous execution and reference-case validation. | Results have verified units, action-size and range conversions, provenance and scope. Unsupported multiway/ICM situations remain explicit. Measured latency, cost and permitted service use fit the intended deployment. |
| 4. Improve and validate opponent realism | Build on the opponents already used in Stage 2. Keep PokerKit for mechanics; evaluate existing bot engines and policies before expanding custom implementations. Adapt suitable policies and add contextual variation where needed, using ranges, position, stacks, sizes and history. | Rayner reviews example lines. Conditional behavior statistics match intended policies across situations. Policies see only permitted observations. Identities and hidden profile assignments vary across independent experiments while remaining stable within a tournament. |
| 5. Validate judgment and generalization | Compare the heuristic, the same LLM without tools, and the full agent. Remove memory or solver tools in separate experiments to measure their contribution. Use held-out policies/parameters as well as seeds, balanced seat assignments and isolated evaluation memory. | Reviewed hand decisions, prediction calibration where predictions are made, tournament prize results with uncertainty, legality, tool errors, latency and cost support a useful improvement. Results do not depend on leaked metadata or one predictable opponent family. |
| 6. Prepare the public research demo | Complete UI inspection of evidence, tool results, decisions and replay. Prepare reproducible setup instructions, example traces, evaluation results, dependency notices and a concise demonstration for GitHub and LinkedIn. Verify persistence, bounded costs and worker recovery; deploy a hosted preview when requested. | A fresh setup and sustained two-table run work as documented. Example hands and results support the public claims, with strategy coverage and limitations stated clearly. Any hosted preview also verifies provider connections and appropriate access controls. |

Stages 2A and 2B together deliver the agent, solver access, opponent simulation and trace inspection. Rayner requested the playable environment first, then the fuller strategy. Completing 2A does not imply the tool loop or solver is implemented. Milestones 3 and 4 expand coverage and realism. Hand-based regression checks start in Stage 1; Stage 5 is the broader performance evaluation. A genuine supported solver integration is required for 2B, while unavailable references remain explicit.

## First useful deliverable

Proposed scope: a reviewed set of roughly 10 to 20 decisions, including value, bluff/semi-bluff, opponent aggression, multiway uncertainty and short-stack tournament pressure. Start with one hand through the entire pipeline before broadening the set.

For a supported solver spot, demonstrate a real reference query, opponent evidence retrieval, competing scenario analysis and a final LLM decision, all visible in the trace. Also demonstrate a spot outside solver coverage where the agent correctly recognizes the limitation. Tests should check evidence use and boundaries without requiring a particular wording or identical stochastic model output. Rayner reviews strategic tradeoffs; solver action frequencies are not automatically universal answer keys.

The same components must run inside a local simulated game: opponent actions produce public history, the hero observes and investigates that history, its tools return evidence and applicable references, the LLM submits a decision, and the engine applies it before play continues. The UI exposes the evidence, competing assessments, tool results, concise justification and final action. Keep opponent profiles and evaluator-only information outside that loop. Provider selection, credentials and the bounded live-call budget need to be resolved as part of the Stage 2 execution brief; they are not authorized by the roadmap alone.

## Solver integration findings

Sources checked on 2026-10-25. No account, API key, paid call, solver installation or output validation was performed. The recommendations below are provisional.

| Option | Verified interface | Fit and limitations |
| --- | --- | --- |
| Pokerai.bet | Hosted HTTP API, official clients and an MCP server. Documented precomputed lookups and custom solves. | Candidate for an API proof of concept. Its FAQ excludes ICM strategy; the custom solve endpoint takes two player ranges. Six-max preflop coverage does not establish multiway postflop coverage. Accuracy, coverage, latency and service reliability need independent checks. |
| PioSOLVER | Documented UPI text protocol for scripting and integration with its engine. | Candidate when solver control and reference generation matter. Desktop deployment uses Windows; server/web use has a separate business offering. It requires operating an engine or arranging service access, rather than assuming a hosted consumer HTTP API. |
| HoldemResources Calculator (HRC) | Tournament/cash analysis and documented scripts for building calculation trees inside HRC. | Candidate for preparing tournament reference cases with Rayner. The documented scripting feature still uses UI configuration for stacks and equity model. We have not verified a supported headless HTTP service for our agent. |
| GTO Wizard | Public benchmark API and separate partner APIs for GTO Score/FairPlay. | Benchmark access explicitly excludes solver queries. It can provide an external heads-up evaluation environment if access is obtained, but does not supply our general tournament solver tool. Other commercial solver access remains unverified. |

Pokerai's [API documentation](https://pokerai.bet/docs), [coverage FAQ](https://pokerai.bet/faq) and [official MCP implementation](https://github.com/pokerai-bet/mcp) establish the advertised integration path, not independently measured solving quality. Its separate ICM-equity calculator is not an ICM strategy solver.

Pio documents its [UPI integration protocol](https://piosolver.com/docs/upi/), [deployment requirements](https://piosolver.com/docs/technical_details/) and [business service offering](https://piosolver.com/docs/faq/business/). HRC documents [its analysis scope](https://www.holdemresources.net/) and [scripted tree construction](https://www.holdemresources.net/docs/scripting/). GTO Wizard describes [benchmark scope and the exclusion of solver access](https://benchmark.gtowizard.com/) and [partner APIs](https://developers.gtowizard.com/).

Provisional recommendation: evaluate Pokerai.bet for the first supported API-backed reference tool because it publishes a direct API/MCP path. Keep the adapter replaceable and the initial coverage explicitly limited. Use independently reviewed solver cases, potentially prepared with Pio/HRC, to check results. Do not select it as the complete tournament solver on documentation alone. Full tournament and multiway coverage remains a separate requirement to resolve.

## Why an API does not complete the solver work

The transport can be straightforward. Our backend still has to translate the actual hand into the provider's modeled situation: player count, pot and effective stacks, positions, action history, legal sizing, range hypotheses and tournament payout assumptions. Opponent ranges are hypotheses derived from public evidence, never the simulator's actual hole cards.

The adapter must distinguish exact support, an explicitly identified approximation, and an unsupported request. Return action frequencies and EVs only with their units, assumptions, provider/version and spot match. A chip-EV result is not automatically a tournament prize-EV result. Handle queued solves, time limits, errors and caching without allowing the LLM to invent missing outputs. MCP is an optional tool interface; direct backend HTTP calls can expose the same qualified capability to LangGraph.

## Opponent realism and independent evaluation

### Reuse candidates

Researched on 2026-10-25 after Rayner raised the availability of opponent libraries. The [QuantPlay assessment](research/quantplay.md) ran two upstream smoke-test modules successfully. A subsequent [PokerTH assessment](research/pokerth.md) found stronger community evidence and successfully compiled and exercised its AI engine 4 independently of the desktop app. Rayner then confirmed combining PokerKit's environment with PokerTH's opponent logic, now implemented and reviewed in Stage 2A. The alternatives remain reference candidates. Realistic human behavior remains unverified.

| Candidate | What is available | Fit to investigate |
| --- | --- | --- |
| PokerTH | Established C++ poker game with AI engine 4 accepting a snapshot and personality. Stage 2A vendors the pinned core, builds a native wrapper and translates its intentions into PokerKit legal actions. Source declares AGPLv3 or later. | Integrated opponent family, verified in complete games. Multiway equity and varied behavior are implemented; human realism and playing strength are unverified. |
| QuantPlay | Python six-max trainer/research code with profiled and adaptive opponents and tournament modes. Its `SixMaxBot` interface was inspected and upstream engine/RNG smoke checks passed locally. Uses PolyForm Noncommercial. | Alternative opponent family with a Python interface. Independent user feedback is sparse. PokerKit compatibility and human realism remain unverified, and large research artifacts are not all included. |
| RLCard / PokerRL | Training and evaluation frameworks for card-game agents. RLCard's inspected model registry includes Leduc and limit-holdem agents, not a ready six-player NLH tournament policy. | Useful if training becomes a deliberate workstream. Installing a framework does not provide the specific trained opponent required by our game. |
| DecisionHoldem | Heads-up NLH research agent with blueprint/search interfaces and separately downloaded strategy data. | Possible separate heads-up benchmark; it is not a direct six-player tournament opponent. Verify artifact availability and resource requirements before committing to an experiment. |

Sources: [PokerTH](https://github.com/pokerth/pokerth), [QuantPlay README](https://github.com/aeneassoft/QuantPlay/blob/poker-core/README.md), [QuantPlay license](https://github.com/aeneassoft/QuantPlay/blob/poker-core/LICENSE.md), [RLCard model registry](https://github.com/datamllab/rlcard/blob/master/rlcard/models/__init__.py), [PokerRL](https://github.com/EricSteinberger/PokerRL), [DecisionHoldem](https://github.com/AI-Decision/DecisionHoldem).

Repository names and old search snippets are insufficient evidence of coverage. For example, the current [CFR-NLHE-6max README](https://github.com/dberweger2017/CFR-NLHE-6max) describes a heads-up research bot, three-player release work and six-player support as a later goal. Do not assume older six-player claims establish a usable current artifact.

The first adapter experiment is delivered as Stage 2A. PokerKit remains the game authority and PokerTH receives only the acting player's permitted observation. Complete games and regression checks cover changing player counts, short stacks, side pots, legal mapping, reproducibility and private-information boundaries. Borrowed source, profiles and experiment identifiers remain outside the hero LLM's context, and upstream notices are retained. Review the recorded public hands for plausible play before making human-realism claims or expanding opponent families.

### Validation

First define behaviors that persist coherently across streets: which situations induce loose calls, missed value, excess aggression, underbluffing or overfolding. Parameters should change conditional action distributions, not simply add random mistakes to every decision. Exact policy mechanisms remain private to the simulator.

Rayner's hand reviews can establish plausible behavior. Stronger claims that bots resemble people require comparison with appropriately available human hand histories and conditional statistics. Until then, describe them as designed opponent models. Keep a separate strong benchmark and held-out policies; opponents used to tune the agent must not be the entire evaluation set. Any external heads-up benchmark measures only that format and cannot certify six-player tournament performance.

## Proposed workstream alignment

- Backend and strategy jointly own the first complete decision specification. Backend implements execution, evidence access and enforcement; strategy defines analytical tools and decision behavior.
- Evaluation owns blinded comparisons and reports simulator changes needed for better opponents and balanced experiments. Engine changes are coordinated with backend ownership.
- Frontend exposes the actual analysis and tool outputs as they become available. Further UI work follows the shared decision contract.
- Integration maintains accepted decisions and reviews, combines completed work deliberately and keeps reported status tied to evidence.

No fixed delivery dates or paid-service budget are asserted yet. Solver coverage and service access, model latency and cost, and the first reviewed hand set determine the next concrete implementation brief.
