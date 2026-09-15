import { analyzeDesignSystem } from './design-system';
import { analyzePrototypeMigration } from './prototype-migration';

function main(): void {
  const [, , command, root] = process.argv;
  if (!command || !root) {
    process.stderr.write('usage: cli.js <design-system|prototype-migration> <root-path>\n');
    process.exit(2);
  }

  let result: unknown;
  switch (command) {
    case 'design-system':
      result = analyzeDesignSystem(root);
      break;
    case 'prototype-migration':
      result = analyzePrototypeMigration(root);
      break;
    default:
      process.stderr.write(`unknown command: ${command}\n`);
      process.exit(2);
      return;
  }
  process.stdout.write(JSON.stringify(result));
}

main();
