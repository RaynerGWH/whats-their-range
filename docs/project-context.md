# Shared project context

Revision: 21. Updated: 2026-10-25 (Asia/Singapore).

This is the current project brief and decision log for every coding chat and worktree. Read it before starting or resuming work. The integration chat maintains it from Rayner's decisions and verified branch evidence. The local canonical checkout is identified in [shared context access](shared-context.md).

## Goal

This is a noncommercial research and demonstration project, intended for a public GitHub repository and a LinkedIn presentation. Prioritize a reproducible setup, inspectable decisions and honest evaluation results. Commercial product requirements are outside the agreed scope.

The primary use case is to build and evaluate an agent harness that enables Rayner's LLM poker agent to outperform competing LLM agents. The harness is the main development product: memory, evidence access, poker tools, strategy references and a disciplined decision workflow. Success is measured through repeated games against defined opponents, with model settings, inference budgets, uncertainty and failures reported.

Poker supplies the competitive environment. Public table talk adds claims, deception and social influence that the harness can interpret or use. The UI and traces make play and decisions inspectable. The agent should interpret the whole hand, maintain cautious opponent reads, examine competing hypotheses and consider future responses and streets. Rayner has chosen six seats as the new baseline, with five LLM opponents on a stable saved configuration. He explicitly wants to choose his hero's actions and messages manually first, with optional LLM takeover making all six seats automated. OpenRouter model choice, instruction profile, chat access and harness remain independently configurable. Same-model comparisons isolate harness effects; explicit model variants assess broader competition. The existing six-player PokerTH environment and two-table support remain the preserved baseline.

Rayner's Garrett Edelstein reference expresses the desired depth of player-like judgment. It is not a claimed reproduction of his strategy or evidence of comparable skill. This project's actual decision context includes tournament stacks and payouts.

## Agreed direction

- Under LLM control, the LLM makes the final poker decision. It can request evidence, calculations, relevant strategy references and scenario analyses, then revise its assessment before choosing a legal action. Manual hero control lets Rayner choose that seat's action instead without changing the automated harness's intended authority.
- Strategy is part of the backend. The two coding workstreams implement one decision system: poker analysis and tool semantics alongside the runtime, evidence pipeline and execution controls.
- There is no fixed numerical blend of GTO and opponent context. The LLM judges whether evidence supports an adjustment and identifies the assumptions and uncertainty behind it.
- Deterministic calculations support the agent. They do not require deterministic final play or make heuristic classifications into a GTO strategy.
- The target is a bounded, model-directed tool loop in LangGraph, with parallel analyses when useful. The current fixed preparation graph is an intermediate implementation.
- The immediate focus is backend and strategy. Rayner wants to review concrete hands and strategic tradeoffs as this develops.
- Rayner has pivoted the next product direction to an all-LLM table with public chat, including deceptive claims and attempts to influence decisions. The hero's strategy and harness are the main development focus. PokerTH remains a comparison mode; the existing baseline is preserved.
- Rayner requested the terminal/pixel-inspired UI from his reference, with both dark and light themes, and explicitly handed this to the frontend chat. Keep the interface compact, readable and functional in both modes. Player count, message budgets and provider/tool contracts still need implementation.
- Rayner directed backend work toward a shared LLM player interface using OpenRouter, configurable per-seat models and instructions, then clarified that bluff-directed wording was too deliberate. Ordinary players use free play with the task, objective, rules and optional chat but no suggested strategy. Bluffing and deceptive talk are situational choices, without increased-frequency targets, quotas or forced behavior. The initial bluff-directed profile/preset is removed; explicit prompt experiments can be added later. Benchmark conditions remain distinct, and profiles are not proven human playstyles.
- The new baseline has six seats. Interactive play starts with Rayner choosing the hero's legal actions and optional messages, with a Manual/LLM switch for takeover. Five opponents retain a saved neutral model/instruction configuration while reacting to the actual game. Fully automated runs use six LLMs. Human or mixed-control games must not be reported as autonomous-agent benchmark results.
- Stage 2 must be an end-to-end playable agent, including actual simulated opponents, public player history, a genuine solver/reference tool for supported spots, and visible analysis and decisions. Later stages expand solver coverage and opponent realism.
- The preserved Stage 2A baseline combines PokerKit's game environment with PokerTH opponent decisions. PokerKit continues to own cards, betting, pots and legality in the new direction. The new LLM opponents choose their own actions and public messages; solver access remains a separate tool.
- Deliver this in two steps: Stage 2A makes complete games playable against PokerTH through the existing hero decision interface; Stage 2B implements the fuller strategy/tool loop and initial genuine solver access. Rayner explicitly requested the environment first, then strategy development.
- Make meaningful local commits during development. The integration chat may merge completed, reviewed milestones into local `main` after their checks pass. Remote pushes and deployment remain separate actions.
- Protect evaluation from both hidden-state leakage and shortcuts based on knowing the simulator's opponent policies. Opponent adjustments should be supported by permitted observations; successful play against recognizable scripts does not establish general poker skill.
- Judge simulation behavior across recurring situations and a meaningful sample. An isolated unusual or losing action does not establish that PokerTH is inaccurate. Imperfect opponents are useful for this side project; keep legality, adapter fidelity and strategic quality separate.

