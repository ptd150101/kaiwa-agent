import tempfile
import unittest
from pathlib import Path

from kaiwa_poc.domain import SessionRuntime
from kaiwa_poc.repository import SessionRepository
from kaiwa_poc.scenario_catalog import ScenarioCatalog


class RepositoryTests(unittest.TestCase):
    def test_report_updates_learner_profile_once(self) -> None:
        scenario = ScenarioCatalog.load().get("job_interview_n3")
        session = SessionRuntime.create(
            user_id="learner-1", scenario=scenario, feedback_mode="delayed"
        )
        session.add_turn("user", "ファン・ティエン・ダットと申します。")
        session.finish()
        report = {
            "corrections": [
                {"category": "politeness", "original": "x", "corrected": "y"}
            ]
        }

        with tempfile.TemporaryDirectory() as directory:
            repository = SessionRepository(Path(directory) / "test.db")
            repository.save_session(session)
            profile = repository.save_report_and_update_profile(session, report)
            latest = repository.latest_report("learner-1")

        self.assertEqual(1, profile.completed_sessions)
        self.assertEqual(1, profile.recurring_issues["politeness"])
        self.assertIsNotNone(latest)
        self.assertEqual(session.session_id, latest["session_id"])


if __name__ == "__main__":
    unittest.main()

