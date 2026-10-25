# Terminal UI delivery

Branch: `feat/terminal-ui`, based on reviewed local main `f73fbe1`. Shared project context revision 18 was read at the start; revision 19 and the live revised task/contract were read during implementation. Free play is the only initial instruction profile. The canonical decision log and backend/runtime files are unchanged.

## Implementation

The compact workspace contains the poker table, selected-player decision, public chat, public action history and standings. A token-based dark/light palette covers the workspace, cards, table, dialogs and recorded trace explorer. Theme selection is saved locally and otherwise follows the operating system; a small pre-paint script prevents the initial palette from flashing. Native scrolling, keyboard controls, reduced motion and progressive one-time panel reveals are preserved.

Existing six-player PokerTH tables, session controls, creation, archive, replay and trace endpoints remain the live path. New capability flags are treated as unavailable when absent. LLM seat setup supports four or six players, a hero seat, model defaults/overrides, free-play profiles, baseline harnesses and chat access. No unsupported harness or tactical profile is offered. New LLM fields are omitted from baseline creation requests.

Public messages use the snapshot's chat sequence and game version, so a replay cannot display future messages. Selected decisions must match their player and state version. Legacy unattributed records belong to seat 0. New trace-list requests use the player filter and reject mismatched detail metadata. PokerTH opponents do not gain fabricated LLM records. Private records are never used as public chat.

An explicit `/dev/workspace` preview shows four synthetic seats and public claims, with local synthetic trace views and configuration controls. It makes no provider calls or gameplay requests. Production builds eliminate this preview and the earlier `/dev/traces` fixture entry.

## Verification in progress

Initial implementation checks passed: TypeScript, production build and 28 frontend tests. These include theme persistence/system changes, unavailable capability handling, neutral per-seat configuration, player attribution, chat cutoffs and trace filtering, alongside existing trace regressions.

The native PokerTH core built from the vendored source. The reviewed API runs at port 8013 against this worktree's `data/terminal-ui-qa.sqlite`, with external tracing disabled and no OpenRouter key. Frontend preview uses 5176. Desktop/narrow checks and final screenshots are being completed. Integration services on 8012/5175 are untouched.

## Integration needs

Consume the additive LLM table contract from the backend delivery. Real per-seat LLM play/chat and hosted provider operation are not established by a synthetic UI preview or mocked tests. Model IDs remain user-entered or backend-provided. No paid calls, remote pushes, deployment or main merge are authorized or performed by this delivery.