Detailed design targets and proposed tool families are in [agent direction](agent-direction.md). That document distinguishes implemented behavior from future work.

The pivot and concrete playing/evaluation plan are in [LLM agent harness](llm-agent-harness.md). The six-seat LLM environment, public chat, manual hero/takeover, terminal UI and benchmark setup are now implemented and reviewed together. The richer hero strategy harness and solver remain future work. Earlier milestone reports describe the preserved PokerTH baseline.

## Current implementation

The combined Stage 1 baseline was reviewed into local `main` via `a486a49`, followed by Stage 2A through `e99817b`. The new environment/UI delivery combines backend `e6db68c` through `0cbdb8a`, frontend `404ae2c` through `6ec8305`, and integration fixes `4c88015`. The [LLM table integration review](review/llm-table-integration.md) records independent checks and the new `baseline/llm-table` checkpoint. No remote push was made. This is an inspection snapshot, not an automatic monitor, and passing checks do not establish poker strength.

Rayner requested committing and merging all current work as the starting baseline for agent development. The remaining shared-context notes in the original, strategy, frontend and evaluation checkouts were committed and merged. The consolidated checkpoint is tagged `baseline/stage-2a` on local main. See the [baseline record](baseline-stage-2a.md). Future Stage 2B work should start from this checkpoint or a later reviewed main revision, rather than an old worktree head.

| Workstream | Branch and audited commit | Implemented | Integration status |
| --- | --- | --- | --- |
| Baseline and integration | Stage 1 `01f3a81`, integration `a486a49` | Combined simulator, traces, frontend, analysis module and evaluation | Reviewed and present in local main |
| PokerTH environment | `feat/pokerth-opponents`, `a82a152`, integration `e99817b` | Real native opponents, legal action mapping, independent RNG streams, private shuffled personalities, public statistics and complete games | Stage 2A reviewed and present in local main; human realism remains unverified |
| Strategy | Input `feat/strategy`, `6f44297` | Pure candidate analysis, hand labels and conditional calculations | Integrated as an available module; not connected to live action selection; no solver |
| Backend | `feat/llm-table`, `e6db68c`, integration `0cbdb8a` | Six-seat neutral LLM policies, private memory, public chat, manual hero/takeover, budgets, traces and replay | Reviewed with the frontend and real workers using mocked provider calls; live provider compatibility remains unverified |
| Frontend | `feat/terminal-ui`, `404ae2c`, integration `6ec8305`, fixes `4c88015` | Dark/light terminal workspace, board beside chat, manual actions/takeover, per-player inspection and replay | Combined browser check passed with actual API/worker state and explicit provider mocks |
| Evaluation | Earlier `34c7e2d` plus LLM runner `aeed481` | Shared production player/game path, versioned manifests, rotations, held-out configuration and failure/usage reporting | Mock engineering reports inspected; real-model competition and richer harness comparisons remain future work |

