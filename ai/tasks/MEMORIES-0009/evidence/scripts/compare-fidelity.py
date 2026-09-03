#!/usr/bin/env python3
"""Durable, stdlib-only PNG grid-average-color-distance comparator for MEMORIES-0009's
homepage fidelity evidence (review:5:2 — earlier cycles computed this with an
uncommitted /tmp script, so it could not be reproduced from workspace files).

Decodes 8-bit PNG (RGB/RGBA, any standard filter type, non-interlaced — exactly what
Chrome's `Page.captureScreenshot` produces) using only `zlib`/`struct` from the standard
library, samples each image on a 16x16 grid (proportional to each image's own
width/height, so reference and actual do not need identical pixel dimensions — their
document heights legitimately differ once real catalog content replaces the static
prototype mock), and reports the mean Euclidean RGB distance across corresponding
cells. This number is documented, non-gating evidence (see fidelity-matrix.json's
method_notes) — `status` on each entry reflects an actual visual inspection, not a
threshold on this metric alone.

Usage:
  compare-fidelity.py pair <reference.png> <actual.png>
      Prints the mean_cell_color_distance for one image pair.

  compare-fidelity.py matrix <fidelity-matrix.json> <repo-root>
      Recomputes mean_cell_color_distance in place for every entry whose
      comparison_method starts with "grid-average-color-distance", resolving each
      entry's reference/actual paths relative to <repo-root>.
"""
from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path

GRID = 16
SAMPLES_PER_CELL = 6

_CHANNELS_BY_COLOR_TYPE = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def read_png(path: Path) -> tuple[int, int, int, bytes]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG file")
    pos = 8
    idat = bytearray()
    width = height = bit_depth = color_type = None
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", chunk[:10])
        elif chunk_type == b"IDAT":
            idat.extend(chunk)
        elif chunk_type == b"IEND":
            break
    if width is None or bit_depth != 8:
        raise ValueError(f"{path}: only 8-bit PNG is supported (got bit_depth={bit_depth})")
    channels = _CHANNELS_BY_COLOR_TYPE[color_type]
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    pixels = bytearray(height * stride)
    prev = bytearray(stride)
    src = 0
    for y in range(height):
        filter_type = raw[src]
        src += 1
        line = raw[src : src + stride]
        src += stride
        out = bytearray(stride)
        for x in range(stride):
            a = out[x - channels] if x >= channels else 0
            b = prev[x]
            c = prev[x - channels] if x >= channels else 0
            v = line[x]
            if filter_type == 0:
                out[x] = v
            elif filter_type == 1:
                out[x] = (v + a) & 0xFF
            elif filter_type == 2:
                out[x] = (v + b) & 0xFF
            elif filter_type == 3:
                out[x] = (v + (a + b) // 2) & 0xFF
            elif filter_type == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                out[x] = (v + pr) & 0xFF
            else:
                raise ValueError(f"{path}: unsupported PNG filter type {filter_type}")
        pixels[y * stride : (y + 1) * stride] = out
        prev = out
    return width, height, channels, bytes(pixels)


def grid_average_color(
    width: int, height: int, channels: int, pixels: bytes
) -> list[list[tuple[float, float, float]]]:
    cell_w = width / GRID
    cell_h = height / GRID
    grid: list[list[tuple[float, float, float]]] = []
    for gy in range(GRID):
        row: list[tuple[float, float, float]] = []
        y0, y1 = gy * cell_h, (gy + 1) * cell_h
        for gx in range(GRID):
            x0, x1 = gx * cell_w, (gx + 1) * cell_w
            total = [0.0, 0.0, 0.0]
            for sy in range(SAMPLES_PER_CELL):
                y = int(y0 + (sy + 0.5) * (y1 - y0) / SAMPLES_PER_CELL)
                y = min(height - 1, max(0, y))
                row_off = y * width * channels
                for sx in range(SAMPLES_PER_CELL):
                    x = int(x0 + (sx + 0.5) * (x1 - x0) / SAMPLES_PER_CELL)
                    x = min(width - 1, max(0, x))
                    off = row_off + x * channels
                    total[0] += pixels[off]
                    total[1] += pixels[off + 1]
                    total[2] += pixels[off + 2]
            n = SAMPLES_PER_CELL * SAMPLES_PER_CELL
            row.append((total[0] / n, total[1] / n, total[2] / n))
        grid.append(row)
    return grid


def mean_cell_distance(
    grid_a: list[list[tuple[float, float, float]]], grid_b: list[list[tuple[float, float, float]]]
) -> float:
    total = 0.0
    count = 0
    for row_a, row_b in zip(grid_a, grid_b):
        for a, b in zip(row_a, row_b):
            total += sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5
            count += 1
    return total / count


def compare(reference: Path, actual: Path) -> float:
    ref_grid = grid_average_color(*read_png(reference))
    act_grid = grid_average_color(*read_png(actual))
    return round(mean_cell_distance(ref_grid, act_grid), 2)


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "pair":
        distance = compare(Path(sys.argv[2]), Path(sys.argv[3]))
        print(distance)
        return 0
    if len(sys.argv) == 4 and sys.argv[1] == "matrix":
        matrix_path = Path(sys.argv[2])
        repo_root = Path(sys.argv[3]).resolve()
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        updated = 0
        for entry in matrix.get("entries", []):
            method = entry.get("comparison_method", "")
            if not method.startswith("grid-average-color-distance"):
                continue
            reference = repo_root / entry["reference"]
            actual = repo_root / entry["actual"]
            entry["mean_cell_color_distance"] = compare(reference, actual)
            updated += 1
        matrix_path.write_text(f"{json.dumps(matrix, indent=2, ensure_ascii=False)}\n", encoding="utf-8")
        print(f"Recomputed mean_cell_color_distance for {updated} matrix entr{'y' if updated == 1 else 'ies'}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
