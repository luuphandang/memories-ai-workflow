# Component ownership

| Owner | Put here | Do not put here |
|---|---|---|
| `packages/design-system` | CSS tokens, theme scopes, Tailwind preset | React business components, mock data |
| `packages/ui` | Neutral primitives with stable cross-app APIs | Site header, product card, cart summary |
| Application | Brand shell, composed sections, feature components | Duplicate copies of shared primitives |

Promote a component only after at least two consumers share semantics and API, not merely similar markup. Keep composition close to the feature. Test behavior at the owning layer and avoid repeating the same primitive tests in every page.
