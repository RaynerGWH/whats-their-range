# Poker agent direction

Project direction clarified with Rayner on 2026-10-25 (Asia/Singapore). This describes the intended design, not functionality already implemented. It guides the next backend and strategy milestone; the first-milestone contracts and branches remain unchanged.

The [shared project context](project-context.md) holds the current accepted decisions, priorities and audited implementation status. Keep that brief current when this design changes. Specific tool capabilities below remain proposals until their contracts and milestone are agreed.

The intended release is a noncommercial research demo shared on GitHub and LinkedIn, with reproducible setup, inspectable decisions and clearly stated limitations.

Rayner's subsequent pivot makes the next environment a six-seat table with public conversation, while the hero remains the main strategy-development target. He explicitly wants to choose his hero's actions and messages manually first, with optional LLM takeover for a fully automated six-LLM table. The five opponents retain a saved neutral configuration. OpenRouter model, private instruction profile, chat access and harness remain independently configurable. The initial profile provides the task, objective, rules and optional chat without strategy advice. Following Rayner's clarification, do not direct ordinary players toward increased bluffing; tactical choices remain with the model. The [playing and evaluation harness plan](llm-agent-harness.md) and [shared interface](../contracts/llm-table-v1.md) record the assigned environment/UI slices and unresolved live-run budgets. The tagged six-player PokerTH baseline remains available.

## Decision authority

Under LLM control, the LLM is the poker decision-maker. It uses the permitted game context, observed opponent behavior, numerical tools and applicable strategy references to choose a legal action. It may request more evidence, compare competing explanations, reconsider a candidate and choose an exploitative adjustment when the evidence supports one. In the new interactive manual mode, Rayner chooses the hero's action instead; the engine still validates it, and the runtime does not call the hero model until LLM control is selected.

There is no fixed percentage weighting between GTO and contextual judgment. Tools inform the decision without prescribing it through hand-category rules. Numerical calculations remain reproducible. Any action mixing must be explicit and auditable; model output variability is not a calibrated mixed strategy.

The ambition is player-like judgment: interpreting the whole betting line, examining plausible opponent holdings and intentions, anticipating responses and future streets, and recognizing uncertainty. Rayner's player reference is Garrett Edelstein. This is a reference for the desired depth of analysis, not a claim that we can reproduce his personal strategy or playing strength. Tournament objectives and payouts remain part of this project's actual decision context.

## One decision system

Strategy is part of the backend. The strategy work defines useful poker analyses, tool semantics, hypothesis comparison and decision instructions. Backend work implements the observation and evidence pipeline, LangGraph execution, model and tool interfaces, budgets, persistence and action enforcement. Both workstreams implement one shared decision process.

The implemented baseline retains PokerKit for game state, cards, bets, pots and legal execution. Separate LLM players now have private contexts and shared public messages, with manual hero control and optional LLM takeover. PokerTH and legacy heuristic opponents remain comparison modes. The game advances after each validated action and produces public history for later decisions. PokerKit does not supply opponent strategy or a GTO solver; solver access remains a separate tool integration. Stage 2A and Stage 2B's environment/UI slice are complete and reviewed into local main. The fuller hero strategy and initial solver access remain unfinished. See the [integration review](review/llm-table-integration.md) for verification with mocked providers.

The target flow is:

1. Assemble a versioned permitted observation and relevant public opponent evidence.
   Freeze the public chat sequence visible to this decision. Treat peer messages as claims and game data, with no authority to change instructions or tool permissions.
2. Let the LLM identify plausible explanations of the situation and what further information would distinguish them.
3. Execute requested tools, including bounded parallel scenario work where useful, against the same frozen observation.
4. Return results with their sources, assumptions, uncertainty and applicability limits. The LLM may revise its assessment or request further work within explicit budgets.
5. Have the LLM submit its final action with a concise justification, evidence references and material uncertainty.
6. Validate the action and observed state version before the table worker applies it.

LangGraph manages this bounded model/tool loop. A mandatory sequence of every possible analysis is not required for every hand. Existing heuristic play remains available as a separately named comparison policy and clearly labeled operational fallback.

## Proposed tool capabilities

These are design targets requiring implementation and review:

- **Opponent evidence:** Retrieve public actions and relevant opportunities by situation, including position, sizing and stack context. Distinguish observed facts, tentative tendencies and proposed exploits. Observe public play even after hero folds, keeping memory isolated per table.
- **Table-talk evidence:** Retrieve attributed public statements and their timing relative to bets. Compare claims with permitted public behavior, preserve competing interpretations and avoid promoting a claim to verified card information. Keep private analysis and evaluator truth outside the conversation.
- **Hand and range calculations:** Assess hand features and conditional outcomes against explicitly supplied range hypotheses. Identify unsupported side-pot, multiway or tournament assumptions. Keep random-range equity separate from inferred-range analysis.
- **Strategy references:** Retrieve verified material or solver results when available, with provenance and the modeled game, ranges, sizes, stacks and payoff assumptions. Return unavailable or mismatched results honestly. An LLM recollection is not a verified solver result.
- **Scenario comparison:** Compare legal actions under competing opponent hypotheses and possible future responses or streets. Preserve disagreement and identify what makes a candidate succeed or fail. Hypothetical future states never come from the simulator's actual future deck or outcomes.
- **Critique:** Check for unsupported reads, omitted alternatives, inconsistent plans and reliance on weak assumptions. Agreement between model-generated hypotheses is not additional observed evidence.

All tools use permitted observations and evidence. Opponent hole cards, simulator profiles, credentials and future state remain excluded. Tool results and model summaries are bounded, structured and traceable; stored explanations describe decisions and assumptions rather than private internal reasoning.

Rayner additionally requires attention to evaluation leakage through simulator knowledge. Apply the permitted-information boundary to identifiers, tool results, retrieved documents and memories as well as explicit card/profile fields. Keep experiment seeds, hidden opponent-policy settings and source code outside the playing agent's access. Preserve legitimate learning from public actions. Use independently held-out opponent behavior to assess whether performance generalizes beyond known scripts. The [shared project context](project-context.md#evaluation-integrity-finding) records the original metadata leak, Stage 1's delivered fixes and remaining evaluation risks.

## Current implementation and next specification

The integrated six-seat environment uses a neutral per-seat LLM policy with one bounded model decision, own memory and public chat. The hero can instead be played manually and handed back to the LLM. The older hero-only path with PokerTH/legacy opponents retains fixed assessment and evidence nodes followed by one optional model call. Neither path has a model-directed tool loop. The strategy module supplies deterministic candidate labels and conditional calculations but is not wired into live selection, and no solver is integrated. The shared-path LLM benchmark runner and combined UI are verified with provider mocks, as recorded in the [integration review](review/llm-table-integration.md). These pieces do not yet establish the target judgment system or competitive strength.

The next shared specification should follow one decision through the entire process using hands reviewed with Rayner. Define the observation, tool requests and responses, hypothesis representation, decision output and failure behavior together. Select a limited initial tool set, provider requirements and total decision budgets before implementation. Review evidence use and strategic judgments alongside legality, reproducibility, latency, cost and held-out outcomes. Persuasive explanations alone do not establish decision quality.
