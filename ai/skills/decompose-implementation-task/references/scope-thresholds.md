# Scope thresholds

Treat decomposition as mandatory when any condition holds:

- Jira type is `epic` and it has an implementation worktree.
- More than 20 unchecked acceptance items are effective.
- More than one repository or bounded context changes.
- Work combines three or more of database, API, security, background processing and UI.
- A single attempt is unlikely to finish implementation plus validation.

Each slice must be independently reviewable. Keep one concise primary criterion per generated scope section and retain field-level checkboxes under `requirement_details`; do not flatten hundreds of sub-requirements into the handoff. A backend feature slice is incomplete if it declares a port without its adapter/wiring, changes persistence without migration/constraint analysis, or exposes behavior without tests.

Prefer this order when dependencies permit:

1. Contracts and domain invariants.
2. Persistence and migrations.
3. Application use cases and transaction boundaries.
4. DI/module wiring and presentation.
5. Client integration.
6. End-to-end and security verification.
