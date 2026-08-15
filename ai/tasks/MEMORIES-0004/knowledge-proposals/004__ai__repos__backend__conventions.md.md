# Proposed update

Target: `ai/repos/backend/conventions.md`

Document a real bug/fix as a required convention: with the global ValidationPipe's `enableImplicitConversion: true`, a DTO boolean/numeric query-param field decorated only with a custom `@Transform` gets silently overridden by class-transformer's implicit primitive-conversion step (e.g. `?flag=false` becomes `true`; a blank numeric string becomes `0`, not `NaN`, silently passing `@Min(0)`) — `@Type(() => Number)`'s conversion runs before any co-located `@Transform` regardless of decorator order. Fix: add `@Type(() => String)` before the custom `@Transform` to pin the implicit-conversion type away from the real target type, so the `@Transform` output is final (see `rush` in list-products.dto.ts; `toTrimmedNumber` for priceMin/priceMax/prepWithinDays/ratingMin). Companion CSV-array rule: `toIdArray`-style helpers must NOT `.filter(Boolean)` after splitting/trimming — a blank/inner-empty segment must survive as an empty string so `@IsUUID`/`@IsIn { each: true }` rejects it instead of being silently dropped.


