# Poker agent direction

Project direction clarified with Rayner on 2026-10-25 (Asia/Singapore). This describes the intended design, not functionality already implemented. It guides the next backend and strategy milestone; the first-milestone contracts and branches remain unchanged.

The [shared project context](project-context.md) holds the current accepted decisions, priorities and audited implementation status. Keep that brief current when this design changes. Specific tool capabilities below remain proposals until their contracts and milestone are agreed.

The intended release is a noncommercial research demo shared on GitHub and LinkedIn, with reproducible setup, inspectable decisions and clearly stated limitations.

## Decision authority

The LLM is the poker decision-maker. It uses the permitted game context, observed opponent behavior, numerical tools and applicable strategy references to choose a legal action. It may request more evidence, compare competing explanations, reconsider a candidate and choose an exploitative adjustment when the evidence supports one.

There is no fixed percentage weighting between GTO and contextual judgment. Tools inform the decision without prescribing it through hand-category rules. Numerical calculations remain reproducible. Any action mixing must be explicit and auditable; model output variability is not a calibrated mixed strategy.

The ambition is player-like judgment: interpreting the whole betting line, examining plausible opponent holdings and intentions, anticipating responses and future streets, and recognizing uncertainty. Rayner's player reference is Garrett Edelstein. This is a reference for the desired depth of analysis, not a claim that we can reproduce his personal strategy or playing strength. Tournament objectives and payouts remain part of this project's actual decision context.

## One decision system

Strategy is part of the backend. The strategy work defines useful poker analyses, tool semantics, hypothesis comparison and decision instructions. Backend work implements the observation and evidence pipeline, LangGraph execution, model and tool interfaces, budgets, persistence and action enforcement. Both workstreams implement one shared decision process.

The agreed simulated-game architecture retains PokerKit for game state, cards, bets, pots and legal execution. PokerTH's opponent logic will choose actions for the other seats through an adapter, using each player's permitted observation. Our LLM chooses hero actions. The game advances after each validated action and produces public history for later decisions. PokerKit does not supply opponent strategy or a GTO solver; solver access remains a separate tool integration. Stage 2A now assigns the backend chat the environment integration using the existing hero interface. Stage 2B will implement the fuller strategy described below. The PokerTH adapter is not implemented yet.

The target flow is:

1. Assemble a versioned permitted observation and relevant public opponent evidence.
2. Let the LLM identify plausible explanations of the situation and what further information would distinguish them.
3. Execute requested tools, including bounded parallel scenario work where useful, against the same frozen observation.
4. Return results with their sources, assumptions, uncertainty and applicability limits. The LLM may revise its assessment or request further work within explicit budgets.
5. Have the LLM submit its final action with a concise justification, evidence references and material uncertainty.
6. Validate the action and observed state version before the table worker applies it.

LangGraph manages this bounded model/tool loop. A mandatory sequence of every possible analysis is not required for every hand. Existing heuristic play remains available as a separately named comparison policy and clearly labeled operational fallback.

## Proposed tool capabilities

These are design targets requiring implementation and review:

- **Opponent evidence:** Retrieve public actions and relevant opportunities by situation, including position, sizing and stack context. Distinguish observed facts, tentative tendencies and proposed exploits. Observe public play even after hero folds, keeping memory isolated per table.
- **Hand and range calculations:** Assess hand features and conditional outcomes against explicitly supplied range hypotheses. Identify unsupported side-pot, multiway or tournament assumptions. Keep random-range equity separate from inferred-range analysis.
- **Strategy references:** Retrieve verified material or solver results when available, with provenance and the modeled game, ranges, sizes, stacks and payoff assumptions. Return unavailable or mismatched results honestly. An LLM recollection is not a verified solver result.
- **Scenario comparison:** Compare legal actions under competing opponent hypotheses and possible future responses or streets. Preserve disagreement and identify what makes a candidate succeed or fail. Hypothetical future states never come from the simulator's actual future deck or outcomes.
- **Critique:** Check for unsupported reads, omitted alternatives, inconsistent plans and reliance on weak assumptions. Agreement between model-generated hypotheses is not additional observed evidence.

All tools use permitted observations and evidence. Opponent hole cards, simulator profiles, credentials and future state remain excluded. Tool results and model summaries are bounded, structured and traceable; stored explanations describe decisions and assumptions rather than private internal reasoning.

Rayner additionally requires attention to evaluation leakage through simulator knowledge. Apply the permitted-information boundary to identifiers, tool results, retrieved documents and memories as well as explicit card/profile fields. Keep experiment seeds, hidden opponent-policy settings and source code outside the playing agent's access. Preserve legitimate learning from public actions. Use independently held-out opponent behavior to assess whether performance generalizes beyond known scripts. The [shared project context](project-context.md#evaluation-integrity-finding) records the original metadata leak, Stage 1's delivered fixes and remaining evaluation risks.

## Current implementation and next specification

The skeleton has fixed assessment and evidence nodes followed by one optional LLM decision call. It has no model-directed tool loop. The separate strategy branch supplies deterministic candidate labels and conditional calculations; it contains no integrated GTO solver or verified strategy dataset. The observability branch records execution, and the evaluation branch measures baseline policies. These pieces do not yet implement the target above.

The next shared specification should follow one decision through the entire process using hands reviewed with Rayner. Define the observation, tool requests and responses, hypothesis representation, decision output and failure behavior together. Select a limited initial tool set, provider requirements and total decision budgets before implementation. Review evidence use and strategic judgments alongside legality, reproducibility, latency, cost and held-out outcomes. Persuasive explanations alone do not establish decision quality.
