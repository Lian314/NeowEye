"""
Unit tests for Deck Tracker and Draw Probability Engine.
Verifies:
1. Hypergeometric probability calculation correctness and edge case handling.
2. Accurate categorization of Draw, Discard, and Exhaust piles.
3. Tactical advice generation based on deck composition and draw probabilities.
"""
import unittest
import math
from deck_tracker import DeckTracker

class TestDeckTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = DeckTracker()

    def test_hypergeometric_prob_calculation(self):
        # Case 1: N=10, K=2, n=5
        # Total ways = C(10, 5) = 252
        # Ways with no target = C(8, 5) = 56
        # Prob = 1 - (56 / 252) = 196 / 252 ≈ 0.7777777777777778
        prob = self.tracker._calc_hypergeometric_prob(N=10, K=2, n=5)
        self.assertAlmostEqual(prob, 196 / 252, places=5)

        # Case 2: All cards are target (K == N) -> 1.0
        self.assertEqual(self.tracker._calc_hypergeometric_prob(N=10, K=10, n=5), 1.0)

        # Case 3: No target cards (K == 0) -> 0.0
        self.assertEqual(self.tracker._calc_hypergeometric_prob(N=10, K=0, n=5), 0.0)

        # Case 4: Drawing all cards (n >= N) -> 1.0 if K > 0 else 0.0
        self.assertEqual(self.tracker._calc_hypergeometric_prob(N=5, K=1, n=5), 1.0)
        self.assertEqual(self.tracker._calc_hypergeometric_prob(N=5, K=0, n=5), 0.0)

        # Case 5: Empty pile (N == 0)
        self.assertEqual(self.tracker._calc_hypergeometric_prob(N=0, K=0, n=5), 0.0)

    def test_analyze_deck_breakdown(self):
        combat_state = {
            "draw_pile": [
                {"id": "Strike_R", "name": "打击", "type": "ATTACK", "cost": 1},
                {"id": "Strike_R", "name": "打击", "type": "ATTACK", "cost": 1},
                {"id": "Defend_R", "name": "防御", "type": "SKILL", "cost": 1, "block": 5},
                {"id": "Demon Form", "name": "恶魔形态", "type": "POWER", "cost": 3},
                {"id": "Dazed", "name": "晕眩", "type": "STATUS", "cost": -2}
            ],
            "discard_pile": [
                {"id": "Bash", "name": "痛击", "type": "ATTACK", "cost": 2}
            ],
            "exhaust_pile": [
                {"id": "AscendersBane", "name": "进阶之灾", "type": "CURSE", "cost": -2}
            ]
        }

        stats = self.tracker.analyze_deck(combat_state, draw_count_next_turn=5)

        self.assertEqual(stats.total_draw_count, 5)
        self.assertEqual(stats.total_discard_count, 1)
        self.assertEqual(stats.total_exhaust_count, 1)

        self.assertEqual(stats.draw_attacks, 2)
        self.assertEqual(stats.draw_skills, 1)
        self.assertEqual(stats.draw_powers, 1)
        self.assertEqual(stats.draw_curses_status, 1)
        self.assertEqual(stats.draw_block_cards, 1)

        # Drawing 5 from 5 means 100% chance for each present card type
        self.assertEqual(stats.prob_draw_block, 1.0)
        self.assertEqual(stats.prob_draw_attack, 1.0)
        self.assertEqual(stats.prob_draw_curse_status, 1.0)

        self.assertIn("打击", stats.draw_pile_cards)
        self.assertIn("痛击", stats.discard_pile_cards)
        self.assertIn("进阶之灾", stats.exhaust_pile_cards)

    def test_tactical_advice_generation(self):
        # Scenario: Low block probability
        combat_state = {
            "draw_pile": [
                {"id": "Strike_R", "name": "打击", "type": "ATTACK"},
                {"id": "Strike_R", "name": "打击", "type": "ATTACK"},
                {"id": "Strike_R", "name": "打击", "type": "ATTACK"},
                {"id": "Strike_R", "name": "打击", "type": "ATTACK"},
                {"id": "Strike_R", "name": "打击", "type": "ATTACK"},
                {"id": "Strike_R", "name": "打击", "type": "ATTACK"},
                {"id": "Strike_R", "name": "打击", "type": "ATTACK"},
                {"id": "Strike_R", "name": "打击", "type": "ATTACK"},
                {"id": "Strike_R", "name": "打击", "type": "ATTACK"},
                {"id": "Defend_R", "name": "防御", "type": "SKILL", "block": 5},
                {"id": "Dazed", "name": "晕眩", "type": "STATUS"},
                {"id": "Dazed", "name": "晕眩", "type": "STATUS"},
                {"id": "Dazed", "name": "晕眩", "type": "STATUS"},
                {"id": "Dazed", "name": "晕眩", "type": "STATUS"},
                {"id": "Dazed", "name": "晕眩", "type": "STATUS"},
                {"id": "Dazed", "name": "晕眩", "type": "STATUS"},
            ],
            "discard_pile": [],
            "exhaust_pile": []
        }
        stats = self.tracker.analyze_deck(combat_state, draw_count_next_turn=5)

        # N=16, draw_blocks=1. prob = 5/16 = 31.25% < 40%
        self.assertLess(stats.prob_draw_block, 0.40)
        self.assertIn("下回合抽到格挡牌概率仅", stats.tactical_advice)

        # Curses = 6. prob of drawing at least 1 curse: 1 - C(10, 5)/C(16, 5) = 1 - 252/4368 ≈ 94.2%
        self.assertGreater(stats.prob_draw_curse_status, 0.50)
        self.assertIn("防鬼抽", stats.tactical_advice)

if __name__ == "__main__":
    unittest.main()
