import asyncio
import unittest

from kaiwa_poc.coach import RuleBasedCoach, _extract_json, _validate_report
from kaiwa_poc.domain import SessionRuntime
from kaiwa_poc.scenario_catalog import ScenarioCatalog


class CoachTests(unittest.TestCase):
    def test_extract_json_accepts_fenced_local_model_output(self) -> None:
        self.assertEqual({"ok": True}, _extract_json("```json\n{\"ok\": true}\n```"))

    def test_rule_fallback_marks_its_limitations(self) -> None:
        scenario = ScenarioCatalog.load().get("lunch_with_colleague_n4")
        session = SessionRuntime.create(
            user_id="u-1", scenario=scenario, feedback_mode="delayed"
        )
        session.add_turn("user", "昨日、会社へ行きません。")
        report = asyncio.run(RuleBasedCoach().assess(session))
        self.assertEqual("grammar", report["corrections"][0]["category"])
        self.assertIn("không phải bộ chấm", report["limitations"][0])

    def test_report_validation_rejects_missing_evidence_sections(self) -> None:
        with self.assertRaises(ValueError):
            _validate_report({"summary_vi": "incomplete"})


if __name__ == "__main__":
    unittest.main()
