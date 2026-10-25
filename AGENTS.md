# Project conventions

- Keep UI copy minimal and functional. Use direct labels such as "Live tables" and "Agent decision". Do not add slogans, motivational taglines, decorative introductory copy, or claims about intelligence.
- Do not use em dashes or en dashes in copy or documentation.
- Preserve native scrolling while hiding visible scrollbars. Respect reduced-motion preferences.
- Keep opponent cards and simulator profiles out of agent observations and model traces.
- Label heuristic estimates and unsolved strategy assumptions accurately. Do not describe baseline play as GTO.
- Each table owns its state in an independent worker process. Validate every action against its observed state version.
- Provider credentials and database connections belong on the backend.
