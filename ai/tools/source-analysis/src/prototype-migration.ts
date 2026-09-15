import * as fs from 'node:fs';
import * as path from 'node:path';
import postcss from 'postcss';
import { parse as parseHtml } from 'node-html-parser';
import { Project, Node, SourceFile } from 'ts-morph';
import { walkFiles } from './lib/walk-files';

const PROTOTYPE_TEXT_RE = /(?:\.\.\/)*prototype\//;
const LOWERCASE_HANDLER_ATTRS = new Set(['onclick', 'onchange', 'oninput', 'onsubmit']);
const DOM_QUERY_METHODS = new Set(['querySelector', 'getElementById', 'getElementsByClassName']);
const HTML_COMMENT_RE = /<!--[\s\S]*?-->/g;

type Rule = 'prototype-import' | 'prototype-comment' | 'manual-dom-query' | 'innerhtml-mutation' | 'inline-html-handler';
type Context = 'import' | 'comment' | 'string' | 'call' | 'assignment' | 'jsx-attribute';

interface Finding {
  file: string;
  line: number;
  rule: Rule;
  context: Context;
  snippet: string;
}

function toPosix(p: string): string {
  return p.split(path.sep).join('/');
}

function collectComments(sourceFile: SourceFile): Array<{ pos: number; text: string }> {
  const seen = new Set<number>();
  const comments: Array<{ pos: number; text: string }> = [];
  sourceFile.forEachDescendant((node) => {
    for (const range of [...node.getLeadingCommentRanges(), ...node.getTrailingCommentRanges()]) {
      if (seen.has(range.getPos())) continue;
      seen.add(range.getPos());
      comments.push({ pos: range.getPos(), text: range.getText() });
    }
  });
  return comments;
}

function isImportModuleSpecifier(node: Node): boolean {
  const parent = node.getParent();
  if (!parent) return false;
  if (Node.isImportDeclaration(parent) || Node.isExportDeclaration(parent)) {
    return true; // moduleSpecifier of `import ... from '...'` / `export ... from '...'`
  }
  if (Node.isCallExpression(parent)) {
    // require('...') and dynamic import('...') both render their callee's text as
    // "require" / "import" (the latter is a bare ImportKeyword token, not an identifier).
    const calleeText = parent.getExpression().getText();
    return calleeText === 'require' || calleeText === 'import';
  }
  return false;
}

function analyzeTsFile(root: string, absPath: string, project: Project, findings: Finding[]): void {
  const relPath = toPosix(path.relative(root, absPath));
  const sourceFile = project.addSourceFileAtPath(absPath);

  for (const comment of collectComments(sourceFile)) {
    if (PROTOTYPE_TEXT_RE.test(comment.text)) {
      const { line } = sourceFile.getLineAndColumnAtPos(comment.pos);
      findings.push({ file: relPath, line, rule: 'prototype-comment', context: 'comment', snippet: comment.text.trim().slice(0, 200) });
    }
  }

  sourceFile.forEachDescendant((node) => {
    if (Node.isStringLiteral(node) && PROTOTYPE_TEXT_RE.test(node.getLiteralText())) {
      const { line } = sourceFile.getLineAndColumnAtPos(node.getStart());
      const isImport = isImportModuleSpecifier(node);
      findings.push({
        file: relPath,
        line,
        rule: isImport ? 'prototype-import' : 'prototype-comment',
        context: isImport ? 'import' : 'string',
        snippet: node.getText().slice(0, 200),
      });
      return;
    }
    if (Node.isCallExpression(node)) {
      const expr = node.getExpression();
      if (Node.isPropertyAccessExpression(expr)) {
        const objectText = expr.getExpression().getText();
        const methodName = expr.getName();
        if (objectText === 'document' && DOM_QUERY_METHODS.has(methodName)) {
          const { line } = sourceFile.getLineAndColumnAtPos(node.getStart());
          findings.push({ file: relPath, line, rule: 'manual-dom-query', context: 'call', snippet: node.getText().slice(0, 200) });
        }
      }
    }
    if (Node.isBinaryExpression(node) && node.getOperatorToken().getText() === '=') {
      const left = node.getLeft();
      if (Node.isPropertyAccessExpression(left) && left.getName() === 'innerHTML') {
        const { line } = sourceFile.getLineAndColumnAtPos(node.getStart());
        findings.push({ file: relPath, line, rule: 'innerhtml-mutation', context: 'assignment', snippet: node.getText().slice(0, 200) });
      }
    }
    if (Node.isJsxAttribute(node)) {
      const attrName = node.getNameNode().getText();
      if (LOWERCASE_HANDLER_ATTRS.has(attrName)) {
        const { line } = sourceFile.getLineAndColumnAtPos(node.getStart());
        findings.push({ file: relPath, line, rule: 'inline-html-handler', context: 'jsx-attribute', snippet: node.getText().slice(0, 200) });
      }
    }
  });
}

