#!/usr/bin/env node
/**
 * Durable, dependency-free CDP capture for MEMORIES-0009's homepage fidelity evidence.
 *
 * Uses only Node's built-in `fetch`/`WebSocket` (stable since Node 22) to drive an
 * already-running headless Chrome instance over the DevTools Protocol — no npm package
 * (not even `ws`) and no /tmp scratch files. This replaces the review-cycle-2/3 ad-hoc
 * /tmp/mem0009-fidelity-v2 and -v3 scripts referenced in earlier fidelity-matrix.json
 * revisions (review:5:2): those were never committed, so the capture procedure could not
 * be reproduced once the /tmp directory was cleaned up.
 *
 * Root causes this script deliberately works around (see prior fidelity-matrix.json
 * method_notes / implementation-progress.json decisions for the original diagnosis):
 *   - Both the prototype's own scroll-reveal script and apps/public-web/components/
 *     common/reveal.tsx keep `.reveal`/`Reveal`-wrapped elements at opacity:0 until an
 *     IntersectionObserver fires, which never happens for below-fold content in a
 *     non-scrolling headless capture. Fix: emulate `prefers-reduced-motion: reduce`
 *     before navigation — both implementations already treat that as an immediate-
 *     visible fallback (not a capture-only hack).
 *   - `captureBeyondViewport` renders the whole document in one shot without scrolling
 *     it, so next/image's native `loading="lazy"` never fetches images far below the
 *     initial fold (Gifts cards; the Testimonials carousel's non-current slides, which
 *     also sit outside the *horizontal* viewport inside a translateX track). Fix: scroll
 *     the full document, click through every carousel dot, then scrollIntoView + await
 *     completion for any image still incomplete, before taking the screenshot.
 *
 * Prerequisites (documented in this directory's README.md):
 *   1. `npm run build --workspace=@memories/public-web && npx next start -p 3100
 *      --prefix worktrees/MEMORIES-0009/frontend/apps/public-web` (or equivalent) —
 *      a fresh production server for the *current* worktree state.
 *   2. A headless Chrome/Chromium reachable at --cdp-port (default 9223), e.g.:
 *      `google-chrome --headless=new --remote-debugging-port=9223
 *      --window-size=1600,1200 --user-data-dir=/tmp/mem0009-chrome-profile`
 *
 * Usage:
 *   node ai/tasks/MEMORIES-0009/evidence/scripts/capture-fidelity.mjs \
 *     [--cdp-port=9223] [--actual-base=http://127.0.0.1:3100] [--repo-root=<path>]
 *
 * Exits non-zero (and writes no partial screenshots for the failing check) if any image
 * is still incomplete after the settle retries; if any open/dismiss selector (trigger, outside
 * target, close button) matches nothing in the DOM; if the outside-click dismissal's real CDP
 * mousePressed+mouseReleased pointer sequence never completes its own click lifecycle on the
 * outside target (verified via a one-time listener, not just the popover's mousedown-triggered
 * dismissal); if the search dialog fails to actually open or fails to actually close (by DOM
 * presence, not just an unchanged geometry read) after any of its three dismissal paths (Escape,
 * outside click, close button); or if opening search from a deterministic non-zero scroll
 * position changes header/main geometry, introduces horizontal overflow, or shifts window.scrollY
 * at any point across open + all three dismissal paths at any
 * viewport.
 */
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

function parseArgs(argv) {
  const args = {};
  for (const arg of argv) {
    const match = /^--([a-z-]+)(?:=(.*))?$/.exec(arg);
    if (match) args[match[1]] = match[2] ?? true;
  }
  return args;
}

const args = parseArgs(process.argv.slice(2));
const scriptDir = dirname(fileURLToPath(import.meta.url));
const evidenceDir = resolve(scriptDir, '..');
const repoRoot = resolve(String(args['repo-root'] ?? resolve(scriptDir, '../../../../..')));
const cdpPort = String(args['cdp-port'] ?? '9223');
const actualBase = String(args['actual-base'] ?? 'http://127.0.0.1:3100').replace(/\/$/, '');
const endpoint = `http://127.0.0.1:${cdpPort}`;
const viewports = [
  [375, 812],
  [768, 1024],
  [1440, 900],
];

