# DOM-to-React mapping

| Prototype pattern | React/Next.js replacement |
|---|---|
| `querySelector` plus class toggling | State and conditional class/markup |
| Inline `onclick`/listener registration | JSX event handler |
| `innerHTML` rendering | JSX and typed data mapping |
| Manual page navigation | Next.js `Link` or router |
| Global mutable object | Component state, reducer or scoped context |
| Browser storage at module load | Client-only effect with SSR guard |
| Imperative focus | Ref after state transition, only when focus management requires it |

Use effects only to synchronize with an external system. Derive display values during render and keep business rules outside mock fixtures.
