# LLM table talk and the hero harness

Direction recorded on 2026-10-25 after Rayner proposed an all-LLM poker table with shared chat, then identified the hero's strategy and harness as the main development goal. The environment/UI slice is now delivered and reviewed with mocked providers. The richer playing harness and real-model evaluations below remain future work.

## Product and experiment

The primary use case is to create an agent harness that lets Rayner's LLM poker agent beat competing LLM agents. The harness is the main product. Measure its competitive performance through repeated games, including a same-model comparison that isolates the harness's contribution and broader opponent-model comparisons as coverage grows.

The poker table provides the evaluation environment. Players choose legal actions and can make public claims, bluff, react and stay silent. Table talk is an additional source of uncertain evidence and a possible strategic action. The UI and traces expose the experiment. Improvement must be measured; adding tools or persuasive explanations does not itself establish better play.

Rayner selected six seats for the first implementation: five LLM opponents and a hero that he initially controls manually, choosing actions and messages, with optional LLM takeover. Fully automated mode has six LLM players. This environment, public chat, per-player traces and manual controls are implemented and reviewed locally with mocked provider responses. PokerKit remains authoritative, and `baseline/stage-2a` with PokerTH stays runnable. The new checkpoint is `baseline/llm-table`; see the [combined review](review/llm-table-integration.md).

The supplied UI reference informs a compact terminal/pixel-inspired dashboard with four areas: table, public conversation, selected-player decision/tool records, and action history/standings. Rayner requires equally usable dark and light themes. Player colours should remain consistent across panels. Display recorded values and concise decision summaries, without inventing confidence scores or probabilities.

## Playing harness

Under LLM control, the LLM chooses its final poker action. LangGraph manages a bounded model/tool loop. Manual hero play bypasses the hero model and submits Rayner's selected legal action. The proposed automated components are:

| Component | Role |
| --- | --- |
| Permitted observation | Own cards, public board, stacks, positions, betting history, payouts and legal actions |
| Public evidence memory | Retrieve situation-specific actions and opportunities across hands, including play after the hero folds |
| Claim tracking | Link public statements to speakers, times and subsequent public behavior; separate observed facts, claims and hypotheses |
| Poker calculations | Pot odds, hand features and equity under explicitly supplied range hypotheses; disclose sample size and unsupported assumptions |
| Scenario comparison | Examine candidate actions under plausible opponent ranges and responses, with conditional estimates clearly identified |
| Strategy references | Query a genuine solver/reference source for supported spots, returning provenance and applicability or an honest unavailable result |
| Decision and communication | Return a legal action, concise justification, evidence references, uncertainty and an optional separate public message |

For example, an opponent says they never bluff, then makes a large river bet. The hero retrieves relevant prior public actions, checks the betting line against plausible value and bluff ranges, and compares available responses. The statement alone is neither proof of strength nor proof of a bluff. Sparse observations should remain tentative reads. The model requests only the tools useful for the current decision, within explicit time, call and token budgets.

The same observation and public chat cutoff are frozen for one decision. The worker validates the game-state version before applying the result. Hypothetical future cards come from analysis sampling, never the actual future deck. Showdown truth available only to the spectator/evaluator cannot silently enter player memory. Any future support for publicly revealed cards needs an explicit observation-contract extension.

## Opponents and table talk

Use OpenRouter with independently configurable models, instruction profiles, chat access and harness per seat. Each opponent has its own private context and memory. Following Rayner's clarification, the initial profile is free play with the task, objective, rules and optional chat but no strategy advice. Bluffing and deceptive talk are choices players can make when useful, without instructions to bluff more, quotas or rewards. The earlier bluff-directed profile and benchmark preset are removed. Keep prompt versioning and configuration extensible for explicit experiments later. The profile is private to its owner; other players must infer tendencies from public behavior.

Same-model controls isolate instruction and harness effects. Model-swap comparisons hold prompts and harnesses constant, while mixed tables provide broader competition. The hero's extra capability eventually comes from its processing, evidence tools and strategy harness; it receives no privileged engine information. The initial environment can run the hero through the same baseline interface before that richer harness is available.