let messageId = 0;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function openPage() {
  const target = await fetch(`${endpoint}/json/new?about:blank`, { method: 'PUT' }).then((r) =>
    r.json(),
  );
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  const pending = new Map();
  await new Promise((resolveOpen, reject) => {
    socket.addEventListener('open', () => resolveOpen(undefined), { once: true });
    socket.addEventListener('error', reject, { once: true });
  });
  socket.addEventListener('message', (event) => {
    const payload = JSON.parse(event.data);
    if (!payload.id) return;
    const request = pending.get(payload.id);
    if (!request) return;
    pending.delete(payload.id);
    if (payload.error) request.reject(new Error(payload.error.message));
    else request.resolve(payload.result);
  });
  const send = (method, params = {}) =>
    new Promise((resolveSend, reject) => {
      const id = (messageId += 1);
      pending.set(id, { resolve: resolveSend, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
  await send('Page.enable');
  await send('Runtime.enable');
  return { socket, send, targetId: target.id };
}

async function closePage(page) {
  page.socket.close();
  await fetch(`${endpoint}/json/close/${page.targetId}`).catch(() => undefined);
}

async function evaluate(page, expression, { awaitPromise = false } = {}) {
  const result = await page.send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text ?? JSON.stringify(result.exceptionDetails));
  }
  return result.result.value;
}

/** Scrolls the full document, cycles every Testimonials-carousel dot, then scrollIntoView
 * + awaits completion for any <img> still incomplete (bounded retries). */
const SETTLE_SCRIPT = `(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const step = Math.max(400, window.innerHeight);
  for (let y = 0; y < document.body.scrollHeight; y += step) {
    window.scrollTo(0, y);
    await sleep(120);
  }
  const dots = Array.from(document.querySelectorAll('button[aria-label^="Đến mục "]'));
  for (const dot of dots) {
    dot.click();
    await sleep(150);
  }
  if (dots[0]) { dots[0].click(); await sleep(150); }
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const incomplete = Array.from(document.images).filter((img) => !img.complete || img.naturalWidth === 0);
    if (incomplete.length === 0) break;
    incomplete.forEach((img) => img.scrollIntoView({ block: 'center' }));
    await sleep(300);
  }
  window.scrollTo(0, 0);
  await sleep(100);
  const stillIncomplete = Array.from(document.images).filter((img) => !img.complete || img.naturalWidth === 0).length;
  return { total: document.images.length, incomplete: stillIncomplete, scrollHeight: document.body.scrollHeight };
})()`;

async function captureDefault(page, { url, width, height, output }) {
  await page.send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
    screenWidth: width,
    screenHeight: height,
  });
  await page.send('Emulation.setEmulatedMedia', {
    features: [{ name: 'prefers-reduced-motion', value: 'reduce' }],
  });
  await page.send('Page.navigate', { url });
  await wait(1500);
  const settle = await evaluate(page, SETTLE_SCRIPT, { awaitPromise: true });
  if (settle.incomplete > 0) {
    throw new Error(
      `${url} @ ${width}x${height}: ${settle.incomplete}/${settle.total} images still incomplete after settle retries`,
    );
  }
  const { data } = await page.send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: true,
    clip: { x: 0, y: 0, width, height: settle.scrollHeight, scale: 1 },
  });
  await writeFile(output, Buffer.from(data, 'base64'));
  return settle;
}

async function readHeaderGeometry(page) {
  return evaluate(page, `(() => {
    const header = document.querySelector('header');
    const main = document.querySelector('main');
    const headerRect = header.getBoundingClientRect();
    return {
      headerHeight: headerRect.height,
      headerBottom: headerRect.bottom,
      mainTop: main ? main.getBoundingClientRect().top : null,
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      scrollY: window.scrollY,
    };
  })()`);
}

