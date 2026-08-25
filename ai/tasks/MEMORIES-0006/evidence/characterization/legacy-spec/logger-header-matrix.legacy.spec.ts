// [LEGACY origin/master@c8ca980672459e9eccbb03396a9c246448d1ead6]
// MEMORIES-0006 fix-request-review-002 finding #3 — reproducible characterization.
//
// Boots the frozen, byte-identical `LoggerModule` (nestjs-pino wiring, genReqId, customProps) and
// `CorrelationMiddleware` fixtures through a real Nest application (not a hand-rolled Express
// double), mirroring the two describe blocks in the migrated
// `libs/platform/observability/test/logger.module.spec.ts` ("no CLS active" / "wired app") so the
// same HTTP header matrix can be compared before/after this migration.
import {
  Controller,
  Get,
  INestApplication,
  MiddlewareConsumer,
  Module,
  NestModule,
} from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { Test, TestingModule } from '@nestjs/testing';
import request from 'supertest';

import { CorrelationContext } from '../legacy-fixtures/correlation-context';
import { CorrelationMiddleware } from '../legacy-fixtures/correlation.middleware';
import { LoggerModule } from '../legacy-fixtures/logger.module';

const fakeConfigService: Pick<ConfigService, 'getOrThrow'> = {
  getOrThrow: <T>(key: string): T => {
    if (key === 'observability') {
      return { logLevel: 'info', logFormat: 'json' } as unknown as T;
    }
    if (key === 'app') {
      return { name: 'legacy-characterization', env: 'test' } as unknown as T;
    }
    throw new Error(`unexpected config key requested in legacy characterization test: ${key}`);
  },
};

@Controller('probe')
class ProbeController {
  @Get()
  get(): { requestId: string | undefined; correlationId: string | undefined } {
    return {
      requestId: CorrelationContext.requestId(),
      correlationId: CorrelationContext.correlationId(),
    };
  }
}

function findRequestCompletedLine(chunks: string[]): Record<string, unknown> {
  const line = chunks
    .join('')
    .split('\n')
    .filter(Boolean)
    .map((raw) => JSON.parse(raw) as Record<string, unknown>)
    .find((entry) => entry.msg === 'request completed');
  if (!line) {
    throw new Error('no "request completed" log line was captured');
  }
  return line;
}

describe('[LEGACY] LoggerModule genReqId with no CorrelationMiddleware mounted (no active ALS context)', () => {
  let app: INestApplication;
  let writeSpy: jest.SpyInstance;
  let chunks: string[] = [];

  beforeAll(async () => {
    writeSpy = jest.spyOn(process.stdout, 'write').mockImplementation((chunk: unknown) => {
      chunks.push(typeof chunk === 'string' ? chunk : String(chunk));
      return true;
    });

    const moduleRef: TestingModule = await Test.createTestingModule({
      imports: [ConfigModule.forRoot({ isGlobal: true, ignoreEnvFile: true }), LoggerModule.register()],
      controllers: [ProbeController],
    })
      .overrideProvider(ConfigService)
      .useValue(fakeConfigService)
      .compile();

    app = moduleRef.createNestApplication();
    await app.init();
  });

  afterAll(async () => {
    await app.close();
    writeSpy.mockRestore();
  });

  beforeEach(() => {
    chunks = [];
  });

  it('LEGACY BUG, fixed by MEMORIES-0006 fix-request-review-002 finding #2: discards an incoming x-request-id header because genReqId never reads its own `req` argument', async () => {
    const response = await request(app.getHttpServer())
      .get('/probe')
      .set('x-request-id', 'incoming-outside-als')
      .expect(200);

    // no ambient ALS context was ever active for genReqId()/customProps() to read from
    expect(response.body.requestId).toBeUndefined();

    const entry = findRequestCompletedLine(chunks);
    const loggedId = (entry.req as { id?: string } | undefined)?.id;
    expect(loggedId).toBeDefined();
    // This is the characterized defect: the header is silently replaced by a random id. The
    // migrated implementation (`resolveRequestId` in the current `correlation-context.ts`) fixes
    // this — see the equivalent, now-passing case in
    // `libs/platform/observability/test/logger.module.spec.ts`.
    expect(loggedId).not.toBe('incoming-outside-als');
  });
});

@Module({})
class LegacyRootModule implements NestModule {
  static register() {
    return {
      module: LegacyRootModule,
      imports: [ConfigModule.forRoot({ isGlobal: true, ignoreEnvFile: true }), LoggerModule.register()],
      controllers: [ProbeController],
    };
  }

  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(CorrelationMiddleware).forRoutes('*');
  }
}

describe('[LEGACY] LoggerModule + CorrelationMiddleware wired (mirrors apps/api import order)', () => {
  let app: INestApplication;
  let writeSpy: jest.SpyInstance;
  let chunks: string[] = [];

  beforeAll(async () => {
    writeSpy = jest.spyOn(process.stdout, 'write').mockImplementation((chunk: unknown) => {
      chunks.push(typeof chunk === 'string' ? chunk : String(chunk));
      return true;
    });

    const moduleRef: TestingModule = await Test.createTestingModule({
      imports: [LegacyRootModule.register()],
    })
      .overrideProvider(ConfigService)
      .useValue(fakeConfigService)
      .compile();

    app = moduleRef.createNestApplication();
    await app.init();
  });

  afterAll(async () => {
    await app.close();
    writeSpy.mockRestore();
  });

  beforeEach(() => {
    chunks = [];
  });

  it.each([
    {
      name: 'both headers present',
      headers: { 'x-request-id': 'both-req', 'x-correlation-id': 'both-corr' },
      expectedCorrelationId: 'both-corr',
    },
    {
      name: 'request id only',
      headers: { 'x-request-id': 'reqonly-req' },
      expectedCorrelationId: 'reqonly-req',
    },
    {
      name: 'correlation id only',
      headers: { 'x-correlation-id': 'corronly-corr' },
      expectedCorrelationId: 'corronly-corr',
    },
    {
      name: 'neither header',
      headers: {},
      expectedCorrelationId: undefined,
    },
  ])('$name: response headers and logged id agree with the controller-observed id', async ({ headers, expectedCorrelationId }) => {
    let req = request(app.getHttpServer()).get('/probe');
    for (const [name, value] of Object.entries(headers)) {
      req = req.set(name, value);
    }
    const response = await req.expect(200);

    const resolvedRequestId = response.body.requestId as string;
    expect(resolvedRequestId).toEqual(expect.any(String));
    if (headers['x-request-id']) {
      expect(resolvedRequestId).toBe(headers['x-request-id']);
    }
    expect(response.body.correlationId).toBe(expectedCorrelationId ?? resolvedRequestId);
    expect(response.headers['x-request-id']).toBe(resolvedRequestId);
    expect(response.headers['x-correlation-id']).toBe(expectedCorrelationId ?? resolvedRequestId);

    const entry = findRequestCompletedLine(chunks);
    const loggedReqId = (entry.req as { id?: string } | undefined)?.id;
    // In the "wired" configuration, CorrelationMiddleware (registered by the same module that
    // imports LoggerModule) happens to seed ALS before pino-http's genReqId runs, so legacy and
    // migrated behavior agree here — the divergence this migration's fix targets is specific to
    // the "logger runs before anything seeds the context" case exercised above.
    expect(loggedReqId).toBe(resolvedRequestId);
  });
});