Latest independent integration verification: 160 API tests passed, one optional PostgreSQL test skipped, 48 frontend tests passed, and TypeScript/production build passed. The API suite executed native PokerTH regressions and spawned production workers. Browser checks covered manual action/chat, both takeover directions, replay cutoffs, per-seat traces/usage and dark/light responsive layouts. The backend's 72 completed mock games and 5,382 legal actions were inspected rather than rerun in full. Provider and LangSmith tests used mocks. Real-model play and hosted OpenRouter, LangSmith and Supabase operation remain unverified. Milestone test counts overlap and must not be added together.

## Evaluation integrity finding

Confirmed in the original evaluation milestone `34c7e2d`: table IDs exposed split, deck seed, repeat, policy and scenario in observations and public event IDs. Stage 1's delivery `d97b465`, included in `01f3a81`, addresses this with opaque table IDs, table-local event IDs, separate policy seeds and reconstructed public names/action text. Semantic privacy regressions cover actual mocked-provider payloads and local/exported traces. Stage 2A additionally separates deck, hero, per-seat opponent and personality RNG streams, privately shuffles profiles across neutral identities between tournaments and resets public statistics per table. Integration reran these checks and merged the fixes into local main. Broader generalization to unknown policies remains unverified.

Keep opaque policy-visible table and event identifiers and retain experiment metadata only in evaluator-owned records. Audit all prompt, tool, retrieval and trace paths for equivalent leakage. PokerTH identity/profile assignments vary between independent runs; the new neutral LLM opponent preset remains fixed unless deliberately changed. The LLM runner supports rotations and held-out configuration, with isolated per-run memory, but only mock engineering evidence exists. Real-model evaluation must assess held-out behavior rather than infer generalization from these tests.

The player agent must not receive opponent-policy source, simulator settings, deck seeds, evaluation answer keys or unrestricted access to the repository and spectator APIs. Controller access for reproducibility is separate from agent access. Knowledge of public poker rules or a game engine does not itself reveal an opponent's strategy; opponent decisions come from an LLM policy, PokerTH or the explicit legacy heuristic. PokerKit supplies mechanics, not opponent strategy or a solver.

## Next work and open decisions

Stage 1 is complete as an engineering baseline and reviewed into local main. The original backend delivery `01f3a8120790fbdad4d8589962be6d90fcb7d8b7` remains preserved on `feat/baseline-integration`. The [integration review](review/stage-1-integration.md) records independently rerun checks and the merge. Strategic hand review remains pending.

[Stage 2A](tasks/stage-2a.md) is complete and reviewed into local main. The backend delivered `a82a152` on `feat/pokerth-opponents`: complete games with real PokerTH opponents and the existing hero decision path, public history, traces and replay. The [delivery report](stage-2a.md) records 20 completed tournament runs and ten matching repeat pairs. The [integration review](review/stage-2a-integration.md) records the independent checks and merge. Following Rayner's pivot, Stage 2B now includes an all-LLM table and public chat, then the hero's model-directed strategy/tool loop and initial genuine solver access, with controlled comparisons throughout. The [harness plan](llm-agent-harness.md) records implementation slices.

The [backend assignment](tasks/backend-llm-table.md) and [terminal UI assignment](tasks/frontend-terminal-ui.md) are delivered and reviewed together against the [shared interface](../contracts/llm-table-v1.md). The environment and manual controls form the new engineering baseline. The fuller hero strategy/tool loop and solver remain a subsequent slice. OpenRouter is selected; exact models and live-call budgets remain open. Real-model behavior still needs a live review before strategic claims.

The [roadmap](roadmap.md) records this sequence, completion evidence, opponent-model work and a solver shortlist researched on 2026-10-25. Splitting Stage 2 into A and B changes sequencing; Stage 2A alone does not establish the target reasoning system or solver integration. No solver has been selected or integrated.

