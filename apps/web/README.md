# Frontend trace explorer

The Trace tab opens a full-width explorer for the selected table. Use the hand filter, decision buttons, or recorded decision list to select a trace. Selecting a span or its timing bar opens its inputs, outputs, status, model, usage, cost, error and identifiers. Expand buttons support native keyboard interaction.

Only recorded spans appear. Parent IDs determine nesting; monotonic offsets determine overlap. Total elapsed time is separate from child durations. Missing measurements display as `Not recorded`; running spans with unknown duration show a start marker. Optional HTTPS LangSmith links are limited to `smith.langchain.com` and its regional subdomains.

## Development preview

From this checkout's root:

```sh
npm ci
VITE_API_URL=http://127.0.0.1:8013 npm run dev -w apps/web -- --port 5176 --strictPort
```

Open [the fixture preview](http://127.0.0.1:5176/dev/traces). It imports `contracts/trace-v1.example.json` only through a development-gated lazy entry. Completed, running, error, cancelled and empty-span scenarios are explicitly synthetic. They make no API or provider calls. The production build removes the preview and fixture payload. Failed requests in normal gameplay never fall back to fixtures.

For gameplay checks, run the original API on port 8013 with `ALLOWED_ORIGINS=http://127.0.0.1:5176,http://localhost:5176` and a worktree-local SQLite database. The baseline API does not implement trace endpoints, so its trace panel correctly reports unavailable endpoints.

## Integration requirements

- Implement the authenticated list and detail endpoints in `docs/parallel-work.md`, returning the unchanged trace v1 contract. The list uses `hand`, `limit=50` and opaque cursors, preserving newest-first order. No contract changes are proposed.
- Populate optional `Decision.trace_id` and `Table.active_trace_id`. Replay decisions without these fields remain valid. The explorer starts with the active trace when present, otherwise the decision trace. Explicit buttons can select a newer decision without replacing an older trace being inspected.
- Use the existing `VITE_API_URL` and Connections access token. All trace requests use the same backend origin and bearer authentication as session controls. No provider credentials enter React.
- A selected running trace polls every two seconds after each response; failures retry every four seconds. Completion stops polling. Table/replay changes, credentials, hand filters and unmounts cancel obsolete requests. Cross-table responses are rejected.
- The list refreshes on opening, filter changes, explicit refresh or live-connection changes. It does not continuously follow new decisions. Use **Decision trace**, **Running trace**, or **Refresh** to inspect newer work. Pagination and historical selection stay under user control.
- The backend must redact trace inputs, outputs and metadata before returning them. The frontend never derives trace data from spectator snapshots or sends spectator cards to any trace endpoint. Server-side trace sanitization and live backend interoperability require integration verification.
- Normal session controls retain server validation messages. Trace endpoint errors do not display raw server/proxy bodies.

## Verification

Checked on 2026-10-25:

- `npm run check`: TypeScript passed.
- `npm run build`: production build passed. Inspected generated assets and confirmed the fixture preview and synthetic payload are absent.
- `npm run test -w apps/web`: 14 tests passed. Coverage includes unordered trees, orphans/cycles, collapsing, overlapping timing, unknown versus zero measurements, safe links, authenticated requests, pagination, stale responses across hand/table changes, reconnects, polling cleanup, selected details and error spans.
- `cd apps/api && .venv/bin/pytest -q`: all 19 existing backend tests passed. Provider calls in that suite are mocked.
- Supported in-app browser: inspected 1440 x 1000 desktop and 390 x 844 narrow viewports. Verified nested selection, collapse, keyboard expansion, running markers, missing cost and error details. Both fixture and live screens had no horizontal page overflow at 390 px.
- Local heuristic gameplay: created a table, stepped, ran, paused, scrubbed replay, returned to live and toggled spectator card visibility. The baseline backend's unavailable trace endpoint showed the explicit error state without synthetic data.
- Reduced motion uses the existing global media override; reveal animation is progressive and native scrolling stays available with hidden scrollbars. Activity autoscrolling also honors reduced motion.

No paid provider calls, cloud resources, deployments or external trace uploads were made. Hosted OpenRouter, LangSmith and PostgreSQL were not verified. Combined frontend/backend trace operation remains an integration check.

## Screenshots

[Desktop details](qa/trace-desktop.jpg), [narrow details](qa/trace-narrow.jpg), [error details](qa/trace-error.jpg), and [legacy backend](qa/trace-legacy.jpg).

## Stage 1 integration

The combined backend implements both trace endpoints. Completed traces without a LangSmith URL now explicitly instruct the user to refresh. **Refresh** requests both the list and selected detail again, including completed traces, and can reveal a delayed export URL. This behavior is covered by a test; completion still stops automatic polling. Local inspection does not depend on LangSmith availability.

Stage 1 browser checks use ports 8012/5175 and a disposable SQLite database. `apps/api/tests/stage1_preview.py` is an optional local QA bootstrap that mocks every provider request, including in spawned workers. It is never imported by the production API. See `docs/stage-1.md` for combined checks and screenshots.
