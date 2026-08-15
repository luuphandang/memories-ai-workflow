# Proposed update

Target: `ai/repos/backend/conventions.md`

Document the seed-convergence convention: an idempotent find-by-code-or-create seed use case must reconcile (update) an already-existing row's mutable fields onto the canonical seed definition, not just skip it, or a rerun only guarantees row *presence*, not row *content* — a manually-altered or stale-from-an-earlier-code-change row is never repaired. See `CatalogTerm.reconcile()` (libs/modules/catalog/src/domain/catalog-term/catalog-term.ts) + `SeedCatalogTermsUseCase.findOrCreate`'s existing-row branch for the reference implementation: re-validate the same invariants `create()` checks (duplicated, not extracted into a shared validator, matching the existing `UserProfile.update`/`Account.activate` convention), never reconcile the row's stable lookup identity fields (here: `code`/`catalogType`).


