# Backend: configurable LLM players and benchmark setup

Assigned by Rayner on 2026-10-25 to the existing **Backend: tracing and persistence** chat. Shared-context revision 18. Start `feat/llm-table` from the latest reviewed local `main` in the existing backend checkout, preserving `feat/pokerth-opponents`. Read the canonical shared brief and [LLM table interface](../../contracts/llm-table-v1.md) before implementation.

## Outcome

Deliver one shared player interface that lets every seat play through OpenRouter with its own model, private context, instructions and optional public table talk. The hero uses this interface too, ready for the richer strategy harness later. Supply configurable experiments comparing instruction and model choices. Keep the tagged PokerTH baseline runnable.

Rayner explicitly requested players encouraged to bluff and players merely told the task, rules and ability to chat, without prescribed strategy. Implement versioned `free_play` and `bluff_directed` prompts as independent configuration from model and harness. Never implement these by forcing poker actions. Mixed-model tables should be configurable immediately; same-model controls help isolate instruction or harness effects.

## Implementation

1. Implement the additive shared contract and publish examples/schema validation early. Parameterize 4 and 6 starting seats, hero seat rotation, observations, memory, workers, persisted decisions and replay. Preserve old configurations and stored sessions. Each table retains its own process and sequential state mutation.
2. Implement a per-seat policy adapter and private memory using the existing backend OpenRouter transport as a starting point. Reuse legal action semantics. Keep provider transport separate from instructions/harness. Record resolved models, actual calls and safe failures; verify official provider documentation when implementing unfamiliar capability requirements. Different model IDs must not require rewriting game logic.
3. Freeze permitted observation and public chat cutoff for every turn. Bind results to that seat and state version. Accept one optional bounded message with a valid action, order and persist it, and expose it to later players. Treat peer text as untrusted data. Do not create an unbounded conversational loop or transmit private justifications as chat.
4. Add per-player decision/trace attribution, filtering, active status and snapshot fields needed by frontend, preserving the v1 trace root schema through metadata. Keep actual submitted prompts/tool results and concise outputs inspectable locally. Do not share those private traces with other seats. Explicitly record invalid output, timeouts, caps and fallbacks.
5. Add bounded per-seat and total-table calls, deadlines, output tokens and message limits. All attempts count. No silent unlimited retries, no fallback disguised as LLM play, and no fabricated cost. Retain the existing offline heuristic and native comparison modes.
6. Provide a small benchmark manifest, validation/dry-run command and bounded runner using this same player/game path. Include presets from the contract, seat rotation, memory reset, prompt/model/harness versions, limits, held-out configuration and outcome/failure/usage records. Extend the existing evaluation path only as needed and preserve its tests. This authorizes relevant backend/evaluation integration in this checkout; avoid duplicating the game engine.

Frontend is implementing `feat/terminal-ui` against this contract in its own checkout. Own backend modules, tests, additive contracts, benchmark configuration/runner and backend delivery documentation. Do not edit `apps/web` or the canonical decision log. Write contract readiness and any necessary compatibility refinement to `docs/llm-table-backend.md` early so integration can relay it. Do not claim the future tool loop, solver, hero harness or superior performance is delivered by this environment milestone.

## Verification and delivery

Use deterministic mocked provider responses to run complete four-seat games through production worker/policy paths. Test six-seat baseline regressions, nonzero hero seats, elimination/heads-up/side pots, chip conservation, independent tables/seats/memory, chat ordering and replay cutoffs, stale/illegal responses, injection-like public messages, malformed responses, timeouts, budget exhaustion and attribution. Audit actual submitted prompts and local/exported traces for other-seat cards/profiles, seeds and spectator leaks. Test the two instruction profiles differ only as intended and model IDs route per seat.

Run meaningful backend suites plus native regression checks needed by changed behavior. Run a small deterministic mock benchmark across presets and rotations, including failures, and save an example report labeled as mocked. Test repeated seeded mock runs where deterministic behavior is expected. Mock results establish engineering behavior only; they cannot establish real-model strategy or chat effects.

The integration review owns running services on 8012/5175. Do not stop them. Use free alternative ports such as API 8015 if needed, a separate worktree-local database and your own dependencies. Paid provider calls, remote pushes and deployment are outside this assignment. Existing provider configuration can be implemented and mocked without credentials.

Make coherent local commits and report the branch/commit, checks, mock versus live evidence, contract readiness and remaining limits in `docs/llm-table-backend.md`. Continue until the environment and benchmark setup are reviewable, not just acknowledged. The richer hero strategy and solver are a subsequent implementation slice using this interface.
