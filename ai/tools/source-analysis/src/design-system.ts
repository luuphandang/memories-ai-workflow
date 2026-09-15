import * as fs from 'node:fs';
import * as path from 'node:path';
import postcss from 'postcss';
import { Project, Node, SyntaxKind, StringLiteral, NoSubstitutionTemplateLiteral } from 'ts-morph';
import { walkFiles } from './lib/walk-files';

const HEX_RE = /#[0-9a-fA-F]{3,8}\b/g;
const TAILWIND_ARBITRARY_RE = /-\[#[0-9a-fA-F]{3,8}\]/;
const BUSINESS_DATA_PATH_RE = /(^|\/)(mock|fixtures|__fixtures__|__mocks__|test)(\/|$)/i;
const BUSINESS_DATA_NAME_RE = /swatch|palette|preset|color.*option/i;
const TOKEN_DIR_RE = /(^|\/)packages\/design-system(\/|$)/;

type Context = 'styling' | 'token-definition' | 'business-data' | 'unknown';

interface ColorEntry {
  file: string;
  line: number;
  value: string;
  context: Context;
  construct: string;
}

interface RootBlock {
  file: string;
  line: number;
}

function toPosix(p: string): string {
  return p.split(path.sep).join('/');
}

function isTokenFile(relPath: string): boolean {
  return TOKEN_DIR_RE.test(relPath) || path.basename(relPath) === 'globals.css';
}

function analyzeCssFile(root: string, absPath: string, colorEntries: ColorEntry[], rootBlocks: RootBlock[]): void {
  const relPath = toPosix(path.relative(root, absPath));
  const text = fs.readFileSync(absPath, 'utf8');
  let ast;
  try {
    ast = postcss.parse(text, { from: absPath });
  } catch {
    return; // unparsable CSS: skip rather than crash the whole run
  }
  const tokenFile = isTokenFile(relPath);
  ast.walkRules((rule) => {
    const isRootRule = rule.selector.trim() === ':root';
    if (isRootRule && relPath.includes('apps/') && path.basename(relPath) !== 'globals.css') {
      rootBlocks.push({ file: relPath, line: rule.source?.start?.line ?? 0 });
    }
    rule.walkDecls((decl) => {
      const matches = decl.value.match(HEX_RE);
      if (!matches) return;
      const line = decl.source?.start?.line ?? 0;
      const context: Context = isRootRule && tokenFile ? 'token-definition' : 'styling';
      for (const value of matches) {
        colorEntries.push({ file: relPath, line, value: value.toLowerCase(), context, construct: 'CssDeclaration' });
      }
    });
  });
}

/** Names collected by walking a literal's ancestors: enclosing variable names and object-property keys. */
function collectAncestorNames(node: Node): string[] {
  const names: string[] = [];
  let current: Node | undefined = node;
  while (current) {
    if (Node.isVariableDeclaration(current)) {
      names.push(current.getName());
    } else if (Node.isPropertyAssignment(current)) {
      const nameNode = current.getNameNode();
      names.push(nameNode.getText().replace(/^['"]|['"]$/g, ''));
    }
    current = current.getParent();
  }
  return names;
}

function isInsideObjectOrArrayLiteral(node: Node): boolean {
  let current: Node | undefined = node.getParent();
  while (current) {
    const kind = current.getKind();
    if (kind === SyntaxKind.ObjectLiteralExpression || kind === SyntaxKind.ArrayLiteralExpression) {
      return true;
    }
    current = current.getParent();
  }
  return false;
}

function isInsideJsxStyleAttribute(node: Node): boolean {
  let current: Node | undefined = node;
  while (current) {
    if (Node.isJsxAttribute(current) && current.getNameNode().getText() === 'style') {
      return true;
    }
    current = current.getParent();
  }
  return false;
}

function isInsideCssInJsTag(node: Node): boolean {
  let current: Node | undefined = node;
  while (current) {
    if (Node.isTaggedTemplateExpression(current)) {
      const tagText = current.getTag().getText();
      if (/^(styled(\.\w+)?(\(.*\))?|css|keyframes)$/.test(tagText.split('(')[0].trim())) {
        return true;
      }
    }
    current = current.getParent();
  }
  return false;
}

function classifyLiteral(node: StringLiteral | NoSubstitutionTemplateLiteral, relPath: string, literalText: string): { context: Context; construct: string } {
  if (isInsideJsxStyleAttribute(node)) {
    return { context: 'styling', construct: 'JsxStyleAttribute' };
  }
  if (isInsideCssInJsTag(node)) {
    return { context: 'styling', construct: 'CssInJsTemplate' };
  }
  if (TAILWIND_ARBITRARY_RE.test(literalText)) {
    return { context: 'styling', construct: 'TailwindArbitraryValue' };
  }
  if (BUSINESS_DATA_PATH_RE.test(relPath) && isInsideObjectOrArrayLiteral(node)) {
    return { context: 'business-data', construct: 'ObjectLiteralInMockPath' };
  }
  if (isInsideObjectOrArrayLiteral(node)) {
    const names = collectAncestorNames(node);
    if (names.some((name) => BUSINESS_DATA_NAME_RE.test(name))) {
      return { context: 'business-data', construct: 'ObjectLiteralProperty' };
    }
  }
  return { context: 'unknown', construct: 'StringLiteral' };
}

function analyzeTsFile(root: string, absPath: string, project: Project, colorEntries: ColorEntry[]): void {
  const relPath = toPosix(path.relative(root, absPath));
  const sourceFile = project.addSourceFileAtPath(absPath);
  sourceFile.forEachDescendant((node) => {
    if (!Node.isStringLiteral(node) && !Node.isNoSubstitutionTemplateLiteral(node)) return;
    const literalText = node.getLiteralText();
    const matches = literalText.match(HEX_RE);
    if (!matches) return;
    const { line } = sourceFile.getLineAndColumnAtPos(node.getStart());
    const { context, construct } = classifyLiteral(node, relPath, literalText);
    for (const value of matches) {
      colorEntries.push({ file: relPath, line, value: value.toLowerCase(), context, construct });
    }
  });
}

export function analyzeDesignSystem(root: string): { color_entries: ColorEntry[]; root_blocks: RootBlock[] } {
  const colorEntries: ColorEntry[] = [];
  const rootBlocks: RootBlock[] = [];

  for (const cssPath of walkFiles(root, new Set(['.css']))) {
    analyzeCssFile(root, cssPath, colorEntries, rootBlocks);
  }

  const project = new Project({ skipAddingFilesFromTsConfig: true });
  for (const tsPath of walkFiles(root, new Set(['.ts', '.tsx']))) {
    analyzeTsFile(root, tsPath, project, colorEntries);
  }

  return { color_entries: colorEntries, root_blocks: rootBlocks };
}
