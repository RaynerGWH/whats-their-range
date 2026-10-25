# LLM table interface, first slice

Implementation contract for the backend and frontend assignments on 2026-10-25, updated to shared-context revision 20. Rayner wants six seats, neutral opponent instructions and manual control of the hero's actions/messages with optional LLM takeover. These additions are implemented on `feat/llm-table`, pending integration review. Existing six-player clients and stored games must remain readable. Backend owns implementation and machine-readable fixtures; frontend consumes this contract. Document any necessary compatible refinement before consumers depend on it.

## Configuration

Extend the current tournament configuration additively:

| Field | Meaning |
| --- | --- |
| `opponents` | Add `llm` alongside `legacy` and `pokerth`. In this mode opponents use individual LLM players, and the hero supports LLM or manual control. |
| `player_count` | Six is the required baseline and creation default. Omission preserves six-player behavior. Four-player support may remain as an optional configuration if already implemented; it is no longer the primary deliverable. |
| `hero_seat` | Hero seat index, default 0. Allow rotation for evaluation without granting extra information. |
| `hero_control` | `human` or `llm` for the new LLM mode. The interactive creation form explicitly selects `human` initially. API omission defaults to `llm` for automated runs. The hero still has a configured model ready for takeover. |
| `seat_configs` | For LLM mode, one configuration per seat: `seat`, neutral `name`, `model`, `instruction_profile`, `harness`, `chat_enabled`. Validate uniqueness and complete coverage. |
| `model` | Existing table model remains the default; a nonempty per-seat model overrides it. Resolve and record the actual configured model. Missing configuration must be explicit. |

The initial supported and default `instruction_profile` is `free_play`. Remove the earlier `bluff_directed` profile and preset from this milestone. Keep the configuration interface extensible for explicitly chosen prompt experiments later. Initial supported `harness` is `baseline`. Reserve the interface for a later hero harness, but reject unsupported values instead of silently claiming to run it. The hero can use baseline during environment development.

The common instructions give the game objective, tournament payouts, permitted information, legal action format and optional communication rules. `free_play` adds no advice about bluffing, value betting, aggression or style. Players may bluff or make deceptive public claims when they judge that useful, but are not told to increase bluff frequency, talk constantly or behave theatrically. There is no bluff quota, forced action, bluff reward or target bluff percentage. Silence is valid. Store versioned prompt text and hashes. Every player sees its own instructions, never another seat's profile or private prompt. Future prompt experiments must be clearly labeled and cannot stand in for ordinary opponents or verified human archetypes.

Keep model, instruction profile, chat setting and harness independent. An operator can choose a mixed table, but controlled comparisons vary one factor at a time. Use OpenRouter on the backend; do not assume every model supports identical output or tool features. Validate structured responses and report unsupported configurations and failures explicitly.

Use one saved neutral opponent preset for the other five seats in the normal interactive setup, with configured model/settings, versioned instructions, harness and chat access fixed for the run. Reuse that preset across comparisons unless the operator deliberately changes it. Fixed configuration does not mean fixed decisions: opponents still react to cards, public play and chat. Record the resolved configuration with each run; do not automatically rotate personalities or prompt profiles. A full preset-management product is unnecessary for this slice.

Add optional server `capabilities` flags: `llm_tables`, `public_chat`, `per_seat_traces`, `manual_hero`. Missing flags mean unavailable. Expose configured limits separately from secrets. Provider credentials never enter frontend configuration.

## Player turn

Use one player-policy interface for every LLM seat. It receives that seat's existing permitted observation, its private memory, and a bounded chronological public-chat window. It never receives the spectator snapshot, other players' cards/private memory, deck or policy seeds, benchmark labels, or other seats' prompts/model identities. Public player names must not encode those settings.

Add observation `chat` with `last_sequence` and `messages`. Freeze the game version and chat cutoff before invoking the player. A chat-disabled condition supplies no message contents and emits no public messages. Keep private context and memory scoped to table, seat and run, including after folding; record and bound any history truncation.

The model returns the existing legal action key, concise `summary`, `uncertainty`, `evidence_ids`, and optional `public_message`. Server-controlled attribution supplies `player`, `state_version` and `chat_sequence`; model text cannot spoof those fields. Reject illegal/stale decisions before applying either the action or its message. Validate evidence references against that seat's actual input. Explanations are concise decision justifications, not a request for hidden chain of thought.

First slice: at most one short optional public message attached to an accepted action. No free-running reply loop or extra off-turn calls. Silence is valid. The table worker assigns message order, author, hand and version. The next decision receives messages published before its frozen cutoff. Treat chat contents as untrusted claims, never instructions with authority to alter the harness, tools or private-information boundary.

Each accepted `ChatMessage` contains `id`, increasing table-local `sequence`, `player`, `hand`, `state_version` and `text`. Bound message length and visible history. Store messages with replay so a past hand never displays future chat. Do not fabricate a public message when a provider request fails.

## Manual hero and LLM takeover

