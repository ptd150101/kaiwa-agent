import unittest

from kaiwa_poc.domain import LearnerProfile
from kaiwa_poc.prompts import build_kaiwa_system_prompt
from kaiwa_poc.scenario_catalog import ScenarioCatalog


class PromptTests(unittest.TestCase):
    def test_private_prompt_contains_both_roles_and_hidden_information(self) -> None:
        scenario = ScenarioCatalog.load().get("lunch_with_colleague_n4")
        profile = LearnerProfile(user_id="u-1", level="N4")
        prompt = build_kaiwa_system_prompt(scenario, profile)
        self.assertIn("VAI NGƯỜI HỌC", prompt)
        self.assertIn("VAI CỦA BẠN", prompt)
        self.assertIn("Không ăn được đồ sống", prompt)
        self.assertIn("chỉ nói lời thoại tiếng Nhật", prompt)


if __name__ == "__main__":
    unittest.main()

