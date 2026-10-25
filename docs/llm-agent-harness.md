# LLM table talk and the hero harness

Direction recorded on 2026-10-25 after Rayner proposed an all-LLM poker table with shared chat, then identified the hero's strategy and harness as the main development goal. This is the next implementation plan. It does not describe functionality already present in the application.

## Product and experiment

The primary use case is to create an agent harness that lets Rayner's LLM poker agent beat competing LLM agents. The harness is the main product. Measure its competitive performance through repeated games, including a same-model comparison that isolates the harness's contribution and broader opponent-model comparisons as coverage grows.

The poker table provides the evaluation environment. Players choose legal actions and can make public claims, bluff, react and stay silent. Table talk is an additional source of uncertain evidence and a possible strategic action. The UI and traces expose the experiment. Improvement must be measured; adding tools or persuasive explanations does not itself establish better play.

The first implementation scope is four players: the hero and three LLM opponents, with six-player compatibility. Keep PokerKit authoritative. Preserve `baseline/stage-2a` and its PokerTH mode as a runnable comparison. Four starting players, LLM opponents, shared chat and per-player trace selection all require implementation; the existing configuration still starts six players and offers legacy or PokerTH opponents.

The supplied UI reference informs a compact terminal/pixel-inspired dashboard with four areas: table, public conversation, selected-player decision/tool records, and action history/standings. Rayner requires equally usable dark and light themes. Player colours should remain consistent across panels. Display recorded values and concise decision summaries, without inventing confidence scores or probabilities.

## Playing harness

The LLM chooses its final poker action. LangGraph manages a bounded model/tool loop. The proposed components are:

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

Use OpenRouter with independently configurable models, instruction profiles, chat access and harness per seat. Each opponent has its own private context and memory. Rayner requested a free-play condition with the task, objective, rules and optional chat but no strategy advice, and a bluff-directed condition that encourages strategic bluffing without forcing actions. Version these prompts. The profile is private to its owner; other players must infer tendencies from public behavior.

Same-model controls isolate instruction and harness effects. Model-swap comparisons hold prompts and harnesses constant, while mixed tables provide broader competition. The hero's extra capability eventually comes from its processing, evidence tools and strategy harness; it receives no privileged engine information. The initial environment can run the hero through the same baseline interface before that richer harness is available.

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

1. **Four-player LLM table:** parameterize player count through game state, observations, statistics, workers, persistence, replay and UI. Add independent per-seat LLM adapters, bounded public chat and per-seat trace selection. Preserve six-player PokerTH compatibility. Mock provider tests establish engineering behavior; actual LLM play requires a selected provider and an authorized live-call budget.
2. **Hero decision loop:** connect the existing analysis module through a bounded tool registry, implement public evidence/claim retrieval and conditional range/scenario tools, then add the first qualified solver/reference adapter. Demonstrate legal decisions and inspectable tool results on selected hands, including unsupported coverage and failure cases.
3. **Measured comparisons:** run controlled baseline, full-harness and capability-removal comparisons. Broaden held-out opponents and seats before claiming the harness improves results. Review specific hands alongside outcomes, including errors and successful exploits.

The existing 128 API tests and 16 frontend tests cover the Stage 2A baseline, not these new capabilities. New acceptance evidence must include private-context separation, chat ordering, action versions, malformed model output, budget exhaustion, four-player completion, six-player regression coverage and observable per-seat records.

OpenRouter is selected. Exact models, total live-run spend, initial solver access and the richer tool contracts remain unresolved. The first player/chat interface is specified in [LLM table v1](../contracts/llm-table-v1.md). Rayner assigned [backend players and benchmark setup](tasks/backend-llm-table.md) and [frontend terminal UI](tasks/frontend-terminal-ui.md) concurrently. These assignments do not establish runtime completion or authorize paid calls. The fuller hero harness and solver are a subsequent slice.
