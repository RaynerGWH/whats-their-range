# Shared project context

Revision: 14. Updated: 2026-10-25 18:52 Asia/Singapore.

This is the current project brief and decision log for every coding chat and worktree. Read it before starting or resuming work. The integration chat maintains it from Rayner's decisions and verified branch evidence. The local canonical checkout is identified in [shared context access](shared-context.md).

## Goal

This is a noncommercial research and demonstration project, intended for a public GitHub repository and a LinkedIn presentation. Prioritize a reproducible setup, inspectable decisions and honest evaluation results. Commercial product requirements are outside the agreed scope.

Build a spectator lab in which an LLM poker agent plays a six-player single-table NLH tournament against simulated opponents, with up to two independent tables. The agent should interpret the whole hand, maintain cautious opponent reads, examine competing hypotheses, consider future responses and streets, and make informed poker decisions using tools and applicable strategy references.

Rayner's Garrett Edelstein reference expresses the desired depth of player-like judgment. It is not a claimed reproduction of his strategy or evidence of comparable skill. This project's actual decision context includes tournament stacks and payouts.

## Agreed direction

- The LLM makes the final poker decision. It can request evidence, calculations, relevant strategy references and scenario analyses, then revise its assessment before choosing a legal action.
- Strategy is part of the backend. The two coding workstreams implement one decision system: poker analysis and tool semantics alongside the runtime, evidence pipeline and execution controls.
- There is no fixed numerical blend of GTO and opponent context. The LLM judges whether evidence supports an adjustment and identifies the assumptions and uncertainty behind it.
- Deterministic calculations support the agent. They do not require deterministic final play or make heuristic classifications into a GTO strategy.
- The target is a bounded, model-directed tool loop in LangGraph, with parallel analyses when useful. The current fixed preparation graph is an intermediate implementation.
- The immediate focus is backend and strategy. Rayner wants to review concrete hands and strategic tradeoffs as this develops.
- Stage 2 must be an end-to-end playable agent, including actual simulated opponents, public player history, a genuine solver/reference tool for supported spots, and visible analysis and decisions. Later stages expand solver coverage and opponent realism.
- Combine the existing PokerKit game environment with PokerTH's opponent decision logic through an adapter. PokerKit handles cards, betting, pots and legality; PokerTH chooses opponent actions; our LLM chooses hero actions. The solver is a separate tool. Stage 2A implements the opponent environment; the fuller LLM strategy remains Stage 2B.
- Deliver this in two steps: Stage 2A makes complete games playable against PokerTH through the existing hero decision interface; Stage 2B implements the fuller strategy/tool loop and initial genuine solver access. Rayner explicitly requested the environment first, then strategy development.
- Make meaningful local commits during development. The integration chat may merge completed, reviewed milestones into local `main` after their checks pass. Remote pushes and deployment remain separate actions.
- Protect evaluation from both hidden-state leakage and shortcuts based on knowing the simulator's opponent policies. Opponent adjustments should be supported by permitted observations; successful play against recognizable scripts does not establish general poker skill.
- Judge simulation behavior across recurring situations and a meaningful sample. An isolated unusual or losing action does not establish that PokerTH is inaccurate. Imperfect opponents are useful for this side project; keep legality, adapter fidelity and strategic quality separate.

Detailed design targets and proposed tool families are in [agent direction](agent-direction.md). That document distinguishes implemented behavior from future work.

## Current implementation

The combined Stage 1 baseline was reviewed into local `main` via `a486a49`. Stage 2A delivery `a82a152` was then reviewed, independently tested and merged into local `main` on 2026-10-25 via `e99817b`. Documentation-only follow-ups may advance the branch further. See the [Stage 2A integration review](review/stage-2a-integration.md) and the earlier [Stage 1 review](review/stage-1-integration.md). No remote push was made. This is an inspection snapshot, not an automatic monitor, and passing checks do not establish poker strength.

| Workstream | Branch and audited commit | Implemented | Integration status |
| --- | --- | --- | --- |
| Baseline and integration | Stage 1 `01f3a81`, integration `a486a49` | Combined simulator, traces, frontend, analysis module and evaluation | Reviewed and present in local main |
| PokerTH environment | `feat/pokerth-opponents`, `a82a152`, integration `e99817b` | Real native opponents, legal action mapping, independent RNG streams, private shuffled personalities, public statistics and complete games | Stage 2A reviewed and present in local main; human realism remains unverified |
| Strategy | Input `feat/strategy`, `6f44297` | Pure candidate analysis, hand labels and conditional calculations | Integrated as an available module; not connected to live action selection; no solver |
| Backend | Input `feat/observability`, `9c63568`, plus Stage 1 fixes | Recorded spans, trace persistence/APIs, bounded LangSmith export, worker lifecycle and privacy protections | Integrated and checked with frontend; hosted providers remain unverified |
| Frontend | Input `feat/trace-explorer`, `5d34afa`, plus Stage 1 fixes | Trace tree, timeline, details, polling and explicit completed-trace refresh | Integrated with real local trace records; provider calls used mocks |
| Evaluation | Input `feat/evaluation`, `34c7e2d`, plus protocol 2 fixes | Reproducible tournaments, policy adapters, opaque IDs and separate hero policy seed | Integrated baseline evaluation; broader policy holdouts and full LLM/tool-loop evaluation remain future work |

