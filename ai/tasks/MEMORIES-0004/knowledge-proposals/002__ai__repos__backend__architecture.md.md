# Proposed update

Target: `ai/repos/backend/architecture.md`

Document the 'one shared reference-taxonomy table discriminated by type' pattern (libs/modules/catalog) as an established alternative to per-concept tables when several catalogs share an identical shape, and record the facet-count semantics convention (self-exclusion per facet, descendant-inclusive counts via recursive CTE for hierarchical types, plus response-derived price/preparation/rating option groups) as a reusable pattern for future faceted-search modules.


