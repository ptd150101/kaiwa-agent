import unittest

from kaiwa_poc.domain import SessionRuntime
from kaiwa_poc.scenario_catalog import ScenarioCatalog, ScenarioNotFoundError


class ScenarioDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = ScenarioCatalog.load()

    def test_catalog_contains_four_seed_scenarios(self) -> None:
        self.assertEqual(4, len(self.catalog.list()))

    def test_public_role_card_does_not_leak_private_data(self) -> None:
        scenario = self.catalog.get("lunch_with_colleague_n4")
        card = scenario.public_role_card()
        self.assertIn("Nhân viên người Việt", card)
        self.assertNotIn("Không ăn được đồ sống", card)
        self.assertNotIn("Quán được chọn đầu tiên đã hết chỗ", card)

    def test_unknown_scenario_lists_choices(self) -> None:
        with self.assertRaises(ScenarioNotFoundError) as captured:
            self.catalog.get("missing")
        self.assertIn("lunch_with_colleague_n4", str(captured.exception))

    def test_session_deduplicates_consecutive_frame_replays(self) -> None:
        scenario = self.catalog.get("supermarket_n5")
        session = SessionRuntime.create(
            user_id="test-user", scenario=scenario, feedback_mode="delayed"
        )
        session.add_turn("user", "  たまごは   どこですか。 ")
        session.add_turn("user", "たまごは どこですか。")
        self.assertEqual(1, len(session.turns))
        self.assertEqual("たまごは どこですか。", session.turns[0].text)


if __name__ == "__main__":
    unittest.main()