Latest independent integration verification: the native core built from vendored sources, 128 API tests passed, one optional PostgreSQL test skipped, 16 frontend tests passed, TypeScript and production build passed. The API suite executed real native opponents and independent production workers. The backend's recorded browser evidence and 20-tournament smoke set were inspected rather than repeated in full. Provider and LangSmith tests used mocks. Hosted OpenRouter, LangSmith and Supabase operation remains unverified. Milestone test counts overlap and must not be added together.

## Evaluation integrity finding

Confirmed in the original evaluation milestone `34c7e2d`: table IDs exposed split, deck seed, repeat, policy and scenario in observations and public event IDs. Stage 1's delivery `d97b465`, included in `01f3a81`, addresses this with opaque table IDs, table-local event IDs, separate policy seeds and reconstructed public names/action text. Semantic privacy regressions cover actual mocked-provider payloads and local/exported traces. Stage 2A additionally separates deck, hero, per-seat opponent and personality RNG streams, privately shuffles profiles across neutral identities between tournaments and resets public statistics per table. Integration reran these checks and merged the fixes into local main. Broader generalization to unknown policies remains unverified.

Keep opaque policy-visible table and event identifiers and retain experiment metadata only in evaluator-owned records. Audit all prompt, tool, retrieval and trace paths for equivalent leakage. Identity/profile assignments now vary between independent runs and remain stable within each tournament. The recorded evaluation varies deck and opponent/assignment seeds, but does not hold out independent opponent policy families. Further evaluation should hold out policies and parameters, rotate the hero seat, and verify isolated agent memory as richer memory is introduced.

The player agent must not receive opponent-policy source, simulator settings, deck seeds, evaluation answer keys or unrestricted access to the repository and spectator APIs. Controller access for reproducibility is separate from agent access. Knowledge of public poker rules or a game engine does not itself reveal an opponent's strategy; opponent behavior comes from PokerTH or the explicit legacy heuristic, not a PokerKit strategy.

## Next work and open decisions

Stage 1 is complete as an engineering baseline and reviewed into local main. The original backend delivery `01f3a8120790fbdad4d8589962be6d90fcb7d8b7` remains preserved on `feat/baseline-integration`. The [integration review](review/stage-1-integration.md) records independently rerun checks and the merge. Strategic hand review remains pending.

[Stage 2A](tasks/stage-2a.md) is complete and reviewed into local main. The backend delivered `a82a152` on `feat/pokerth-opponents`: complete games with real PokerTH opponents and the existing hero decision path, public history, traces and replay. The [delivery report](stage-2a.md) records 20 completed tournament runs and ten matching repeat pairs. The [integration review](review/stage-2a-integration.md) records the independent checks and merge. Stage 2B is next: the fuller backend/strategy decision specification, model-directed tool loop and initial genuine solver access. It remains unassigned and provider access/budget remains unresolved.

The [roadmap](roadmap.md) records this sequence, completion evidence, opponent-model work and a solver shortlist researched on 2026-10-25. Splitting Stage 2 into A and B changes sequencing; Stage 2A alone does not establish the target reasoning system or solver integration. No solver has been selected or integrated.

