# LLM table integration review

Reviewed on 2026-10-25 (Asia/Singapore). The six-seat environment and terminal UI are integrated and verified locally. This completes the environment/UI slice of Stage 2B, not the richer hero strategy harness or solver.

## Delivered baseline

- Six seats, with five neutral LLM opponents and manual hero actions/messages by default when OpenRouter is configured. Hero takeover enables six automated seats. Opponent settings remain fixed while their actions respond to the game.
- Isolated per-seat contexts, public chat, bounded calls/output/history, legal-action and version checks, private execution traces, and persisted replay. Manual waiting never invokes the hero model or chooses an automatic action.
- A dark/light terminal workspace with the board and players beside table talk on desktop. Manual controls, decisions, traces, history and standings follow below. Narrow layouts stack these areas.
- A benchmark runner sharing the production game/player path, with explicit mock mode, configuration versions, seat rotation, held-out seeds and failure/usage records. Manual or mixed-control games are excluded from autonomous comparisons.
- Preserved PokerTH/legacy modes and the `baseline/stage-2a` tag.

## Integration

Backend delivery `e6db68c` was merged through `0cbdb8a`; frontend delivery `404ae2c` through `6ec8305`. The only merge conflict was the shared contract's implementation-status sentence. Revision 20 requirements were preserved.

Integration fix `4c88015` aligns normalized LLM usage with the legacy decision display, reads the server/table chat limit, rejects invalid manual messages before submitting an action, labels a free action Check, and uses the backend's neutral six-seat manual preset when available. Old backends retain PokerTH creation without additive LLM fields. Six additional frontend tests cover these boundaries.

## Independently verified

- Full backend suite: **160 passed, 1 skipped** in 50.32 seconds. The skip is optional PostgreSQL integration. Provider calls were mocked; native PokerTH and spawned-worker coverage executed.
- Final frontend suite: **48 passed**. TypeScript and the production build passed. Synthetic workspace identifiers/model strings are absent from production assets.
- The committed backend report was inspected: **72 completed mock games, 5,382 accepted legal actions**, with conserved chips and no rejected actions. The full 72-game run was not repeated during integration; backend tests and a separate browser exercise were rerun.
- A separate API and web preview used the real application, persistence and production workers with an explicitly mocked HTTP transport. No paid calls were made. A nonzero hero seat (seat 3 in the UI) was used to exercise attribution.
- The browser created six seats from the new default. A manual call plus public message was accepted together while paused, advancing from state 1 to 2. LLM takeover preserved pause, and running the table produced actual per-seat decision records from mocked provider responses. Switching back to Manual stopped at the hero's next turn. The table remains paused at state 28, awaiting a manual action.
- Replay at state 1 showed no future messages and disabled manual actions. Returning to live restored the state-28 turn. Spectator selection of Player 4 showed that seat's permitted input, completed and cancelled traces, and recorded usage. Play view hid opponent cards and private decision panels.
- Both themes were inspected. At the effective desktop width of 1,200 CSS pixels, board and chat are side by side. At 400 CSS pixels, the document had no horizontal overflow and manual action buttons/message entry fit the narrow panel. Temporary browser viewport overrides were reset afterward. The earlier frontend delivery additionally records its 390-pixel checks. Reduced-motion rules were inspected by the frontend; the OS preference was not toggled during integration.

Screenshots: [dark desktop](../qa/llm-integration/dark.png), [light desktop](../qa/llm-integration/light.png), [narrow dark](../qa/llm-integration/narrow-dark.png), [narrow light](../qa/llm-integration/narrow-light.png), [narrow manual controls](../qa/llm-integration/narrow-controls.png). These show real application state with mocked model responses and explicitly labeled mock data.

## Reproduce the offline browser check

The committed `apps/api/tests/llm_preview.py` is a QA bootstrap, never imported by production. It overrides provider credentials with a dummy value and injects `httpx.MockTransport` in every spawned table worker. Run from `apps/api`, using a fresh local database:

```sh
DATABASE_URL=sqlite:///data/llm-preview.sqlite CONTROL_TOKEN= WTR_PUBLIC=false ALLOWED_ORIGINS=http://127.0.0.1:5178,http://localhost:5178 PREVIEW_PORT=8016 PYTHONPATH=. .venv/bin/python tests/llm_preview.py
```

From the repository root:

```sh
VITE_API_URL=http://127.0.0.1:8016 npm run dev -w apps/web -- --port 5178 --strictPort
```

Create a table named clearly as a mock review. Manual actions and takeover use the real API. Model decisions, messages and usage are synthetic; this checks engineering behavior, not poker quality.

## Remaining work

Live OpenRouter compatibility, real-model chat and poker behavior, live LangSmith export and hosted PostgreSQL operation remain unverified. Exact live models and a permitted run budget still need selection. The hero currently uses the neutral baseline player when automated; it has no model-directed LangGraph tool loop, integrated solver or demonstrated competitive advantage. The public evidence/hypothesis tools and stronger hero harness are the next strategy slice.

No remote push or deployment was performed. The existing review services on 8012/5175 were not stopped. The separate integrated preview uses 8016/5178 and a disposable local database.

## Chat height follow-up

Rayner requested that desktop table talk match the board panel's natural height and scroll its messages internally. The chat panel now excludes its message contents from grid row sizing and uses a shrinking middle row. At 1,200 CSS pixels, both panels measured 472.33 pixels high while the 1,445-pixel message list scrolled inside a 396-pixel area. Dark and light themes were checked. At 400 CSS pixels, chat keeps its 260-pixel scroll area below the board, with no horizontal page overflow. The production build passed. See [the updated layout](../qa/llm-integration/chat-height-fixed.png). This follow-up remains on the integration branch for review before another main update.
