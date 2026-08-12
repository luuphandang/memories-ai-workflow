# Mutation matrix

Record each invariant as JSON with `invariant`, `enforcement`, and non-empty `cases`. Each case requires `operation`, `expected`, and `test`.

For relationships, include valid insert, wrong parent type, flat-type parentage, self-parent, multi-node cycle, child type update, referenced parent type update, delete/restrict behavior, and inactive ancestor/descendant behavior.

For aggregate replacement, include failure before delete, after delete, and during each child/link insert; verify the original aggregate remains intact.

For derived queries, cover boundary values, multiple matching children, self-exclusion, AND across families, inactive data, null data, zero-count options, and bounded database-side aggregation for every sibling facet.
