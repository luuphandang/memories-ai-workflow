# Proposed update

Target: `ai/repos/backend/database-rules.md`

Document two variant-selection SQL conventions from typeorm-product.repository.ts: (1) the LATERAL-join 'cheapest matching variant' pattern (`effectiveVariantLateralSql`) for list/sort and the rating facet's product-existence guard; (2) the bounded-aggregate 'value-bucketed' pattern (`computeBucketFacet`, and `computeRatingFacet` following the same shape) required for price/preparation/rush/rating facets — each computed as a single `COUNT(DISTINCT CASE WHEN <bucket condition> THEN p.id END)` query per bucket, entirely in Postgres, never materializing per-variant or per-product rows in application memory (a single representative/cheapest variant under-counts a product with variants on each side of a bucket boundary, so (1) alone is insufficient for these facets; review-cycle-4 introduced this pattern for price/preparation/rush, review-cycle-13 extended it to rating). Also document the recursive closure-CTE pattern for parent/child facet aggregation, and the DB-level BEFORE INSERT/UPDATE trigger pattern (AddCatalogTermsHierarchyGuard) for cycle-detection invariants a plain self-FK can't express.


