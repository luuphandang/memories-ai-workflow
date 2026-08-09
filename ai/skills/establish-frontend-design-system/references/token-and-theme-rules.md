# Token and theme rules

## Token layers

1. Keep raw palette values stable and brand-named only when designers need direct palette access.
2. Map components to semantic tokens such as background, surface, foreground, primary, muted, border, focus, success, warning and destructive.
3. Add component tokens only when a value represents a durable component contract rather than a one-page exception.

## Theme scope

Use `:root` only for defaults shared by every app. Put public-only branding under a layout class or data attribute such as `.theme-public`. Ensure portals inherit or receive the same scope. Verify shared UI in every consuming app after changing a default token.

## Typography and motion

Load fonts once through the framework font mechanism or a stable local asset. Define heading, body and optional accent families with fallbacks. Name spacing, radius, shadow and motion values by intent; avoid creating a token for every literal found in a prototype.
