"""
UI Integration test for Overlay HUD and Mock Scenarios.
Verifies all mock scenarios render without error in OverlayHUD.
"""
import unittest
from overlay_hud import OverlayHUD
from combat_solver import CombatSolver
from macro_advisor import MacroAdvisor
from test_mock_scenarios import MOCK_SCENARIOS

class TestOverlayHUD(unittest.TestCase):
    def test_hud_rendering_all_scenarios(self):
        hud = OverlayHUD()
        combat_solver = CombatSolver()
        macro_advisor = MacroAdvisor()

        # Iterate over all mock scenarios and render them
        for name, data in MOCK_SCENARIOS.items():
            game_state = data.get("game_state", {})
            screen_type = game_state.get("screen_type", "NONE")
            combat_state = game_state.get("combat_state")

            # Update game info
            hud.update_game_info(
                game_state.get("class", "IRONCLAD"),
                game_state.get("act", 1),
                game_state.get("floor", 1),
                game_state.get("current_hp", 80),
                game_state.get("max_hp", 80),
                3 if combat_state else 0,
                game_state.get("gold", 99)
            )

            if combat_state:
                plan = combat_solver.solve(combat_state)
                hud.show_combat_plan(plan)
            elif screen_type == "CARD_REWARD":
                decision = macro_advisor.evaluate_card_reward(game_state)
                hud.show_macro_decision(decision)
            elif screen_type == "MAP":
                decision = macro_advisor.evaluate_map_routing(game_state)
                hud.show_macro_decision(decision)
            elif screen_type == "REST":
                decision = macro_advisor.evaluate_rest_site(game_state)
                hud.show_macro_decision(decision)

            # Process pending tkinter events
            hud.root.update_idletasks()
            hud.root.update()

        hud.root.destroy()

if __name__ == "__main__":
    unittest.main()
