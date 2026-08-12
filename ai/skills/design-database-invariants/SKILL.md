---
name: design-database-invariants
description: Design and verify complete database invariant and mutation coverage for constraints, hierarchies, aggregates, transactions, seeds, filters, and derived queries. Use for TypeORM persistence changes, migrations, recursive relationships, aggregate replacement writes, taxonomy status rules, facet computation, or fixes to a database integrity defect.
---

# Design database invariants

1. Build an invariant matrix from [mutation-matrix.md](references/mutation-matrix.md) before editing persistence code.
2. Cover every write path: insert, update each participating column, delete, parent/child mutation, retry, concurrent write, and partial failure.
3. Enforce durable integrity in the database when invalid state must never exist; keep domain checks for early feedback.
4. Make recursive queries cycle-safe and apply status/type predicates at roots, edges, descendants, filters, response mapping, and facet counting.
5. Test every sibling implementation that uses the same pattern; do not fix only the method named by a review finding.
6. Add real-database tests for every matrix row and run `scripts/check_invariant_matrix.py <matrix.json>`.
7. When a migration changes, apply the migration skill's complete empty-database lifecycle again.
