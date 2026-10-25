# Project conventions

- Keep UI copy minimal and functional. Use direct labels such as "Live tables" and "Agent decision". Do not add slogans, motivational taglines, decorative introductory copy, or claims about intelligence.
- Do not use em dashes or en dashes in copy or documentation.
- Preserve native scrolling while hiding visible scrollbars. Respect reduced-motion preferences.
- Keep opponent cards and simulator profiles out of agent observations and model traces.
- Label heuristic estimates and unsolved strategy assumptions accurately. Do not describe baseline play as GTO.
- Each table owns its state in an independent worker process. Validate every action against its observed state version.
- Provider credentials and database connections belong on the backend.

## Shared project context

- Before starting or resuming work, follow [shared context access](docs/shared-context.md) and read the live project brief and agent direction. Recheck them before scope or interface decisions.
- Treat accepted decisions, proposals and implemented behavior separately. First-milestone task briefs do not describe the complete target agent.
- Keep progress and proposals in the owning workstream's documentation. The integration chat maintains the canonical decision log. Include the shared-context revision used in milestone handoffs.
- New worktrees must receive `docs/shared-context.md` and these reading instructions. Do not assume Git worktrees automatically share document updates.
