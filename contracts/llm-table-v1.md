# LLM table interface, first slice

Implementation contract agreed for the backend and frontend assignments on 2026-10-25, using shared-context revision 18. These additions are not yet implemented. Existing six-player clients and stored games must remain readable. Backend owns implementation and machine-readable fixtures; frontend consumes this contract. Document any necessary compatible refinement before consumers depend on it.

## Configuration

Extend the current tournament configuration additively:

| Field | Meaning |
| --- | --- |
| `opponents` | Add `llm` alongside `legacy` and `pokerth`. In this mode all seats use individual LLM players, including the hero. |
| `player_count` | Support 4 and 6 initially. Omission preserves the existing six-player behavior. The new LLM creation form starts with 4. |
| `hero_seat` | Hero seat index, default 0. Allow rotation for evaluation without granting extra information. |
| `seat_configs` | For LLM mode, one configuration per seat: `seat`, neutral `name`, `model`, `instruction_profile`, `harness`, `chat_enabled`. Validate uniqueness and complete coverage. |
| `model` | Existing table model remains the default; a nonempty per-seat model overrides it. Resolve and record the actual configured model. Missing configuration must be explicit. |

Initial `instruction_profile` values are `free_play` and `bluff_directed`. Initial supported `harness` is `baseline`. Reserve the interface for a later hero harness, but reject unsupported values instead of silently claiming to run it. The hero can use baseline during environment development.

The common instructions give the game objective, tournament payouts, permitted information, legal action format and optional communication rules. `free_play` adds no advice about bluffing, value betting, aggression or style. `bluff_directed` adds encouragement to seek strategic bluff/semi-bluff and deceptive table-talk opportunities while pursuing the same objective; it does not force an action or bluff frequency. Store versioned prompt text and hashes. Every player sees its own instructions, never another seat's profile or private prompt. These profiles test instruction effects, not verified human archetypes.

Keep model, instruction profile, chat setting and harness independent. An operator can choose a mixed table, but controlled comparisons vary one factor at a time. Use OpenRouter on the backend; do not assume every model supports identical output or tool features. Validate structured responses and report unsupported configurations and failures explicitly.

Add optional server `capabilities` flags: `llm_tables`, `public_chat`, `per_seat_traces`. Missing flags mean unavailable. Expose configured limits separately from secrets. Provider credentials never enter frontend configuration.

## Player turn

Use one player-policy interface for every LLM seat. It receives that seat's existing permitted observation, its private memory, and a bounded chronological public-chat window. It never receives the spectator snapshot, other players' cards/private memory, deck or policy seeds, benchmark labels, or other seats' prompts/model identities. Public player names must not encode those settings.

Add observation `chat` with `last_sequence` and `messages`. Freeze the game version and chat cutoff before invoking the player. A chat-disabled condition supplies no message contents and emits no public messages. Keep private context and memory scoped to table, seat and run, including after folding; record and bound any history truncation.

The model returns the existing legal action key, concise `summary`, `uncertainty`, `evidence_ids`, and optional `public_message`. Server-controlled attribution supplies `player`, `state_version` and `chat_sequence`; model text cannot spoof those fields. Reject illegal/stale decisions before applying either the action or its message. Validate evidence references against that seat's actual input. Explanations are concise decision justifications, not a request for hidden chain of thought.

First slice: at most one short optional public message attached to an accepted action. No free-running reply loop or extra off-turn calls. Silence is valid. The table worker assigns message order, author, hand and version. The next decision receives messages published before its frozen cutoff. Treat chat contents as untrusted claims, never instructions with authority to alter the harness, tools or private-information boundary.

Each accepted `ChatMessage` contains `id`, increasing table-local `sequence`, `player`, `hand`, `state_version` and `text`. Bound message length and visible history. Store messages with replay so a past hand never displays future chat. Do not fabricate a public message when a provider request fails.

## Spectator records and compatibility

Add `chat` and `chat_sequence` to new table snapshots, and `decisions_by_player` keyed by seat for the latest recorded decisions. Preserve the existing `decision` field as the hero's latest decision, plus existing table controls/history/replay. Old snapshots without the new fields remain valid.

Add `player` and `chat_sequence` to new decision records. Use `TraceRecord.metadata.player` and `.chat_sequence` to attribute traces without changing the v1 trace root schema. Old unattributed traces belong to the legacy hero, seat 0. Add an optional `player` filter to the existing trace-list API. Keep trace IDs unique across seats/tables, preserve real running/error/fallback states, and record only actual execution.

Spectators may inspect each seat's permitted inputs, tools, outputs and concise justification. Those private records must never enter other players' observations or chat. Model traces may contain the acting seat's own cards and instructions, not another seat's private state. Keep experiment manifests separate from player-visible trace inputs and outputs.

Missing usage or cost stays unavailable, not zero. A fallback action is labeled with its source and reason. All provider attempts, including invalid outputs and timeouts, count toward bounded per-seat and aggregate table budgets. Preserve timeouts and add bounded output tokens and chat lengths. Report actual spend when supplied; call/token caps are not a guaranteed dollar cap.

## Benchmark interface

Provide an offline-validatable run manifest referencing the same tournament/player configuration used by live games. Include model IDs/settings, prompt and harness versions, limits, seat rotations, independent run seeds/splits, chat conditions and stopping rules. Keep experiment IDs and seeds evaluator-only. Capture enough configuration to reproduce the setup, without claiming hosted LLM outputs are deterministic.

First presets: same-model free-play table; the same setup with a bluff-directed opponent; a chat-disabled comparison; and a model-swap comparison holding prompts/harnesses constant. Treat these as separate conditions, not proof of a ranking. A future baseline-versus-hero-harness comparison uses the same interface when that harness exists.

Persist every run's completion/failure, tournament prizes and finishing positions, action validity, fallbacks, usage and latency. Keep failed or budget-exhausted games in the report, with incomplete outcomes explicit. Rotate seats, reset private memory between independent games and support held-out runs. Report sample size and uncertainty when enough independent runs exist. Chat effects require matched decision experiments or controlled game comparisons; a player's self-reported explanation is not causal proof.

No paid games are authorized by this implementation assignment. Provider mocks can establish interface, isolation and execution behavior; they cannot establish poker strength or real-model chat behavior.
