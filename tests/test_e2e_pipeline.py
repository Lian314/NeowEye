"""
End-to-End Integration Tests for NeowEye tactical and macro solver pipeline.
Covers:
1. Silent Poison stacking, Catalyst, and lethal turn-end damage cancellation.
2. Defect Orb evoking (Dualcast), Focus scaling, and turn-end Frost/Lightning passives.
3. Relic timings: Pen Nib 10th attack 2x multiplier and Orichalcum turn-end block.
4. CommBridge protocol schema sanitization and resilient default injection.
5. MacroAdvisor FallbackExpertEngine takeover on low confidence.
"""
import unittest
from combat_solver import CombatSolver, SimMonster, SimPlayer
from comm_bridge import sanitize_game_state
from macro_advisor import MacroAdvisor, FallbackExpertEngine
from card_db import resolve_card_info

class TestE2EPipeline(unittest.TestCase):
    def setUp(self):
        self.solver = CombatSolver()

    def test_silent_poison_lethal_pipeline(self):
        """
        Monster has 20 HP and is attacking for 18 damage!
        Player has Deadly Poison+ (7 poison, cost 1) and Catalyst+ (triple poison, cost 1).
        7 * 3 = 21 poison.
        Turn end poison tick deals 21 damage -> Monster killed -> 18 damage attack cancelled!
        Projected HP loss MUST be 0!
        """
        combat_state = {
            "player": {
                "current_hp": 70,
                "max_hp": 70,
                "block": 0,
                "energy": 3,
                "powers": [],
                "relics": []
            },
            "monsters": [
                {
                    "name": "Gremlin Nob",
                    "current_hp": 20,
                    "max_hp": 85,
                    "block": 0,
                    "intent": "ATTACK",
                    "move_adjusted_damage": 18,
                    "move_hits": 1,
                    "is_gone": False,
                    "half_dead": False,
                    "powers": []
                }
            ],
            "hand": [
                {"id": "Deadly Poison", "name": "Deadly Poison+", "cost": 1, "type": "SKILL", "upgraded": True},
                {"id": "Catalyst", "name": "Catalyst+", "cost": 1, "type": "SKILL", "upgraded": True}
            ]
        }

        plan = self.solver.solve(combat_state)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.monsters_killed, 1)
        self.assertEqual(plan.projected_incoming_damage, 0)
        self.assertEqual(plan.projected_hp_loss, 0)
        self.assertIn("回合末毒伤", plan.end_of_turn_forecast)

    def test_defect_orb_evoke_and_passive_pipeline(self):
        """
        Defect with Focus = 2 and a Lightning orb in slot.
        Cultist has 18 HP and is attacking for 12 damage.
        Player plays Dualcast (evokes Lightning twice: (8+2)*2 = 20 damage).
        Cultist dies immediately -> incoming attack cancelled -> 0 HP loss.
        """
        combat_state = {
            "player": {
                "current_hp": 75,
                "max_hp": 75,
                "block": 0,
                "energy": 3,
                "powers": [{"id": "Focus", "amount": 2}],
                "orbs": [{"name": "Lightning", "evoke_amount": 8, "passive_amount": 3}],
                "relics": []
            },
            "monsters": [
                {
                    "name": "Cultist",
                    "current_hp": 18,
                    "max_hp": 50,
                    "block": 0,
                    "intent": "ATTACK",
                    "move_adjusted_damage": 12,
                    "move_hits": 1,
                    "is_gone": False,
                    "half_dead": False,
                    "powers": []
                }
            ],
            "hand": [
                {"id": "Dualcast", "name": "Dualcast", "cost": 1, "type": "SKILL", "upgraded": False}
            ]
        }

        plan = self.solver.solve(combat_state)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.monsters_killed, 1)
        self.assertEqual(plan.projected_incoming_damage, 0)
        self.assertEqual(plan.projected_hp_loss, 0)

    def test_relic_pen_nib_and_orichalcum_timing(self):
        """
        Player has Pen Nib at 9 count and Orichalcum.
        Hand has Strike (6 damage).
        Playing Strike triggers Pen Nib 10th attack (6 * 2 = 12 damage) and resets counter to 0.
        At turn end, with 0 block, Orichalcum grants +6 block.
        Incoming 6 attack is fully absorbed by Orichalcum block -> 0 HP loss.
        """
        combat_state = {
            "player": {
                "current_hp": 80,
                "max_hp": 80,
                "block": 0,
                "energy": 3,
                "powers": [{"id": "Pen Nib", "amount": 9}],
                "relics": [{"id": "Pen Nib", "counter": 9}, {"id": "Orichalcum"}]
            },
            "monsters": [
                {
                    "name": "Jaw Worm",
                    "current_hp": 40,
                    "max_hp": 40,
                    "block": 0,
                    "intent": "ATTACK",
                    "move_adjusted_damage": 6,
                    "move_hits": 1,
                    "is_gone": False,
                    "half_dead": False,
                    "powers": []
                }
            ],
            "hand": [
                {"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK", "upgraded": False}
            ]
        }

        plan = self.solver.solve(combat_state)
        self.assertIsNotNone(plan)
        # Pen Nib doubled damage
        self.assertEqual(plan.total_damage_dealt, 12)
        # Orichalcum absorbed 6 incoming damage
        self.assertEqual(plan.projected_block, 6)
        self.assertEqual(plan.projected_hp_loss, 0)

    def test_comm_bridge_schema_sanitization(self):
        """Ensures corrupted or missing fields in CommMod JSON are sanitized safely."""
        malformed_raw = {
            "game_state": {
                "floor": "not_an_int",
                "combat_state": {
                    "player": None,
                    "monsters": [None, {"name": "BuggyMonster"}],
                    "hand": "invalid_string"
                }
            }
        }

        sanitized = sanitize_game_state(malformed_raw)
        gs = sanitized["game_state"]
        cs = gs["combat_state"]

        self.assertIsInstance(cs["player"], dict)
        self.assertEqual(cs["player"]["energy"], 3)
        self.assertEqual(cs["player"]["block"], 0)
        self.assertIsInstance(cs["monsters"], list)
        self.assertEqual(len(cs["monsters"]), 1)
        self.assertEqual(cs["monsters"][0]["name"], "BuggyMonster")
        self.assertIsInstance(cs["hand"], list)
        self.assertEqual(len(cs["hand"]), 0)

    def test_macro_advisor_low_confidence_fallback(self):
        """Tests that MacroAdvisor switches to FallbackExpertEngine when model confidence is low."""
        class MockLowConfLaya:
            def predict(self, state, questions):
                return {
                    "answers": {
                        "card_choice": {"choice": "NonsenseCard", "confidence": 0.12},
                        "path_choice": {"choice": "InvalidPath", "confidence": 0.20},
                        "rest_action": {"choice": "InvalidAction", "confidence": 0.15}
                    }
                }

        advisor = MacroAdvisor(laya_client=MockLowConfLaya())

        # Test Card Reward Fallback
        game_state_reward = {
            "screen_type": "CARD_REWARD",
            "screen_state": {
                "cards": [
                    {"id": "Corruption", "name": "Corruption", "cost": 3},
                    {"id": "Strike_R", "name": "Strike", "cost": 1}
                ]
            },
            "class": "IRONCLAD",
            "floor": 5,
            "deck": [{"name": "Strike"}, {"name": "Defend"}],
            "relics": []
        }
        dec_reward = advisor.evaluate_card_reward(game_state_reward)
        self.assertEqual(dec_reward.recommended_choice, "Corruption")
        self.assertIn("专家规则接管", dec_reward.tactical_note)

        # Test Rest Site Fallback (low HP -> Rest)
        game_state_rest = {
            "screen_type": "REST",
            "class": "IRONCLAD",
            "current_hp": 20,
            "max_hp": 80
        }
        dec_rest = advisor.evaluate_rest_site(game_state_rest)
        self.assertEqual(dec_rest.recommended_choice, "Rest")
        self.assertIn("专家规则接管", dec_rest.tactical_note)

if __name__ == "__main__":
    unittest.main()
