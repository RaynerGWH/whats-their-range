# Shared context access

All local project worktrees use one live project brief maintained by the integration chat:

- [Project brief and decision log](/Users/rayner/Documents/ChatGPT/whats-their-range/docs/project-context.md)
- [Detailed agent direction](/Users/rayner/Documents/ChatGPT/whats-their-range/docs/agent-direction.md)

Read those files directly before starting or resuming work and before making scope or interface decisions. They contain the current accepted direction, proposals, implementation status and unresolved decisions. The original workstream briefs remain the record of the first milestone.

Git worktrees have separate file contents. Editing a document on one branch does not update another branch. These links deliberately point to the same integration checkout so decisions are read live without copying the brief or merging code. Editing the brief does not send a message to a chat or restart it; an already-running agent needs to reread it to observe updates.

This absolute path is a local coordination convention. On another machine, use the repository's `docs/project-context.md` and `docs/agent-direction.md` from an up-to-date shared documentation revision, and establish a new common path for local worktrees. If the live source is unavailable, state the revision actually available and do not claim that an old task brief is current.

The integration chat maintains the canonical brief. Workstreams record local progress and proposals in their own documentation. Include the context revision used in milestone handoffs. Direct instructions from Rayner take precedence over recorded documentation.