The roadmap also records an [opponent reuse shortlist](roadmap.md#reuse-candidates), researched after Rayner raised existing bot libraries and requested reputation checks. The [QuantPlay assessment](research/quantplay.md) found sparse independent feedback and passed two upstream smoke-test modules at `d1b4ca2`. The subsequent [PokerTH assessment](research/pokerth.md) found a stronger community history and a separable AI engine 4 interface. Stage 2A now vendors release `0a7dceb`, with a reproducible native build and a tested adapter in local main. Its discrete raise mapping, public-statistic definitions and RNG differ from desktop PokerTH and are documented. Human realism, strategic strength and solver agreement remain unverified.

The subsequent [behavior review](review/pokerth-behavior.md) ran a live game and sampled 150 hands across six 100-BB games, checking 1,054 native decisions without illegal actions or chip-conservation failures. It records a plausible live hand, sizing changes, a position shortcut and descriptive action frequencies. Rayner clarified that one unusual bluff is not grounds to dismiss the simulator. These observations remain review notes and proposed refinements, not a rejection of PokerTH or a new blocker for Stage 2B. No opponent policy was changed.

Still to decide:

- The first useful tool set, its input/output contracts and evidence representation.
- How to represent and compare opponent hypotheses and tentative leaks without inventing calibrated probabilities.
- Sources and applicability checks for verified poker strategy references or solver outputs, including unavailable coverage.
- Exact OpenRouter models, authorized live-run spend, and richer tool-loop time/call limits and fallback behavior. The initial LLM environment must already enforce bounded calls, output and deadlines.
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
| D014 | Rayner requested committing and merging all current work as the solid starting baseline before agent logic | Consolidate remaining worktree notes into local main, preserve the reviewed environment as `baseline/stage-2a`, and base Stage 2B on this checkpoint or a later reviewed main revision |
| D015 | Rayner proposed pivoting to LLM players sharing table talk, including deceptive claims, while developing his own hero strategy | Preserve PokerKit and the tagged PokerTH baseline; make all-LLM opponents, public chat, independent private contexts and observable decision influence the next product direction |
| D016 | Rayner explicitly clarified the project's primary use case: create an agent harness that lets his bot beat other LLM agents at poker | Make competitive performance the objective of the playing harness and evaluation; use same-model comparisons to isolate harness gains and broader opponent models to assess competitiveness. Table talk, the UI and traces support this objective. Superiority remains an outcome to demonstrate |
| D017 | Rayner requested a terminal/pixel-inspired UI matching his reference, with a light mode as well, and assigned it to the frontend chat | Implement a compact readable workspace in both themes, preserving real baseline controls/traces and preparing capability-aware LLM seat/chat views |
| D018 | Rayner directed backend work toward a common player interface, configurable instructions including active bluffing versus unprescribed strategy, and interchangeable OpenRouter models | Implement isolated per-seat LLM policies and public chat, with model/profile/harness/chat settings separated; add versioned benchmark presets and run records without treating mock games as performance evidence. D019 supersedes the initial bluff-directed profile choice |
| D019 | Rayner clarified that bluff-directed wording sounds too deliberate and that players should not constantly bluff | Use neutral task/objective/rules/chat instructions for ordinary players, leaving tactical choices to each model. Remove the initial bluff-directed profile and preset; preserve configurable prompts for explicit future experiments without bluff quotas or rewards |
| D020 | Rayner chose a six-seat baseline and explicitly confirmed choosing his hero's poker actions and messages manually, with an option for the LLM to take over | Build five LLM opponents on a reusable stable configuration, manual legal-action/chat controls and safe takeover. Automated mode has six LLMs. This supersedes the earlier proposed four-player default; manual/mixed runs are not autonomous performance evidence |

## Keeping this current

The integration chat updates this brief when Rayner accepts or changes direction, when a reviewed milestone changes the project status, or when integration changes the interfaces. Increment the revision and timestamp with material changes, update the current summary, and append or supersede the relevant decision record. Keep implementation details in their owning documents.

Other workstreams keep evidence and proposals in their own documentation and report the shared-context revision they used in milestone handoffs. They should read the live brief again before making a scope or interface decision. Do not promote a proposal to an accepted project decision or overwrite another workstream's files to synchronize context. Coordinate changes through the integration chat and direct user instructions. New worktrees must receive the shared-context pointer before their next assignment.
