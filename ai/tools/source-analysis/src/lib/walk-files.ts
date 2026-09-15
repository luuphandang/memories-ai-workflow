import * as fs from 'node:fs';
import * as path from 'node:path';

const SKIP_DIRS = new Set(['node_modules', '.next', 'dist', 'build', 'coverage', '.git']);

/** Same skip-list and extension filter as the Python checkers this replaces. */
export function walkFiles(root: string, extensions: Set<string>): string[] {
  const results: string[] = [];
  const stack: string[] = [root];
  while (stack.length) {
    const current = stack.pop() as string;
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (SKIP_DIRS.has(entry.name)) continue;
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(full);
      } else if (entry.isFile()) {
        if (extensions.has(path.extname(entry.name))) {
          results.push(full);
        }
      }
    }
  }
  return results;
}
