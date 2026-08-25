import { CorrelationContext } from '@memories/platform/observability';
import { Injectable, NestMiddleware } from '@nestjs/common';
import { NextFunction, Request, Response } from 'express';

import { createEmptyRequestContextStore, RequestContext } from './request-context';

/**
 * Seeds `RequestContext` for every request BEFORE any guard runs (§14), reusing the request/
 * correlation IDs `CorrelationMiddleware` (platform/observability) already established earlier in
 * the middleware chain — not generating a second, disagreeing pair of IDs for the same request.
 * `accountId`/`userProfileId`/`sessionId`/`portal`/`authProvider`/`roles`/`permissions` start
 * empty and are filled in later by `JwtAuthGuard`/`PermissionsGuard` once the caller is resolved.
 */
@Injectable()
export class RequestContextMiddleware implements NestMiddleware {
  constructor(private readonly requestContext: RequestContext) {}

  use(req: Request, res: Response, next: NextFunction): void {
    const correlation = CorrelationContext.current();
    const store = createEmptyRequestContextStore({
      requestId: correlation?.requestId,
      correlationId: correlation?.correlationId,
      ipAddress: req.ip ?? null,
      userAgent: req.header('user-agent') ?? null,
    });

    this.requestContext.run(store, () => next());
  }
}
