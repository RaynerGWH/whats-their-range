# Terminal UI delivery

Branch: `feat/terminal-ui`, based on reviewed local main `f73fbe1`. Implementation commits: `20d3fd6` (themed workspace) and `61a00c6` (manual hero, six seats and board/chat layout). The final documentation/QA commit is the branch tip following these commits.

Shared project context revisions 18, 19 and 20 were read during implementation, together with the live revised task and LLM interface. Revision 20 governs this delivery. Rayner's subsequent direct request simplifies the main view: board and players beside public chat, with controls, decisions, traces, history and standings below. Canonical context, contracts and backend/runtime files are unchanged.

## Implemented

The main desktop row contains the poker table and public table talk. Supporting panels sit below; narrow screens keep the board and chat first in a single column. Charcoal and pale neutral themes cover the workspace, cards, dialogs, charts and trace explorer. Explicit theme choice persists locally, otherwise the system preference applies. The pre-paint script avoids a theme flash. Monospaced typography, seat colours and thin borders provide the terminal appearance without decorative metrics.

Existing six-player PokerTH tables, run/pause/step/pace controls, independent sessions, creation, archive, replay and trace endpoints remain usable. Missing capability flags mean unavailable. Baseline creation omits the new LLM configuration fields entirely.

LLM creation defaults to six seats and explicitly selects manual hero control. Four seats remain optional. The hero has its own model configuration ready for takeover. A neutral preset supplies the five opponents' model, free-play instructions, baseline harness and chat setting. Operators can edit seat-specific settings and save the resulting opponent configuration in browser storage for reuse. Only `free_play` and the implemented `baseline` harness are offered. Model IDs come from the operator or backend, with final validation owned by the backend. No tactical profile or bluff-frequency control is provided.

The manual panel uses the server's legal keys, observed version and opaque turn token. Action and optional public message share one submission. No action is selected by default, silence is valid, double submission is locked, and stale/network failures require an explicit refresh and new selection. Requests are aborted and selection/message state cleared when the turn changes. Acceptance waits for an authoritative table snapshot. There is no automatic retry or timeout action. Manual/LLM switching submits only the control command, target mode and observed version, preserving opponent settings and pause state.

Play view shows hero cards and does not mount opponent decision or trace views. Spectator inspection is an explicit choice; revealing opponent cards is a further control. Returning to play hides those records and cards. This is a UI separation, not an anti-cheat security boundary against an operator with spectator API access. Human decisions display their actual action and `source: human`, without model reasoning or fabricated tool execution.

Public messages remain separate from private records and are marked as unverified claims. Replay uses the snapshot's chat sequence, hand and state version. Decisions must match their player and state version. Unattributed legacy records belong to seat 0. Trace requests filter by player and reject mismatched returned metadata. PokerTH opponents do not gain invented LLM traces. Missing usage stays unavailable.

`/dev/workspace` is an explicit synthetic six-seat preview for manual actions, optional chat, takeover, configuration and private trace selection. It performs no provider calls or gameplay requests. Both this fixture and `/dev/traces` are excluded from production assets. Live errors never trigger synthetic replacements.

## Verification

- TypeScript: `npm run check` passed.
- Frontend: `npm run test -w apps/web` passed, 42 tests in four files. Coverage includes theme persistence/system changes, capability gates, neutral presets, player attribution, chat cutoffs, trace filtering, exact manual payloads, duplicate locking, explicit stale recovery, cancellation on turn changes, takeover payloads, chat-disabled turns, replay/offline/wrong-seat rejection, human-source display and play-view privacy.
- Production: `npm run build` passed. An additional asset scan confirmed synthetic workspace identifiers, fixture model and preview copy are absent from production JavaScript/HTML.
- Browser: inspected desktop at 1440 pixels and narrow at 390 pixels in dark and light themes. Narrow document width matched the viewport with no horizontal page overflow. Board and chat precede supporting panels. Keyboard focus is visible, Escape closes native dialogs, and keyboard slider navigation reaches the first replay state.
- Motion/scrolling: native overflow remains available and CSS hides scrollbars. One-time IntersectionObserver reveals are progressive enhancements. The reduced-motion media rule disables animations/transitions and restores ordinary scroll behavior. The OS reduced-motion preference was not toggled during this review.
- Real baseline: built the vendored native PokerTH core, then used the reviewed API on port 8013 with worktree-local SQLite, no OpenRouter key and external tracing disabled. Created a six-player table, stepped/ran/paused a hand, inspected its recorded hero trace and permitted raw observation, navigated replay back to state 1, and returned to live state 15. A second table advanced independently to state 3 while the first remained at state 15. Pace and archive controls worked; the archived session remained in the library. Unsupported LLM creation was visibly disabled.
- Synthetic coverage: the six-seat preview submitted an explicitly selected action plus message, then switched Manual to LLM and back. The last human action remained labeled Manual. This verifies UI wiring only, not a backend manual turn or real LLM play.

Screenshots are in `apps/web/qa/terminal`: `desktop-dark.jpg` and `desktop-light.jpg` show the labelled six-seat fixture; `narrow-dark.jpg` and `narrow-light.jpg` show its mobile layout; `baseline-dark.jpg` shows real PokerTH data. Synthetic images are presentation evidence, not performance results.

## Integration needs

The running reviewed Stage 2A backend lacks the new LLM/chat/manual capabilities. End-to-end LLM play, manual token consumption, atomic chat publication, takeover fencing and replayed control changes require integration with the backend delivery. Browser fixtures and mocked tests do not establish those server guarantees or poker strength. The backend remains responsible for configured chat length limits and resolved versioned prompts; the shared contract currently provides no frontend limit field to consume.

Frontend preview uses port 5176. API QA uses port 8013 and `apps/api/data/terminal-ui-qa.sqlite`. Integration services on 8012/5175 were untouched. All commits are local. No provider spend, cloud resource, remote push, deployment or main merge was performed.
