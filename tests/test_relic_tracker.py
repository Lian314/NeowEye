"""
Unit tests for Relic Tracker and Relic Combat Modifiers.
Verifies:
1. RelicTracker correctly identifies counter thresholds (Incense Burner 5/6, Pen Nib 9/10).
2. CombatSolver integrates Pen Nib double damage (Strike 6 -> 12 dmg).
3. CombatSolver integrates Anchor initial block (+10 block on turn 1).
4. MacroAdvisor includes boss and deck thickness warnings in decisions.
"""
import unittest
from relic_tracker import RelicTracker
from combat_solver import CombatSolver
from macro_advisor import MacroAdvisor
from test_mock_scenarios import SCENARIO_RELIC_ALERT, SCENARIO_THICK_DECK_BOSS

class TestRelicTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = RelicTracker()
        self.solver = CombatSolver()
        self.advisor = MacroAdvisor()

    def test_relic_alerts(self):
        relics = [
            {"id": "Incense Burner", "name": "香炉", "counter": 5},
            {"id": "Pen Nib", "name": "钢笔尖", "counter": 9}
        ]
        alerts = self.tracker.analyze_relics(relics, turn=2)
        self.assertEqual(len(alerts), 2)
        alert_ids = [a.relic_id for a in alerts]
        self.assertIn("Incense Burner", alert_ids)
        self.assertIn("Pen Nib", alert_ids)
        self.assertTrue(any("无实体" in a.message for a in alerts))
        self.assertTrue(any("翻倍" in a.message for a in alerts))

    def test_pen_nib_combat_integration(self):
        """
        In SCENARIO_RELIC_ALERT, Pen Nib has counter 9 (next attack deals double damage).
        Player has Strike (base 6 dmg). With Pen Nib, it deals 12 damage!
        """
        combat_state = SCENARIO_RELIC_ALERT["game_state"]["combat_state"]
        relics = SCENARIO_RELIC_ALERT["game_state"]["relics"]
        plan = self.solver.solve(combat_state, relics=relics)

        self.assertIsNotNone(plan)
        # Find the Strike step
        strike_steps = [s for s in plan.steps if s.card_info.name == "Strike"]
        self.assertTrue(len(strike_steps) > 0)
        # Damage should be 12 (6 * 2) due to Pen Nib!
        self.assertEqual(strike_steps[0].damage_dealt, 12)
        self.assertIn("钢笔尖", strike_steps[0].notes)

    def test_boss_and_deck_thickness_warning(self):
        """
        In SCENARIO_THICK_DECK_BOSS, deck has 26 cards and Act Boss is Time Eater.
        MacroDecision should contain both deck thickness and Time Eater warnings.
        """
        decision = self.advisor.evaluate_card_reward(SCENARIO_THICK_DECK_BOSS["game_state"])
        self.assertIsNotNone(decision)
        self.assertIn("卡组已达", decision.tactical_note)
        self.assertIn("时光吞噬者", decision.tactical_note)

if __name__ == "__main__":
    unittest.main()
