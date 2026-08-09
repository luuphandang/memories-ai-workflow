from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "skills" / "verify-openapi-contract" / "scripts" / "check_openapi_contract.py"


class VerifyOpenApiContractTest(unittest.TestCase):
    def run_checker(self, statuses: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "controller.ts"
            source.write_text(
                f"""class Controller {{
  @Post('register')
  {statuses}
  async register(): Promise<void> {{}}
}}
""",
                encoding="utf-8",
            )
            (root / "contract.spec.ts").write_text("buildOpenApiDocument();\n", encoding="utf-8")
            (root / "openapi-contracts.json").write_text(
                json.dumps(
                    {
                        "operations": [
                            {
                                "method": "post",
                                "path": "/api/v1/auth/register",
                                "source": "controller.ts",
                                "handler": "register",
                                "required_statuses": [201, 400, 409],
                                "contract_test": "contract.spec.ts",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.run(
                [sys.executable, str(CHECKER), str(root)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

    def test_rejects_runtime_errors_missing_from_swagger(self) -> None:
        result = self.run_checker("@ApiResponse({ status: HttpStatus.CREATED })")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[400, 409]", result.stdout)

    def test_accepts_complete_explicit_response_contract(self) -> None:
        result = self.run_checker(
            "\n  ".join(
                [
                    "@ApiResponse({ status: HttpStatus.CREATED })",
                    "@ApiResponse({ status: HttpStatus.BAD_REQUEST })",
                    "@ApiResponse({ status: 409 })",
                ]
            )
        )
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
