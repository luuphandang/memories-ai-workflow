import { Injectable, NestMiddleware } from '@nestjs/common';
import { NextFunction, Request, Response } from 'express';

import { CorrelationContext } from './correlation-context';

const REQUEST_ID_HEADER = 'x-request-id';
const CORRELATION_ID_HEADER = 'x-correlation-id';

@Injectable()
export class CorrelationMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction): void {
    const requestId = (req.header(REQUEST_ID_HEADER) as string) || crypto.randomUUID();
    const correlationId = (req.header(CORRELATION_ID_HEADER) as string) || requestId;

    res.setHeader(REQUEST_ID_HEADER, requestId);
    res.setHeader(CORRELATION_ID_HEADER, correlationId);

    CorrelationContext.run({ requestId, correlationId }, () => next());
  }
}
