import { AppConfig, ObservabilityConfig } from '@memories/platform/configuration';
import { DynamicModule, Module } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { LoggerModule as PinoLoggerModule } from 'nestjs-pino';
import type { ReqId } from 'pino-http';

import { CorrelationContext } from './correlation-context';

/** Fields that must never reach a log line, however deep, per initialize_project.md §13/§15. */
const REDACT_PATHS = [
  'req.headers.authorization',
  'req.headers.cookie',
  'res.headers["set-cookie"]',
  '*.password',
  '*.accessToken',
  '*.refreshToken',
  '*.token',
  '*.cookie',
  '*.presignedUrl',
  '*.cardContent',
  '*.paymentDetails',
];

/** Query-string keys that carry transient OAuth credentials (fix-request-review-010 #1).
 * `pino`'s `redact` option only strips known object paths — it cannot see into `req.url`, which
 * embeds the raw query string as a substring, so `req.query.code`/`req.query.state` alone would
 * still leak both values via `req.url`. This is a request serializer instead, redacting both. */
const SENSITIVE_QUERY_KEYS = [
  'code',
  'state',
  'access_token',
  'token',
  'id_token',
  'client_secret',
];
const CENSOR = '[REDACTED]';

interface SerializedPinoRequest {
  id: ReqId;
  method: string;
  url?: string;
  query?: Record<string, unknown>;
  params?: Record<string, unknown>;
  headers: Record<string, unknown>;
  remoteAddress?: string;
  remotePort?: number;
}

/** Runs after pino-http's default request serializer (`serializers.req` below is wrapped so it
 * always receives the already-serialized object, per pino-http's `wrapRequestSerializer`). */
function redactSensitiveQueryParams(req: SerializedPinoRequest): SerializedPinoRequest {
  const redacted: SerializedPinoRequest = { ...req };

  if (redacted.query && typeof redacted.query === 'object') {
    const query = { ...redacted.query };
    for (const key of SENSITIVE_QUERY_KEYS) {
      if (key in query) {
        query[key] = CENSOR;
      }
    }
    redacted.query = query;
  }

  if (typeof redacted.url === 'string' && redacted.url.includes('?')) {
    const [path, search] = redacted.url.split('?');
    const params = new URLSearchParams(search);
    let changed = false;
    for (const key of SENSITIVE_QUERY_KEYS) {
      if (params.has(key)) {
        params.set(key, CENSOR);
        changed = true;
      }
    }
    redacted.url = changed ? `${path}?${params.toString()}` : redacted.url;
  }

  return redacted;
}

@Module({})
export class LoggerModule {
  static register(): DynamicModule {
    return {
      module: LoggerModule,
      imports: [
        PinoLoggerModule.forRootAsync({
          inject: [ConfigService],
          useFactory: (configService: ConfigService) => {
            const observability = configService.getOrThrow<ObservabilityConfig>('observability');
            const app = configService.getOrThrow<AppConfig>('app');

            // pino-http's Options type does not opt into exactOptionalPropertyTypes, so an
            // explicit `transport: undefined` is a type error — omit the key instead.
            return {
              pinoHttp: {
                level: observability.logLevel,
                redact: { paths: REDACT_PATHS, censor: '[REDACTED]' },
                serializers: { req: redactSensitiveQueryParams },
                genReqId: () => CorrelationContext.requestId() ?? crypto.randomUUID(),
                customProps: () => ({
                  service: app.name,
                  environment: app.env,
                  correlationId: CorrelationContext.correlationId(),
                }),
                ...(observability.logFormat === 'pretty' && {
                  transport: { target: 'pino-pretty' },
                }),
              },
            };
          },
        }),
      ],
      exports: [PinoLoggerModule],
    };
  }
}