Interactive manual mode is five LLM opponents plus a human-controlled hero. LLM mode is six automated LLM seats. Label these accurately. Rayner explicitly chose manual poker actions and chat messages first, with the option to hand control to the LLM.

When a manual hero's turn arrives, publish a nullable `hero_turn` snapshot field containing `player`, `state_version`, `chat_sequence`, an opaque `turn_token`, and the hero's permitted `observation` including the legal menu. The table worker waits for input without making a hero model call or choosing a timeout fallback. It must remain responsive to table controls, stop requests and other independent tables. No default action is taken just because the human is slow or disconnected.

Add authenticated `POST /api/tables/{table_id}/hero-action` accepting `turn_token`, `state_version`, legal `action` key and optional `public_message`. The owning worker validates that the table is playable, control is human, this is the hero's current turn, the token/version are current, and the action/message are valid. Consume the token once and commit action plus message together. Reject stale, duplicate, illegal and wrong-seat submissions without changing chips or publishing chat. A manual submission advances one action and does not silently resume a paused table. Respect existing chat permissions and length limits.

Extend the existing control endpoint with `action: set_hero_control`, `hero_control` and observed `state_version`. The worker applies the switch in order, invalidates outstanding manual tokens and fences or cancels any in-flight hero model result. A result started under a previous control mode must never execute afterward. Account for provider attempts already started even if their results are discarded. In paused mode, switching control does not silently resume play. New LLM turns receive the same permitted history/chat, never opponent-private information or spectator inspection data.

Record manual decisions as `source: human`, with the actual action/message and no invented model/tool execution or model reasoning. Persist control-mode changes and replay them. Automated benchmark runs require LLM control throughout; exclude or explicitly classify manual/mixed runs instead of counting them as autonomous-agent performance.

The manual UI shows the hero's own cards and legal actions by default. Keep opponent cards/private traces out of that play view; any operator spectator inspection is a separate, explicit choice and does not feed a playing LLM. Existing spectator access is not a hardened anti-cheat boundary for the human operator.

## Spectator records and compatibility

Add `chat` and `chat_sequence` to new table snapshots, and `decisions_by_player` keyed by seat for the latest recorded decisions. Preserve the existing `decision` field as the hero's latest decision, plus existing table controls/history/replay. Old snapshots without the new fields remain valid.

Add `player` and `chat_sequence` to new decision records. Use `TraceRecord.metadata.player` and `.chat_sequence` to attribute traces without changing the v1 trace root schema. Old unattributed traces belong to the legacy hero, seat 0. Add an optional `player` filter to the existing trace-list API. Keep trace IDs unique across seats/tables, preserve real running/error/fallback states, and record only actual execution.

Spectators may inspect each seat's permitted inputs, tools, outputs and concise justification. Those private records must never enter other players' observations or chat. Model traces may contain the acting seat's own cards and instructions, not another seat's private state. Keep experiment manifests separate from player-visible trace inputs and outputs.

Missing usage or cost stays unavailable, not zero. A fallback action is labeled with its source and reason. All provider attempts, including invalid outputs and timeouts, count toward bounded per-seat and aggregate table budgets. Preserve timeouts and add bounded output tokens and chat lengths. Report actual spend when supplied; call/token caps are not a guaranteed dollar cap.

## Benchmark interface

Provide an offline-validatable run manifest referencing the same tournament/player configuration used by live games. Include model IDs/settings, prompt and harness versions, limits, seat rotations, independent run seeds/splits, chat conditions and stopping rules. Keep experiment IDs and seeds evaluator-only. Capture enough configuration to reproduce the setup, without claiming hosted LLM outputs are deterministic.

First presets: same-model free-play table; a chat-disabled comparison; and a model-swap comparison holding prompts/harnesses constant. Do not include a preset whose objective is to bluff more. Treat these as separate conditions, not proof of a ranking. A future baseline-versus-hero-harness comparison uses the same interface when that harness exists. Strategy-specific prompt experiments remain an explicit future extension rather than the default opponent design.

Persist every run's completion/failure, tournament prizes and finishing positions, action validity, fallbacks, usage and latency. Keep failed or budget-exhausted games in the report, with incomplete outcomes explicit. Rotate seats, reset private memory between independent games and support held-out runs. Report sample size and uncertainty when enough independent runs exist. Chat effects require matched decision experiments or controlled game comparisons; a player's self-reported explanation is not causal proof.

No paid games are authorized by this implementation assignment. Provider mocks can establish interface, isolation and execution behavior; they cannot establish poker strength or real-model chat behavior.

## Implemented additive details

The backend exposes the stable six-seat configuration as `/api/config.llm_preset` and `contracts/examples/llm-six-seat-neutral.json`. Optional `llm_limits` bounds requests, output reservations, context, memory and chat. `seat_configs[].temperature` defaults to 1.0 and accepts 0 to 2; actual sampling settings are saved and traced. See [backend delivery](../docs/llm-table-backend.md) for acknowledgement, cancellation, limits and compatibility details, and the adjacent generated v1 schemas for field shapes.