const SEARCH_POPOVER_ID = 'site-header-search-popover';
const OPEN_TRIGGER_SCRIPT = `(() => {
  const btn = document.querySelector('header button[aria-haspopup="dialog"]');
  if (!btn) return false;
  btn.click();
  return true;
})()`;
// Scans the header's own background for a point whose hit-tested element is not a link/
// button/input (so the click cannot trigger an unrelated side effect — e.g. clicking the
// logo `<a href="/">` while scrolled resets window.scrollY to 0 as a normal, correct
// consequence of Next.js Link's own scroll-to-top-on-navigate behavior, which would
// contaminate the popover-dismissal scroll/geometry assertion below with an unrelated
// navigation side effect rather than proving the popover itself preserves scroll). Returns
// the point's viewport-relative coordinates and arms a one-time `click` listener on it
// (recorded on `window.__outsideClickFired`) so a caller can verify, after dispatching a real
// CDP pointer sequence at those coordinates, that the target's full press-release-click
// lifecycle actually completed — not just the app's own `mousedown` dismiss listener
// (review-009 finding #1: a bare synthetic `mousedown` event proved the component dismissed,
// but never exercised or verified the rest of a real click).
const OUTSIDE_CLICK_TARGET_SCRIPT = `(() => {
  const header = document.querySelector('header');
  if (!header) return null;
  const rect = header.getBoundingClientRect();
  const y = rect.top + rect.height / 2;
  for (let x = rect.left + 1; x < rect.right; x += 4) {
    const el = document.elementFromPoint(x, y);
    if (!el) continue;
    if (el.closest('a, button, input, [role="dialog"], [role="menu"]')) continue;
    window.__outsideClickFired = false;
    el.addEventListener('click', () => { window.__outsideClickFired = true; }, { once: true });
    return { x, y };
  }
  return null;
})()`;
const OUTSIDE_CLICK_FIRED_SCRIPT = `window.__outsideClickFired === true`;
// Popover unmounts entirely on close (see packages/ui/src/components/popover.tsx: `if (!open)
// return null`), so the close button is only ever present in the DOM while the dialog is open —
// select it by its accessible name (it is icon-only, no text node, so `textContent` never
// matches it) scoped to the popover surface itself.
const CLOSE_BUTTON_SCRIPT = `(() => {
  const btn = document.querySelector('#${SEARCH_POPOVER_ID} [aria-label="Đóng tìm kiếm"]');
  if (!btn) return false;
  btn.click();
  return true;
})()`;
const IS_DIALOG_OPEN_SCRIPT = `!!document.getElementById('${SEARCH_POPOVER_ID}')`;

async function runRequiredAction(page, script, label) {
  const acted = await evaluate(page, script);
  if (!acted) {
    throw new Error(`${label}: selector matched nothing, no action performed`);
  }
}

// Drives a genuine CDP `mousePressed` + `mouseReleased` pointer sequence at the outside
// target's coordinates — the same primitive a real user click resolves to (mousedown, then
// mouseup, then a browser-synthesized click) — rather than dispatching a single synthetic
// `mousedown` event from JS. Verifies the target's own `click` listener actually fired
// afterward, so a regression that only proves the popover's `mousedown` listener ran (and
// never completes/verifies the rest of the click) is caught.
async function runOutsideClick(page, label) {
  const target = await evaluate(page, OUTSIDE_CLICK_TARGET_SCRIPT);
  if (!target) {
    throw new Error(`${label}: selector matched nothing, no action performed`);
  }
  await page.send('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x: target.x,
    y: target.y,
    button: 'left',
    clickCount: 1,
  });
  await page.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x: target.x,
    y: target.y,
    button: 'left',
    clickCount: 1,
  });
  await wait(150);
  const fired = await evaluate(page, OUTSIDE_CLICK_FIRED_SCRIPT);
  if (!fired) {
    throw new Error(
      `${label}: outside target's click event never fired (mousedown-only interaction, not a complete click)`,
    );
  }
}

async function assertDialogState(page, expectedOpen, label) {
  const isOpen = await evaluate(page, IS_DIALOG_OPEN_SCRIPT);
  if (isOpen !== expectedOpen) {
    throw new Error(`${label}: expected dialog open=${expectedOpen} but found open=${isOpen}`);
  }
}

/**
 * Opens search from a deterministic non-zero scroll position and exercises all three
 * dismissal paths (Escape, outside click, close button), reading header/main geometry
 * (including scrollY) before/after each so a scroll jump on open or on any dismissal path
 * is caught the same way a layout-geometry regression is (review-007 finding #2), AND asserts
 * after every open/dismiss action that the dialog's actual DOM presence matches what was
 * intended — throwing immediately if a selector matches nothing or the dialog fails to open/
 * close, rather than silently recording geometry for a no-op action (review-008 finding #1: the
 * prior close-button selector matched `button.textContent`, which the real icon-only close
 * control never has, so the button was never clicked and "afterCloseButton" silently reused the
 * still-open state).
 */