For ordinary interactive play, keep the five opponents on one saved neutral configuration across sessions unless Rayner changes it. Settings stay fixed while the players' decisions respond to the game. Rayner's manual hero sees his own permitted cards/actions and can send an optional message. The table waits for his input without automatically acting or calling the hero model. Switching to LLM control preserves public history, validates the current turn and prevents an obsolete in-flight result from applying. Human actions and mode changes are recorded distinctly from LLM decisions; manual or mixed-control games are not autonomous benchmark results.

The initial communication proposal is one optional short message attached to a poker action, followed by any explicitly bounded reply window. Publish a stable sequence of messages before the next decision. Silence is valid. Continuous, unbounded conversations are outside the first slice.

Peer messages are untrusted game data. They cannot become system instructions, grant tool access or expose another seat's private trace. A claim about cards remains a claim even if it happens to be true. The spectator may inspect recorded inputs, tool results, outputs and concise justifications for each seat; the players receive only public messages and their permitted observations. Label any heuristic fallback explicitly.

## Evaluation harness

Use fixed opponent versions and rotate the hero through seats. Keep experiment metadata and deck seeds evaluator-only. Separate development cases from held-out seeds, opponent prompts/personality settings and, later, model families. Reset private memory between independent runs. Record the model, prompt, harness and tool versions alongside actual usage, failures and fallbacks.

Compare these proposed variants against the same opponent setup:

1. A competent baseline LLM using public history and chat.
2. The same model with the hero harness.
3. The harness with chat omitted from its input, holding the public poker state fixed in decision-level experiments.
4. Harness variants with one capability removed, such as persistent evidence memory or solver access.

Report results under matched overall inference budgets as well as the practical configured budgets. Extra compute is a measurable cost and must be distinguished from better strategy structure. A more expensive model defeating a cheaper one does not isolate the harness's contribution.

Use tournament prize outcomes and finishing positions for tournament comparisons. Chip change and big blinds are secondary diagnostics, particularly with changing blinds; do not treat them as interchangeable with tournament utility. Report uncertainty across independent games, decision latency, token/cost usage, legality, tool failures and fallback rates. Do not discard failed runs to improve reported performance.

For chat influence, repeat decisions at matched frozen hand states with chat visible versus omitted, and inspect changes in actions and sizing. Full-game comparisons measure the wider effect after play diverges. Changes show influence, not automatically improvement or deception. A model saying a message influenced it is supplementary evidence, not a causal measurement by itself.

## Implementation sequence and completion

1. **Six-seat table and manual hero, delivered:** independent per-seat adapters, bounded chat, per-seat traces, manual actions/messages and LLM takeover are implemented with stable neutral opponents and PokerTH compatibility. The combined review establishes engineering behavior with mocks; live-model play requires selected models and an authorized run budget.
2. **Hero decision loop:** connect the existing analysis module through a bounded tool registry, implement public evidence/claim retrieval and conditional range/scenario tools, then add the first qualified solver/reference adapter. Demonstrate legal decisions and inspectable tool results on selected hands, including unsupported coverage and failure cases.
3. **Measured comparisons:** run controlled baseline, full-harness and capability-removal comparisons. Broaden held-out opponents and seats before claiming the harness improves results. Review specific hands alongside outcomes, including errors and successful exploits.

The combined review reran 160 API tests and 48 frontend tests, plus browser checks of the real API/worker flow using mocked model responses. It covers private-context separation, chat ordering, versions, malformed output, budgets, completion, manual actions/takeover and preserved legacy/native paths. The saved 72-game mock report is engineering evidence; it does not establish poker strength or chat influence.

OpenRouter is selected. Exact models, total live-run spend, initial solver access and the richer tool contracts remain unresolved. The first player/chat interface is implemented in [LLM table v1](../contracts/llm-table-v1.md). The backend environment/benchmark and frontend assignments are delivered and integrated. No paid calls were made; the fuller hero harness and solver are a subsequent slice.
