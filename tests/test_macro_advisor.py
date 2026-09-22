"""
Unit tests for Macro Advisor (macro_advisor.py).
Verifies:
1. Card reward evaluation via Laya model
2. Map routing evaluation via Laya model
3. Rest site evaluation via Laya model
"""
import unittest
from macro_advisor import MacroAdvisor
from test_mock_scenarios import (
    SCENARIO_CARD_REWARD,
    SCENARIO_MAP_ROUTING,
    SCENARIO_REST_SITE
)

class TestMacroAdvisor(unittest.TestCase):
    def setUp(self):
        self.advisor = MacroAdvisor()

    def test_card_reward_evaluation(self):
        decision = self.advisor.evaluate_card_reward(SCENARIO_CARD_REWARD["game_state"])
        self.assertEqual(decision.decision_type, "CARD_REWARD")
        self.assertTrue(len(decision.recommended_choice) > 0)
        self.assertGreaterEqual(decision.confidence, 0.0)
        self.assertGreaterEqual(len(decision.choice_probabilities), 2)
        if decision.noul_probability is not None:
            self.assertGreaterEqual(decision.noul_probability, 0.0)
            self.assertLessEqual(decision.noul_probability, 1.0)

    def test_map_routing_evaluation(self):
        decision = self.advisor.evaluate_map_routing(SCENARIO_MAP_ROUTING["game_state"])
        self.assertEqual(decision.decision_type, "MAP_ROUTING")
        self.assertTrue(len(decision.recommended_choice) > 0)

    def test_rest_site_evaluation(self):
        decision = self.advisor.evaluate_rest_site(SCENARIO_REST_SITE["game_state"])
        self.assertEqual(decision.decision_type, "REST_SITE")
        self.assertIn(decision.recommended_choice, ["Smith", "Rest"])

if __name__ == "__main__":
    unittest.main()
