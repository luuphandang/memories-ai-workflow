# Proposed update

Target: `ai/repos/backend/conventions.md`

Document the CORP/CORS distinction: Helmet's default `Cross-Origin-Resource-Policy: same-origin` only blocks no-cors cross-origin embeds (e.g. <img>/<script>), never fetch()'s default cors-mode requests — never relax it globally to let a cross-origin SPA consume the API; CORS config already governs that. Scope any real crossOriginResourcePolicy override to the specific route, not globally in configureApp.


