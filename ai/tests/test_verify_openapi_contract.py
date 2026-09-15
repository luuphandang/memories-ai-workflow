from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "skills" / "verify-openapi-contract" / "scripts" / "check_openapi_contract.py"


def write_fixture(root: Path, *, document_responses: dict | None, path: str = "/api/v1/auth/register", required_statuses=(201, 400, 409)) -> None:
    (root / "controller.ts").write_text("class Controller {}\n", encoding="utf-8")
    (root / "contract.spec.ts").write_text("buildOpenApiDocument();\n", encoding="utf-8")
    (root / "openapi-contracts.json").write_text(
        json.dumps({
            "operations": [
                {
                    "method": "post",
                    "path": path,
                    "source": "controller.ts",
                    "handler": "register",
                    "required_statuses": list(required_statuses),
                    "contract_test": "contract.spec.ts",
                }
            ]
        }),
        encoding="utf-8",
    )
    if document_responses is not None:
        (root / "openapi.json").write_text(
            json.dumps({"paths": {path: {"post": {"responses": document_responses}}}}),
            encoding="utf-8",
        )


class VerifyOpenApiContractTest(unittest.TestCase):
    def run_checker(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECKER), str(root), *extra],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )

    def test_rejects_when_generated_document_is_missing_a_required_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_fixture(root, document_responses={"201": {}})
            result = self.run_checker(root)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("[400, 409]", result.stdout)

    def test_accepts_when_generated_document_has_every_required_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_fixture(root, document_responses={"201": {}, "400": {}, "409": {}, "429": {}})
            result = self.run_checker(root)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_reformatting_the_source_file_does_not_change_the_result(self) -> None:
        """The whole point of verifying against the generated document: decorator
        formatting/line-wrapping in the source is irrelevant to the check."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_fixture(root, document_responses={"201": {}, "400": {}, "409": {}})
            before = self.run_checker(root)
            (root / "controller.ts").write_text(
                "class Controller {\n\n\n  // reformatted, decorators moved around, whitespace changed\n\n}\n",
                encoding="utf-8",
            )
            after = self.run_checker(root)
            self.assertEqual(before.returncode, after.returncode)
            self.assertEqual(before.returncode, 0, before.stdout)

    def test_path_param_syntax_is_converted_for_document_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_fixture(root, path="/api/v1/accounts/:id", document_responses=None)
            (root / "openapi.json").write_text(
                json.dumps({"paths": {"/api/v1/accounts/{id}": {"post": {"responses": {"201": {}, "400": {}, "409": {}}}}}}),
                encoding="utf-8",
            )
            result = self.run_checker(root)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_generated_document_fails_with_actionable_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_fixture(root, document_responses=None)
            result = self.run_checker(root)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("npm run export:openapi", result.stdout)

    def test_document_flag_overrides_default_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_fixture(root, document_responses=None)
            custom_document = root / "custom-openapi.json"
            custom_document.write_text(
                json.dumps({"paths": {"/api/v1/auth/register": {"post": {"responses": {"201": {}, "400": {}, "409": {}}}}}}),
                encoding="utf-8",
            )
            result = self.run_checker(root, "--document", str(custom_document))
            self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
