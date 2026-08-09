# Memories Frontend Source Map

| Khái niệm | Đường dẫn | Ghi chú |
|---|---|---|
| App bootstrap | `apps/{admin-web,public-web}/app/layout.tsx` + `app/providers.tsx` | `providers.tsx` wrap `QueryProvider`/`AuthProvider`/Toast |
| Route/page | `apps/admin-web/app/(dashboard)/*/page.tsx`, `apps/public-web/app/{(auth),(account),(cards),(commerce),(marketing)}/**/page.tsx` | Đa số là stub tĩnh — xem `known-issues.md` |
| Shared components | `packages/ui/src/components/{button,card,input,label,toast}.tsx` | Chỉ 5 component, viết tay theo phong cách shadcn/ui |
| Feature modules | `apps/admin-web/components/{auth-guard,dashboard-nav}.tsx` | `public-web/components/` hiện trống (0 file) |
| API client | `packages/api-client/src/{http-client,media-client,errors}.ts`, `packages/api-client/src/generated/schema.d.ts` | `schema.d.ts` sinh tự động từ `openapi.json` của backend |
| State/store | `packages/auth/src/{auth-provider,token-store,token-provider}.tsx`, `packages/query/src/{query-client,query-provider,query-key-factory}.ts` | Không có zustand/redux/jotai |
| Tests | `apps/{admin-web,public-web}/test/*.spec.tsx`, `packages/*/test/*.spec.ts` | Vitest + Testing Library, chưa có E2E |