async function captureSearchOpen(page, { width, height, output }) {
  await page.send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
    screenWidth: width,
    screenHeight: height,
  });
  await page.send('Page.navigate', { url: `${actualBase}/` });
  await wait(1500);
  await evaluate(
    page,
    `(() => { window.scrollTo(0, Math.round(Math.min(600, document.body.scrollHeight * 0.3))); })()`,
  );
  await wait(150);
  const before = await readHeaderGeometry(page);
  await assertDialogState(page, false, 'before-open');

  await runRequiredAction(page, OPEN_TRIGGER_SCRIPT, 'open-trigger');
  await wait(400);
  await assertDialogState(page, true, 'after-open');
  const afterOpen = await readHeaderGeometry(page);
  const { data } = await page.send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: false,
  });
  await writeFile(output, Buffer.from(data, 'base64'));

  await evaluate(
    page,
    `document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`,
  );
  await wait(300);
  await assertDialogState(page, false, 'after-escape-close');
  const afterEscape = await readHeaderGeometry(page);

  await runRequiredAction(page, OPEN_TRIGGER_SCRIPT, 'open-trigger (before outside click)');
  await wait(400);
  await assertDialogState(page, true, 'after-open (before outside click)');
  await runOutsideClick(page, 'outside-click target');
  await wait(300);
  await assertDialogState(page, false, 'after-outside-click-close');
  const afterOutsideClick = await readHeaderGeometry(page);

  await runRequiredAction(page, OPEN_TRIGGER_SCRIPT, 'open-trigger (before close button)');
  await wait(400);
  await assertDialogState(page, true, 'after-open (before close button)');
  await runRequiredAction(page, CLOSE_BUTTON_SCRIPT, 'close button');
  await wait(300);
  await assertDialogState(page, false, 'after-close-button-close');
  const afterCloseButton = await readHeaderGeometry(page);

  return {
    before,
    afterOpen,
    afterEscape,
    afterOutsideClick,
    afterCloseButton,
    closedAfterEscape: true,
    closedAfterOutsideClick: true,
    closedAfterCloseButton: true,
  };
}

const READ_FIRST_CTA_SCRIPT = `(() => {
  const cta = document.querySelector('a[href^="/tao-thiep?template="]');
  if (!cta) return null;
  const style = getComputedStyle(cta);
  const rect = cta.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;
  const hitTarget = document.elementFromPoint(centerX, centerY);
  return {
    opacity: style.opacity,
    pointerEvents: style.pointerEvents,
    rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
    hittable: !!hitTarget && (hitTarget === cta || cta.contains(hitTarget)),
    center: { x: centerX, y: centerY },
  };
})()`;

/**
 * Verifies the review-007 finding #1 fix at both sides of the CTA visibility boundary: the
 * prototype's `.use-template` override keeps the CTA visible/operable through 1024px
 * inclusive, and only above that (1025px+) does it become a hover/focus-revealed control that
 * must not be an invisible pointer-clickable hit target while hidden.
 */
async function captureCtaBoundary(page, { outDir }) {
  const results = {};

  for (const width of [1024, 1025]) {
    await page.send('Emulation.setDeviceMetricsOverride', {
      width,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
      screenWidth: width,
      screenHeight: 900,
    });
    await page.send('Page.navigate', { url: `${actualBase}/` });
    await wait(1500);
    await evaluate(
      page,
      `document.querySelector('#templates-teaser-title')?.scrollIntoView({ block: 'center' })`,
    );
    await wait(200);

    const defaultState = await evaluate(page, READ_FIRST_CTA_SCRIPT);
    if (!defaultState) throw new Error(`No use-template CTA found at ${width}px`);

    await page.send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x: defaultState.center.x,
      y: defaultState.center.y,
    });
    await wait(250);
    const hoveredState = await evaluate(page, READ_FIRST_CTA_SCRIPT);
    // Move the mouse away so the next viewport's initial read is unaffected by a stale :hover.
    await page.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 2, y: 2 });
    await wait(100);

    const { data } = await page.send('Page.captureScreenshot', {
      format: 'png',
      captureBeyondViewport: false,
    });
    await writeFile(`${outDir}/cta-boundary-${width}px.png`, Buffer.from(data, 'base64'));

    results[width] = { default: defaultState, hovered: hoveredState };
  }

  return results;
}

