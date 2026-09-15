#!/usr/bin/env python3
"""Regression coverage for check_fidelity_matrix.py's hardened acceptance-evidence gate
(workflow_issue.md #4): a fidelity matrix entry can no longer be trusted as `passed` just
because it has the right shape -- reference/actual must exist, hash to the declared
sha256, and the comparison score must respect its threshold. `--require-all-passed`
additionally refuses any entry that isn't `passed`, so scaffolded evidence can never be
used as acceptance evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/review-frontend-ui-fidelity/scripts/check_fidelity_matrix.py"
)


def run(matrix_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(matrix_path), *extra],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )


def write_pair(root: Path, ref_bytes: bytes, actual_bytes: bytes) -> tuple[Path, Path, str, str]:
    reference = root / "reference.png"
    actual = root / "actual.png"
    reference.write_bytes(ref_bytes)
    actual.write_bytes(actual_bytes)
    return reference, actual, hashlib.sha256(ref_bytes).hexdigest(), hashlib.sha256(actual_bytes).hexdigest()


def passed_entry(reference_sha: str, actual_sha: str, *, score: float = 0.0, threshold: float = 5.0) -> dict:
    return {
        "route": "/", "viewport": "375x812", "state": "default", "status": "passed",
        "reference": "reference.png", "actual": "actual.png",
        "reference_sha256": reference_sha, "actual_sha256": actual_sha,
        "comparison": {"tool": "t", "tool_version": "1.0", "algorithm": "a", "threshold": threshold, "score": score},
    }


class FidelityMatrixTest(unittest.TestCase):
    def test_passed_entry_with_correct_hashes_and_score_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, _, ref_sha, act_sha = write_pair(root, b"reference", b"actual")
            matrix = root / "matrix.json"
            matrix.write_text(json.dumps({"entries": [passed_entry(ref_sha, act_sha)]}))
            result = run(matrix)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_tampered_actual_file_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, _, ref_sha, act_sha = write_pair(root, b"reference", b"actual")
            matrix = root / "matrix.json"
            matrix.write_text(json.dumps({"entries": [passed_entry(ref_sha, act_sha)]}))
            (root / "actual.png").write_bytes(b"swapped-image-bytes")
            result = run(matrix)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("sha256 mismatch", result.stdout)

    def test_score_above_threshold_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, _, ref_sha, act_sha = write_pair(root, b"reference", b"actual")
            matrix = root / "matrix.json"
            matrix.write_text(json.dumps({"entries": [passed_entry(ref_sha, act_sha, score=9.0, threshold=5.0)]}))
            result = run(matrix)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("exceeds threshold", result.stdout)

    def test_not_verified_entry_with_empty_paths_passes_default_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            matrix = root / "matrix.json"
            matrix.write_text(json.dumps({"entries": [
                {"route": "/", "viewport": "375x812", "state": "default", "status": "not_verified"}
            ]}))
            result = run(matrix)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_not_verified_entry_fails_require_all_passed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            matrix = root / "matrix.json"
            matrix.write_text(json.dumps({"entries": [
                {"route": "/", "viewport": "375x812", "state": "default", "status": "not_verified"}
            ]}))
            result = run(matrix, "--require-all-passed")
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("not passed", result.stdout)

    def test_passed_status_without_comparison_fails_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            matrix = root / "matrix.json"
            matrix.write_text(json.dumps({"entries": [
                {"route": "/", "viewport": "375x812", "state": "default", "status": "passed"}
            ]}))
            result = run(matrix)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("schema violation", result.stdout)


if __name__ == "__main__":
    unittest.main()
