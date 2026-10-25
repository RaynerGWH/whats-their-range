# Frontend trace explorer milestone

Branch: `feat/trace-explorer`. Follow `docs/parallel-work.md` and `contracts/trace-v1.schema.json`.

Build a usable trace explorer in the existing React app. Navigate from a table/hand/decision to its trace. Show an expandable run tree, overlapping timing bars, and selected-span inputs, outputs, status, errors, model, usage and cost where recorded. Show total elapsed time separately from child durations. Include an Open in LangSmith link only when available. Keep UI copy practical and minimal, with no slogans or decorative AI language.

Use authenticated trace endpoints through the existing API configuration. Support old decisions with no trace, disabled external tracing, loading, empty, running, error and reconnect states. Preserve table controls, the card-visibility boundary, independent sessions, and replay. Do not mislabel unavailable metrics as zero or display completed stages that were not recorded.

Backend endpoints are being implemented on another branch. Use the clearly labeled development fixture to build and verify the UI, through an explicit development-only harness or fixture preview. Never silently substitute mock traces in normal live sessions when requests fail. Do not place fixtures in the production gameplay path. The original backend can remain unchanged in your checkout.

Validate TypeScript/build and inspect the UI using the supported browser tools at desktop and narrow widths. Add focused tests only where they verify nontrivial behaviour such as run-tree construction or timing layout. Keep reduced motion and native scrolling. Use worktree ports 8013/5176 if needed; do not stop the existing preview. Commit changes and report screenshots, checks, and backend integration requirements. No public deployment.
