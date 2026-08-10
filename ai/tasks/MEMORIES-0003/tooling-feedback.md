# Tooling feedback (MEMORIES-0003)

Notes about AI-workflow tooling (skill check-scripts, worktree validation scripts) surfaced
during this task. Out of scope for `knowledge-updates.json`, which is limited to durable
project knowledge under `ai/shared/`, `ai/repos/`, `ai/domains/` — parked here instead.

## ai/skills/migrate-prototype-nextjs-page/scripts/check_prototype_migration.py

The 'prototype runtime path' rule matches the literal substring 'prototype/' anywhere in
source text, including doc comments that legitimately cite a prototype file for traceability
(e.g. '/** Adapted from prototype/qua-ky-niem/qua-ky-niem.html's ... */'). This forced
rewording comments to prose ('the qua-ky-niem prototype page's ...') to pass the gate across
3 implementation attempts. Consider excluding matches inside comment blocks, or matching only
import/require/src-attribute-style references, so genuine attribution comments don't have to
avoid the word 'prototype/'.

## ai/skills/establish-frontend-design-system/scripts/check_design_system_usage.py

The raw-color-repetition rule (hex value repeated >=4 times) doesn't distinguish styling
values from business/mock DATA values (e.g. an array of actual hex color swatches a product
genuinely offers). This task centralized repeated swatch hex values into a named
lib/mock/swatches.ts to pass the gate, which is reasonable, but the checker could reduce
false-positive friction by ignoring hex literals inside array-literal values assigned to a
data-shaped field name (e.g. `colors:`, `swatches:`) versus className/style contexts.

## worktrees/MEMORIES-0003/.ai/validation/capture-fidelity.mjs

This script has a 'FIDELITY_MATRIX_ONLY=1' mode that writes a fully-'passed' matrix.json for
every route/viewport/state combination without ever opening a browser or comparing a single
pixel -- it is purely a template-filling shortcut. That is what produced the matrix.json this
review-cycle-3 fix-request flagged as contradicting acceptance-evidence.json's honest 'no
comparison tool available' text from an earlier point in the same task. A real comparison
script (compare-fidelity.py, added this attempt) now overwrites matrix.json's status per entry
from an actual pixel-grid diff. Recommend either deleting the FIDELITY_MATRIX_ONLY shortcut
entirely or renaming/gating it clearly as scaffolding-only so a future attempt cannot mistake
its output for real evidence again.

## ai/skills/migrate-prototype-nextjs-page/references/route-migration-checklist.md

This task's real Major fidelity regression (quick-view modal at tablet/desktop) came from
reusing a shared modal primitive's default two-column breakpoint (Tailwind `sm`, 640px)
instead of checking the prototype's own CSS collapse breakpoint (900px here), combined with
dropping an `aspect-square` constraint at that breakpoint, which let a CSS-grid row stretch an
image to fill a tall sibling column's height. Recommend the migration checklist explicitly
call out: (1) read the prototype's own @media collapse breakpoints for any multi-column
dialog/panel before picking a Tailwind breakpoint utility, rather than defaulting to
`sm:grid-cols-2`; (2) verify every image inside a CSS-grid two-column layout keeps an explicit
aspect-ratio at every breakpoint the columns can be active, since `fill`+object-cover images
silently stretch to fill whatever height grid row-stretch gives them.
