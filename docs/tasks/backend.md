# Backend observability milestone

Branch: `feat/observability`. Follow `docs/parallel-work.md` and the trace schema without breaking existing consumers.

Replace fixed frontend-stage assumptions with real backend trace data. Instrument the existing LangGraph preparation, model/heuristic selection, response validation, and fallback where actually executed. Use one decision root with accurate parent/child relationships and monotonic durations. Keep same-table state changes sequential and preserve two independent table processes, model deadlines, and action validation.

Persist bounded local traces and expose the authenticated trace routes in the shared contract. Capture in-flight spans where practical, associate active and completed traces with table snapshots, and retain historical traces independently of the current hand. Preserve old session/replay compatibility. Add explicit migration or initialization handling for new tables. Prepare documented PostgreSQL/Supabase configuration and access control without creating cloud resources or requiring secrets.

Connect supported LangSmith tracing and normal trace URLs to these IDs. Instrument actual request messages and model token usage when supplied. Avoid blocking decisions on telemetry export and ensure telemetry failures do not stop play. No secrets, other players' hole cards, simulator profiles, or provider error bodies may leak into traces. Investigate process/queue shutdown and bounded buffering so recording longer sessions does not accumulate unbounded IPC messages.

Test root/child integrity, real timing, parallel overlap, error/fallback traces, no-key operation, authentication, cross-table isolation, storage restart, and private-input filtering. Mock external services. Optional Docker/PostgreSQL verification must be reported accurately if the local environment supports it. Do not modify frontend, strategy, or evaluation modules. Do not turn this milestone into a strategy rewrite or production deployment. Commit your code, tests, and backend integration notes.
