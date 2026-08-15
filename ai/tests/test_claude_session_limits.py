import runpy
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ClaudeSessionLimitTests(unittest.TestCase):
    def test_implementer_does_not_pass_a_max_turns_limit(self) -> None:
        source = (ROOT / "ai/bin/run-claude").read_text(encoding="utf-8")
        self.assertNotIn('"--max-turns"', source)
        self.assertNotIn("budget['max_turns']", source)

    def test_requirement_consolidation_does_not_pass_a_max_turns_limit(self) -> None:
        source = (ROOT / "ai/bin/consolidate-requirements").read_text(encoding="utf-8")
        self.assertNotIn('"--max-turns"', source)

    def test_allowed_rate_limit_event_is_not_an_interruption(self) -> None:
        module = runpy.run_path(str(ROOT / "ai/bin/run-claude"))
        classify_termination = module["classify_termination"]
        allowed = '{"type":"rate_limit_event","rate_limit_info":{"status":"allowed"}}\n{"type":"result","subtype":"success"}'
        rejected = '{"type":"rate_limit_event","rate_limit_info":{"status":"rejected"}}\n{"type":"result","subtype":"success"}'

        self.assertEqual(classify_termination(allowed)[0], "ok")
        self.assertEqual(classify_termination(rejected)[0], "usage_limit")

    def test_assistant_text_mentioning_rate_limit_is_not_misclassified(self) -> None:
        module = runpy.run_path(str(ROOT / "ai/bin/run-claude"))
        classify_termination = module["classify_termination"]
        output = (
            '{"type":"assistant","message":{"content":[{"type":"text",'
            '"text":"su dung global validation, error shape va rate limit hien huu"}]}}\n'
            '{"type":"result","subtype":"error_max_turns","errors":["Reached maximum number of turns (60)"]}'
        )

        category, detail = classify_termination(output)
        self.assertEqual(category, "turn_or_budget_cap")
        self.assertEqual(detail, "error_max_turns")

    def test_non_dict_json_line_does_not_crash_classification(self) -> None:
        module = runpy.run_path(str(ROOT / "ai/bin/run-claude"))
        classify_termination = module["classify_termination"]
        output = '42\nnull\n["not", "an", "event"]\n{"type":"result","subtype":"success"}'

        self.assertEqual(classify_termination(output), ("ok", "success"))

    def test_unstructured_output_falls_back_to_marker_match(self) -> None:
        module = runpy.run_path(str(ROOT / "ai/bin/run-claude"))
        classify_termination = module["classify_termination"]

        self.assertEqual(classify_termination("You have hit your session limit.")[0], "usage_limit")
        self.assertEqual(classify_termination("some random crash trace")[0], "unstructured")

    def test_structured_error_event_detects_session_limit(self) -> None:
        module = runpy.run_path(str(ROOT / "ai/bin/run-claude"))
        classify_termination = module["classify_termination"]
        output = '{"type":"error","session_id":"test-session","message":"You have hit your session limit"}'

        self.assertEqual(
            classify_termination(output),
            ("usage_limit", "structured error event marker match"),
        )

    def test_allowed_warning_rate_limit_status_is_not_a_block(self) -> None:
        module = runpy.run_path(str(ROOT / "ai/bin/run-claude"))
        classify_termination = module["classify_termination"]
        output = (
            '{"type":"rate_limit_event","rate_limit_info":{"status":"allowed_warning","utilization":0.95}}\n'
            '{"type":"result","subtype":"success"}'
        )

        self.assertEqual(classify_termination(output), ("ok", "success"))


if __name__ == "__main__":
    unittest.main()