The roadmap also records an [opponent reuse shortlist](roadmap.md#reuse-candidates), researched after Rayner raised existing bot libraries and requested reputation checks. The [QuantPlay assessment](research/quantplay.md) found sparse independent feedback and passed two upstream smoke-test modules at `d1b4ca2`. The subsequent [PokerTH assessment](research/pokerth.md) found a stronger community history and a separable AI engine 4 interface. Stage 2A now vendors release `0a7dceb`, with a reproducible native build and a tested adapter in local main. Its discrete raise mapping, public-statistic definitions and RNG differ from desktop PokerTH and are documented. Human realism, strategic strength and solver agreement remain unverified.

The subsequent [behavior review](review/pokerth-behavior.md) ran a live game and sampled 150 hands across six 100-BB games, checking 1,054 native decisions without illegal actions or chip-conservation failures. It records a plausible live hand, sizing changes, a position shortcut and descriptive action frequencies. Rayner clarified that one unusual bluff is not grounds to dismiss the simulator. These observations remain review notes and proposed refinements, not a rejection of PokerTH or a new blocker for Stage 2B. No opponent policy was changed.

Still to decide:

- The first useful tool set, its input/output contracts and evidence representation.
- How to represent and compare opponent hypotheses and tentative leaks without inventing calibrated probabilities.
- Sources and applicability checks for verified poker strategy references or solver outputs, including unavailable coverage.
- Model/provider choice, total decision time and cost limits, parallel call limits and fallback behavior for the tool loop.
- Representative hands and evaluation criteria, followed by broader tournament configurations and held-out comparisons.

Local implementation is authorized in the assigned delivery branches. Rayner has additionally authorized meaningful commits and merging solid completed work into local `main` after integration review and checks. The integration chat owns those merges; worker chats commit and deliver their own branches. Live provider spend, new cloud resources, remote pushes and deployment are not authorized by this workflow. A recorded proposal does not assign work to another chat.

## Boundaries to preserve

Use only permitted observations and public evidence. Spectator hole cards, opponent simulator profiles, future state and credentials must never enter agent inputs or model traces. Each table owns state and opponent memory independently; actions must match the observed state version. Keep the heuristic as a named reproducible comparison and clearly labeled operational fallback. Preserve local decision records independently of external telemetry. Intended deployment remains Fly.io for the backend and Vercel for the frontend, with SQLite locally and PostgreSQL/Supabase preparation.

Follow [architecture](architecture.md), [contracts](../contracts/) and the ownership and runtime isolation rules in [parallel work](parallel-work.md). The first-milestone task briefs document the original assignments; they do not describe the complete target agent. Proposed future interfaces do not silently replace current contracts.

## Decision log

All entries below were accepted through Rayner's discussion in the integration chat on 2026-10-25. New entries should include a date, source and consequences. Preserve superseded decisions with a pointer to their replacement.

| ID | Decision | Consequence |
| --- | --- | --- |
| D001 | Prioritize backend and strategy development | Frame their next milestone around one complete poker decision process |
| D002 | The LLM owns final poker judgment and chooses useful tools | Develop a model-directed tool loop; deterministic candidate rules remain supporting tools |
| D003 | Combine relevant strategy knowledge with opponent evidence and competing hypotheses | Avoid fixed GTO/context percentages; make evidence, assumptions and reference applicability observable |
| D004 | Seek player-like analysis across plausible scenarios and future actions | Evaluate the quality of judgment on example hands, as well as legal execution and tournament outcomes |
| D005 | Maintain shared project context and a record of decisions | All worktrees read this canonical brief; preserve agreed, proposed and implemented status separately |
| D006 | Treat simulator knowledge and metadata leakage as evaluation risks, as raised by Rayner | Audit the entire agent-visible information boundary and fix the confirmed evaluation identifier leak before LLM evaluation; expand held-out coverage beyond seeds |
| D007 | Rayner requested Stage 1 be directed to an existing worktree | Integration assigned the backend chat to combine and validate the baseline on `feat/baseline-integration`, including leakage fixes; later stages remain unassigned |
| D008 | Rayner clarified that Stage 2 needs simulated opponents and solver access together with the agent logic | Demonstrate a complete simulated-game decision loop with a genuine supported solver/reference query and inspectable analysis; Stages 3 and 4 expand coverage and realism |
| D009 | Rayner clarified that the project will be noncommercial, shared publicly on GitHub and presented on LinkedIn | Scope the release around a reproducible research demo, transparent results and public documentation; assess reusable bots for this purpose rather than a commercial product |
| D010 | Rayner confirmed combining PokerKit with PokerTH's opponent logic for the agent's simulated games | Preserve PokerKit as the game authority and adapt PokerTH decisions to its observations and legal actions; keep the LLM hero and a separate future solver tool distinct |
| D011 | Rayner directed the backend agent to implement the playable environment before developing the fuller strategy | Assign Stage 2A to the existing backend checkout; preserve the current hero interface and defer new strategy/solver work to Stage 2B, refining D008's sequencing |
| D012 | Rayner authorized commits during development and merges to main once work is solid and complete | Use coherent local commits; integration reviews and validates completed deliveries before merging into local main, without an additional permission round |
| D013 | Rayner clarified during live review that a single scenario should not be used to call the simulation inaccurate | Evaluate recurring behavior across a meaningful sample; separate mechanical validity, adapter fidelity and strategic judgment; do not reject PokerTH or block strategy work on an isolated unusual action |

## Keeping this current

The integration chat updates this brief when Rayner accepts or changes direction, when a reviewed milestone changes the project status, or when integration changes the interfaces. Increment the revision and timestamp with material changes, update the current summary, and append or supersede the relevant decision record. Keep implementation details in their owning documents.

Other workstreams keep evidence and proposals in their own documentation and report the shared-context revision they used in milestone handoffs. They should read the live brief again before making a scope or interface decision. Do not promote a proposal to an accepted project decision or overwrite another workstream's files to synchronize context. Coordinate changes through the integration chat and direct user instructions. New worktrees must receive the shared-context pointer before their next assignment.
