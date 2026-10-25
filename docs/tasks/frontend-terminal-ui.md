# Frontend: terminal table and light theme

Assigned by Rayner on 2026-10-25 to the existing **Frontend: trace explorer** chat. Updated for shared-context revision 20. Start a new `feat/terminal-ui` branch from the latest reviewed local `main` in the existing frontend checkout, preserving the old delivery branch. If already working from an earlier revision, apply the current corrections without discarding ongoing work. Read the live shared brief before editing.

## Outcome

Rework the spectator app around Rayner's supplied terminal/pixel-inspired reference, with equally usable dark and light themes. Preserve the working Stage 2A table, controls, trace explorer and replay. Prepare the UI for configurable LLM seats and public table talk through the [shared interface](../../contracts/llm-table-v1.md), implemented concurrently by backend.

The [cropped reference](../design/terminal-reference.png) is a design reference supplied by Rayner from a LinkedIn video, not an application asset or a claim about our capabilities. Borrow its thin bordered panes, compact typography, crisp cards, green table and consistent player colours. Do not copy its branding, claims, author content or arbitrary metrics.

## Design and behavior

- Use charcoal surfaces, restrained amber/cyan/green accents, a crisp table silhouette and readable monospaced text. Pixel character can come from cards, borders and small labels; keep body text and raw traces comfortably readable. Avoid novelty CRT effects, blur, flashing and heavy ornamentation.
- Build a light theme intentionally using pale neutral surfaces, dark ink and contrasting accents, including the table, cards, dialogs, menus, charts and trace tree. Centralize theme tokens. Add an accessible theme switch, remember explicit selection, and use system preference when no choice is saved. Avoid a bright/dark flash at startup where practical.
- Main workspace: poker table and player seats; public table talk; selected-player decision with expandable tools/raw trace; action history and standings. Keep the table and current action prominent. At narrow widths, stack panels or use clear tabs without losing controls or information.
- Use consistent seat colours plus text/name labels, visible keyboard focus, readable contrast in both themes and ordinary accessible controls. Hide scrollbars while preserving native wheel, trackpad, touch and keyboard scrolling. Reveal sections subtly once, respect reduced motion and never animate every incoming event.
- Maintain run/pause/step/speed, independent sessions, creation, archive, card visibility, hand navigation, reconnect/error/loading states and raw trace access. Keep real six-player PokerTH tables usable. The new LLM table also defaults to six seats.
- Add a seat configuration surface aligned to the shared contract: model ID, instruction profile, harness and chat access. Explain `free_play` briefly as rules/objective with no suggested strategy. It is the only initial supported profile; remove the earlier `bluff_directed` option and fixture personality. Do not label ordinary players as habitual bluffers or add a bluff-rate control. Keep future profile choices extensible. Model IDs are user-entered or backend-provided, never a fabricated supported-model list. Do not offer unavailable harnesses as working choices.
- Default the interactive hero to manual control with five LLM opponents using one reusable neutral preset. Present a clear Manual/LLM control for the hero, making full automation six LLM seats. On a manual turn show the hero's own cards, current legal action buttons/sizes and an optional message field. Submit the exact server legal key with its version/token, prevent accidental duplicate submissions, and handle stale/rejected actions without pretending they succeeded. No auto-action timer or auto-send. The user can choose silence.
- Make takeover/pause/waiting states explicit and honor backend capability flags. Keep opponent cards and private traces out of the manual play view by default; operator spectator inspection is a separate choice. Human actions show their source without invented model traces. Preserve the five opponents' saved settings when changing hero control. New controls stay unavailable against old backends.
- Public chat and private spectator decision records are separate views. A chat statement about a hand is a claim, not a verified card reveal. Seat selection must fetch the correct player's trace. Do not imply PokerTH has LLM traces.
- Render real latency, source, model, usage and recorded estimates with their assumptions. Do not invent confidence bars, solver values, bluff labels or completed tool stages just to resemble the screenshot.

## Parallel implementation

Own `apps/web`, frontend tests/dependencies and your delivery/QA documentation. Backend owns API/game/provider work and the shared runtime contract. Consume additive capabilities defensively. Existing backends omit the flags and must remain usable. New LLM creation/chat/seat-trace controls remain unavailable until supported, with short functional copy.

An explicit development-only fixture may preview six seats, manual hero actions, LLM takeover, chat and per-seat traces. Label it as a fixture and exclude it from production gameplay and production assets. Never silently replace failed live requests with invented messages or traces. Prefer real API data for existing capabilities. Do not change a live table into a fabricated game.

Use frontend ports 8013/5176 and a worktree-local database/dependencies. The integration review currently uses 8012/5175; do not stop or alter it. Provider calls and cloud connections are unnecessary for this assignment. Do not merge or push; deliver coherent local commits for integration review.

## Verification and delivery

Run the web tests, TypeScript check and production build. Add focused behavior checks for theme persistence, capability handling, correct player/chat/trace selection, manual action submission and control switching where implemented. Inspect desktop and narrow screens in both themes with the supported browser tools, including real baseline play, replay, trace/raw data and unavailable new-feature states. Check reduced motion and keyboard usability. Save screenshots and document actual tests, fixture coverage and remaining backend integration needs.

Keep progress in `docs/frontend-terminal-ui.md`, including the shared-context revision, implementation status and final commit. Continue implementation through a reviewable milestone; an acknowledgement or plan alone is not the requested delivery.