function analyzeCssFile(root: string, absPath: string, findings: Finding[]): void {
  const relPath = toPosix(path.relative(root, absPath));
  const text = fs.readFileSync(absPath, 'utf8');
  let ast;
  try {
    ast = postcss.parse(text, { from: absPath });
  } catch {
    return;
  }
  ast.walkComments((comment) => {
    if (PROTOTYPE_TEXT_RE.test(comment.text)) {
      findings.push({ file: relPath, line: comment.source?.start?.line ?? 0, rule: 'prototype-comment', context: 'comment', snippet: comment.text.slice(0, 200) });
    }
  });
  ast.walkDecls((decl) => {
    if (PROTOTYPE_TEXT_RE.test(decl.value)) {
      findings.push({ file: relPath, line: decl.source?.start?.line ?? 0, rule: 'prototype-comment', context: 'string', snippet: `${decl.prop}: ${decl.value}`.slice(0, 200) });
    }
  });
}

function analyzeHtmlFile(root: string, absPath: string, findings: Finding[]): void {
  const relPath = toPosix(path.relative(root, absPath));
  const rawText = fs.readFileSync(absPath, 'utf8');
  const withoutComments = rawText.replace(HTML_COMMENT_RE, '');
  const lineOf = (index: number): number => withoutComments.slice(0, index).split('\n').length;

  if (PROTOTYPE_TEXT_RE.test(withoutComments)) {
    const match = withoutComments.match(PROTOTYPE_TEXT_RE);
    findings.push({ file: relPath, line: match ? lineOf(match.index ?? 0) : 0, rule: 'prototype-comment', context: 'string', snippet: 'prototype/ reference in HTML (not AST-verifiable as an import here)' });
  }
  const dom = parseHtml(withoutComments);
  for (const method of DOM_QUERY_METHODS) {
    if (withoutComments.includes(`document.${method}(`)) {
      findings.push({ file: relPath, line: 0, rule: 'manual-dom-query', context: 'call', snippet: `document.${method}(` });
    }
  }
  if (/\.innerHTML\s*=/.test(withoutComments)) {
    findings.push({ file: relPath, line: 0, rule: 'innerhtml-mutation', context: 'assignment', snippet: '.innerHTML =' });
  }
  for (const element of dom.querySelectorAll('*')) {
    for (const attr of Object.keys(element.attributes)) {
      if (LOWERCASE_HANDLER_ATTRS.has(attr.toLowerCase())) {
        findings.push({ file: relPath, line: 0, rule: 'inline-html-handler', context: 'jsx-attribute', snippet: `${attr}="${element.attributes[attr]}"` });
      }
    }
  }
}

export function analyzePrototypeMigration(root: string): { findings: Finding[] } {
  const findings: Finding[] = [];
  const project = new Project({ skipAddingFilesFromTsConfig: true });

  for (const tsPath of walkFiles(root, new Set(['.ts', '.tsx', '.js', '.jsx']))) {
    analyzeTsFile(root, tsPath, project, findings);
  }
  for (const cssPath of walkFiles(root, new Set(['.css']))) {
    analyzeCssFile(root, cssPath, findings);
  }
  for (const htmlPath of walkFiles(root, new Set(['.html']))) {
    analyzeHtmlFile(root, htmlPath, findings);
  }

  return { findings };
}
