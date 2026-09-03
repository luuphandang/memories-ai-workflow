# MEMORIES-0009 homepage fidelity evidence — reproduction procedure

Durable replacement for the review-cycle-2/3 ad-hoc `/tmp/mem0009-fidelity-v2` and
`-v3` scripts (review:5:2 finding: those were never committed, so the capture
procedure they document in `fidelity-matrix.json`'s `method_notes` could not be
reproduced once `/tmp` was cleaned). Both scripts here are dependency-free (Node's
built-in `fetch`/`WebSocket`, Python's stdlib `zlib`/`struct`) and live under version
control, so `check_provenance.py` can hash them like any other evidence artifact.

## Prerequisites

1. A production build/server of the **current** worktree state, on port 3100:

   ```sh
   cd worktrees/MEMORIES-0009/frontend
   npm run build --workspace=@memories/public-web
   npx --prefix apps/public-web next start -p 3100
   ```

2. A headless Chrome/Chromium reachable over the DevTools Protocol, e.g.:

   ```sh
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
     --headless=new --remote-debugging-port=9223 --window-size=1600,1200 \
     --user-data-dir="$(mktemp -d)"
   ```

## Capture

From the repo root:

```sh
node ai/tasks/MEMORIES-0009/evidence/scripts/capture-fidelity.mjs \
  --cdp-port=9223 --actual-base=http://127.0.0.1:3100
```

This regenerates, under `ai/tasks/MEMORIES-0009/evidence/screenshots/`:

- `fidelity/reference/home-<viewport>-default.png` (prototype/index/index.html, full page)
- `fidelity/actual/home-<viewport>-default.png` (the running app, full page)
- `fidelity/actual/home-<viewport>-search-open.png`
- `geometry.log` (header/main geometry closed vs. search-open, plus a
  `geometry-identical=…no-horizontal-overflow=…` line per viewport)
- `capture-report.json` (per-viewport/per-side image-completeness counts)

The script **exits non-zero** (leaving the previous screenshots untouched for whichever
viewport failed) if any `<img>` is still incomplete after the scroll/carousel/
`scrollIntoView` settle retries, or if opening search changes header/main geometry or
introduces horizontal overflow at any viewport — there is no path to a passing run with
stale or broken evidence.

## Compare

```sh
python3 ai/tasks/MEMORIES-0009/evidence/scripts/compare-fidelity.py \
  matrix ai/tasks/MEMORIES-0009/evidence/fidelity-matrix.json .
```

Recomputes `mean_cell_color_distance` in place for every `default`-state entry (the
`search-open` entries are validated by `geometry.log`, not pixel comparison — the static
prototype's search button has no working overlay to compare against).

## Verify

```sh
python3 ai/skills/review-frontend-ui-fidelity/scripts/check_fidelity_matrix.py \
  ai/tasks/MEMORIES-0009/evidence/fidelity-matrix.json
```
