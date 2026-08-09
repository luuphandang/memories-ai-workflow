# Severity and review gates

- **Blocker:** route is inaccessible, blank, unsafe, or core workflow cannot be completed.
- **Major:** wrong layout/theme/asset, broken responsive state, missing core interaction, inaccessible keyboard trap, or architecture bypass that makes the migration non-maintainable.
- **Minor:** localized spacing, type scale, copy, focus or edge-state mismatch that does not block the workflow.
- **Note:** improvement without an acceptance failure.

Require evidence for every route and required viewport. Treat an absent required matrix entry as not verified. Accept documented differences only when they improve accessibility/responsiveness without changing the intended hierarchy or brand.