async function main() {
  const outDir = `${evidenceDir}/screenshots/fidelity`;
  await mkdir(`${outDir}/reference`, { recursive: true });
  await mkdir(`${outDir}/actual`, { recursive: true });

  const page = await openPage();
  const geometryLines = [];
  const settleReport = [];

  try {
    for (const [width, height] of viewports) {
      const viewport = `${width}x${height}`;

      const refSettle = await captureDefault(page, {
        url: `file://${repoRoot}/prototype/index/index.html`,
        width,
        height,
        output: `${outDir}/reference/home-${viewport}-default.png`,
      });
      settleReport.push({ viewport, side: 'reference', ...refSettle });

      const actualSettle = await captureDefault(page, {
        url: `${actualBase}/`,
        width,
        height,
        output: `${outDir}/actual/home-${viewport}-default.png`,
      });
      settleReport.push({ viewport, side: 'actual', ...actualSettle });

      const search = await captureSearchOpen(page, {
        width,
        height,
        output: `${outDir}/actual/home-${viewport}-search-open.png`,
      });
      geometryLines.push(`${viewport} before (scrolled): ${JSON.stringify(search.before)}`);
      geometryLines.push(`${viewport} after-open: ${JSON.stringify(search.afterOpen)}`);
      geometryLines.push(
        `${viewport} after-escape-close: closed=${search.closedAfterEscape} ${JSON.stringify(search.afterEscape)}`,
      );
      geometryLines.push(
        `${viewport} after-outside-click-close: closed=${search.closedAfterOutsideClick} ${JSON.stringify(search.afterOutsideClick)}`,
      );
      geometryLines.push(
        `${viewport} after-close-button-close: closed=${search.closedAfterCloseButton} ${JSON.stringify(search.afterCloseButton)}`,
      );
      const identical = ['headerHeight', 'headerBottom', 'mainTop'].every(
        (key) => search.before[key] === search.afterOpen[key],
      );
      const noOverflow = search.afterOpen.scrollWidth === search.afterOpen.innerWidth;
      // scrollY must equal the pre-open, non-zero scroll position after open and after every
      // dismissal path (Escape, outside click, close button) — a scroll jump on any of these
      // is a regression even if headerHeight/headerBottom/mainTop stay byte-identical.
      const scrollPreserved = [
        search.afterOpen,
        search.afterEscape,
        search.afterOutsideClick,
        search.afterCloseButton,
      ].every((state) => state.scrollY === search.before.scrollY);
      geometryLines.push(
        `${viewport} geometry-identical=${identical} no-horizontal-overflow=${noOverflow} scroll-preserved=${scrollPreserved} (scrollY=${search.before.scrollY})`,
      );
      if (!identical || !noOverflow || !scrollPreserved) {
        throw new Error(
          `${viewport}: search-open geometry regression (identical=${identical}, noOverflow=${noOverflow}, scrollPreserved=${scrollPreserved})`,
        );
      }
    }

    const ctaBoundary = await captureCtaBoundary(page, { outDir });
    const at1024 = ctaBoundary[1024].default;
    const at1025Default = ctaBoundary[1025].default;
    const at1025Hovered = ctaBoundary[1025].hovered;
    const visibleAt1024 = Number(at1024.opacity) === 1 && at1024.pointerEvents !== 'none';
    const hittableAt1024 = at1024.hittable;
    const hiddenByDefaultAt1025 =
      Number(at1025Default.opacity) === 0 && at1025Default.pointerEvents === 'none';
    const notHittableAt1025 = !at1025Default.hittable;
    const revealedOnHoverAt1025 =
      Number(at1025Hovered.opacity) === 1 && at1025Hovered.pointerEvents !== 'none';
    const ctaBoundaryOk =
      visibleAt1024 &&
      hittableAt1024 &&
      hiddenByDefaultAt1025 &&
      notHittableAt1025 &&
      revealedOnHoverAt1025;
    geometryLines.push(
      `cta-boundary 1024px default: opacity=${at1024.opacity} pointerEvents=${at1024.pointerEvents} hittable=${at1024.hittable}`,
    );
    geometryLines.push(
      `cta-boundary 1025px default: opacity=${at1025Default.opacity} pointerEvents=${at1025Default.pointerEvents} hittable=${at1025Default.hittable}`,
    );
    geometryLines.push(
      `cta-boundary 1025px hovered: opacity=${at1025Hovered.opacity} pointerEvents=${at1025Hovered.pointerEvents} hittable=${at1025Hovered.hittable}`,
    );
    geometryLines.push(`cta-boundary-ok=${ctaBoundaryOk}`);
    if (!ctaBoundaryOk) {
      throw new Error(
        `CTA visibility boundary regression: ${JSON.stringify({ visibleAt1024, hittableAt1024, hiddenByDefaultAt1025, notHittableAt1025, revealedOnHoverAt1025 })}`,
      );
    }
  } finally {
    await closePage(page);
  }

  await writeFile(`${evidenceDir}/screenshots/geometry.log`, `${geometryLines.join('\n')}\n`);
  await writeFile(
    `${evidenceDir}/screenshots/capture-report.json`,
    `${JSON.stringify({ generated_at: new Date().toISOString(), settleReport }, null, 2)}\n`,
  );
  console.log(
    'Capture complete: every image settled complete at every viewport; search-open geometry byte-identical (scrollY preserved) with no horizontal overflow; CTA visibility boundary correct at 1024px/1025px.',
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
