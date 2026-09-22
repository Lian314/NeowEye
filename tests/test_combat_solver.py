"""
Unit tests for In-Combat Mathematical Optimizer (CombatSolver).
Verifies:
1. Minimizing HP loss (defending against incoming attacks)
2. Lethal recognition (killing an attacking enemy cancels its attack, achieving 0 HP loss)
3. Synergistic timing (applying Vulnerable before Attack increases damage)
4. Multi-enemy targeting and threat elimination
"""
import unittest
from combat_solver import CombatSolver
from test_mock_scenarios import (
    SCENARIO_CULTIST_ATTACKING,
    SCENARIO_LETHAL_CULTIST,
    SCENARIO_MULTI_SLIMES
)

class TestCombatSolver(unittest.TestCase):
    def setUp(self):
        self.solver = CombatSolver()

    def test_cultist_defense_minimization(self):
        """
        Cultist attacks for 12. Player has 3 energy.
        Hand has Bash (cost 2), Defend (cost 1, 5 block), Defend (cost 1, 5 block), Strike (cost 1, 6 dmg).
        Optimal line should play both Defends (10 block) + 1 Strike, taking only 2 damage,
        rather than Bash + Strike which would take 12 damage.
        """
        combat_state = SCENARIO_CULTIST_ATTACKING["game_state"]["combat_state"]
        plan = self.solver.solve(combat_state)

        self.assertIsNotNone(plan)
        self.assertTrue(len(plan.steps) > 0)
        # Should have at least 10 block gained
        self.assertGreaterEqual(plan.total_block_gained, 10)
        # Projected HP loss should be 2 (12 - 10 block)
        self.assertEqual(plan.projected_hp_loss, 2)
        # Remaining energy should be 0
        self.assertEqual(plan.remaining_energy, 0)

    def test_lethal_cancels_enemy_attack(self):
        """
        Cultist has 15 HP and is attacking for 15 damage!
        Player has Bash (8 dmg + 2 vuln, cost 2) and Strike (6 dmg, cost 1).
        Playing Bash (8 dmg, Cultist at 7 HP + Vuln) then Strike (6 * 1.5 = 9 dmg, Cultist at 0 HP).
        Cultist dies before attacking -> incoming damage drops from 15 to 0!
        Projected HP loss MUST be 0!
        """
        combat_state = SCENARIO_LETHAL_CULTIST["game_state"]["combat_state"]
        plan = self.solver.solve(combat_state)

        self.assertIsNotNone(plan)
        self.assertEqual(plan.monsters_killed, 1)
        self.assertEqual(plan.projected_incoming_damage, 0)
        self.assertEqual(plan.projected_hp_loss, 0)

        # Check step sequence: Bash should come before Strike
        card_names = [s.card_info.name for s in plan.steps]
        self.assertEqual(card_names[0], "Bash")
        self.assertEqual(card_names[1], "Strike")

    def test_multi_enemy_threat_elimination(self):
        """
        Acid Slime M (HP 8, attacking for 8 dmg).
        Acid Slime S (HP 12, debuffing).
        Player hand: Twin Strike (5x2 = 10 dmg, cost 1), Defend (5 block, cost 1), Strike (6 dmg, cost 1).
        Playing Twin Strike on Acid Slime M eliminates it and its 8 incoming damage!
        """
        combat_state = SCENARIO_MULTI_SLIMES["game_state"]["combat_state"]
        plan = self.solver.solve(combat_state)

        self.assertIsNotNone(plan)
        # Acid Slime M should be killed
        self.assertGreaterEqual(plan.monsters_killed, 1)
        # Incoming damage from the attacker should be eliminated
        self.assertEqual(plan.projected_incoming_damage, 0)
        self.assertEqual(plan.projected_hp_loss, 0)

if __name__ == "__main__":
    unittest.main()
