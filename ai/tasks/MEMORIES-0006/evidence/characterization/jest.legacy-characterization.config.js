// MEMORIES-0006 fix-request-review-002 finding #3 — reproducible legacy characterization harness.
//
// Runs the specs in ./legacy-spec against the frozen, byte-identical-to-origin/master@c8ca980
// fixtures in ./legacy-fixtures (fetched verbatim via `git show <base-sha>:<path>`, see
// characterization-baseline.md for the exact provenance of each file). `rootDir` stays the backend
// worktree so ts-jest/node_modules/tsconfig resolution behaves exactly like the real `jest.config.js`;
// only the `@memories/platform/observability` alias is redirected to the legacy fixture shim, and
// only for the one spec (bullmq-publisher-precedence.legacy.spec.ts) that imports the REAL,
// currently-live `bullmq.publisher.ts` unchanged.
//
// Invoke from the backend worktree:
//   npx jest --config ../../../ai/tasks/MEMORIES-0006/evidence/characterization/jest.legacy-characterization.config.js
const path = require('path');

const backendRoot = path.resolve(__dirname, '../../../../../worktrees/MEMORIES-0006/backend');
const fixturesDir = path.join(__dirname, 'legacy-fixtures');

module.exports = {
  moduleFileExtensions: ['js', 'json', 'ts'],
  rootDir: backendRoot,
  roots: [path.join(__dirname, 'legacy-spec')],
  // The fixtures/specs live outside the backend worktree (durable evidence lives under
  // ai/tasks/<TASK-ID>/evidence/, not inside the worktree) — Node's normal upward node_modules
  // walk from those files' actual directory never reaches the worktree's node_modules, so it must
  // be added explicitly here.
  modulePaths: [path.join(backendRoot, 'node_modules')],
  testRegex: '.*\\.legacy\\.spec\\.ts$',
  testPathIgnorePatterns: ['/node_modules/', '/dist/'],
  transform: {
    '^.+\\.(t|j)s$': ['ts-jest', { isolatedModules: true }],
  },
  testEnvironment: 'node',
  moduleNameMapper: {
    '^@memories/platform/observability$': path.join(fixturesDir, 'observability-shim.ts'),
    '^@memories/shared/kernel$': path.join(backendRoot, 'libs/shared/kernel/src/public-api.ts'),
    '^@memories/platform/(.*)$': path.join(backendRoot, 'libs/platform/$1/src/public-api.ts'),
    '^@memories/modules/(.*)$': path.join(backendRoot, 'libs/modules/$1/src/public-api.ts'),
  },
};
