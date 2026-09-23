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

    def test_poison_ignores_enemy_block(self):
        """
        In Slay the Spire, Poison damage directly reduces HP and completely ignores Block!
        Enemy has 5 HP, 10 Block, 5 Poison, and is attacking for 10 damage.
        At turn end, 5 Poison deals 5 direct HP damage -> Enemy HP drops to 0 (lethal).
        Enemy dies -> attack cancelled -> 0 HP loss.
        """
        combat_state = {
            "player": {
                "current_hp": 50,
                "max_hp": 50,
                "block": 0,
                "energy": 0,
                "powers": [],
                "relics": []
            },
            "monsters": [
                {
                    "name": "Shelled Parasite",
                    "current_hp": 5,
                    "max_hp": 70,
                    "block": 10,
                    "intent": "ATTACK",
                    "move_adjusted_damage": 10,
                    "move_hits": 1,
                    "is_gone": False,
                    "half_dead": False,
                    "powers": [{"id": "Poison", "amount": 5}]
                }
            ],
            "hand": []
        }

        # Monsters powers parsed: "powers": [{"id": "Poison", "amount": 5}]
        # Let's ensure SimMonster gets poison=5
        plan = self.solver.solve(combat_state)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.monsters_killed, 1)
        self.assertEqual(plan.projected_incoming_damage, 0)
        self.assertEqual(plan.projected_hp_loss, 0)

    def test_comm_bridge_type_coercion_resilience(self):
        """
        Validates that corrupt numeric values (e.g. 'bad' for hp, '100' string for max_hp)
        are coerced to integers safely and do not cause TypeError during math calculations.
        """
        corrupted_raw = {
            "game_state": {
                "floor": "12",
                "act": "2",
                "current_hp": "corrupted_val",
                "max_hp": "75",
                "gold": None,
                "combat_state": {
                    "player": {
                        "current_hp": "invalid_hp",
                        "max_hp": "75",
                        "block": "15",
                        "energy": "3"
                    },
                    "monsters": [
                        {
                            "name": "CorruptedMonster",
                            "current_hp": "25",
                            "max_hp": "50",
                            "block": "bad_block",
                            "move_adjusted_damage": "12",
                            "move_hits": "2"
                        }
                    ]
                }
            }
        }

        sanitized = sanitize_game_state(corrupted_raw)
        gs = sanitized["game_state"]
        cs = gs["combat_state"]
        player = cs["player"]
        monster = cs["monsters"][0]

        self.assertIsInstance(gs["floor"], int)
        self.assertEqual(gs["floor"], 12)
        self.assertEqual(gs["current_hp"], 80)  # Default on error
        self.assertEqual(gs["max_hp"], 75)
        self.assertEqual(player["current_hp"], 80)
        self.assertEqual(player["block"], 15)
        self.assertEqual(player["energy"], 3)
        self.assertEqual(monster["current_hp"], 25)
        self.assertEqual(monster["block"], 0)
        self.assertEqual(monster["move_adjusted_damage"], 12)
        self.assertEqual(monster["move_hits"], 2)

        # Ensure hp division does not throw TypeError
        hp_pct = player["current_hp"] / player["max_hp"]
        self.assertIsInstance(hp_pct, float)

    def test_stdin_mode_does_not_inject_mock(self):
        """
        Ensures that when running in 'stdin' mode (e.g. launched by CommunicationMod),
        mock scenarios are NEVER injected, preventing misleading HUD overlays.
        """
        from main import SpireTacticalAssistant
        import unittest.mock as mock

        with mock.patch("main.EnvironmentDetector.auto_bind_communication_mod", return_value=(True, "")):
            with mock.patch("main.OverlayHUD") as mock_hud_cls:
                mock_hud = mock.MagicMock()
                mock_hud_cls.return_value = mock_hud
                assistant = SpireTacticalAssistant(mode="stdin")

                mock_select = mock.MagicMock()
                assistant.on_mock_scenario_selected = mock_select

                # Mock comm_bridge.start and hud.run
                with mock.patch.object(assistant.comm_bridge, "start"):
                    with mock.patch.object(assistant.hud, "run"):
                        assistant.start()

                mock_select.assert_not_called()

    def test_combat_state_non_dict_normalization(self):
        """
        Validates that if combat_state is not a dict (e.g. ['bad'] or 'bad_str'),
        sanitize_game_state sets it to None and main.on_game_state_received handles it
        without raising AttributeError.
        """
        from main import SpireTacticalAssistant
        import unittest.mock as mock

        malformed_raw = {
            "game_state": {
                "combat_state": ["bad_list_instead_of_dict"]
            }
        }
        sanitized = sanitize_game_state(malformed_raw)
        self.assertIsNone(sanitized["game_state"]["combat_state"])

        with mock.patch("main.EnvironmentDetector.auto_bind_communication_mod", return_value=(True, "")):
            with mock.patch("main.OverlayHUD") as mock_hud_cls:
                mock_hud = mock.MagicMock()
                mock_hud_cls.return_value = mock_hud
                assistant = SpireTacticalAssistant(mode="stdin")
                # Ensure no AttributeError is raised
                assistant.on_game_state_received(malformed_raw)

    def test_deep_field_type_coercion(self):
        """
        Validates that powers, orbs, relics, deck, and cards with malformed inner fields
        are coerced and filtered to safe, valid types.
        """
        raw = {
            "game_state": {
                "deck": [{"id": 123, "name": 456}, "invalid_card_string"],
                "relics": [{"id": "Pen Nib", "counter": "9"}, None],
                "combat_state": {
                    "player": {
                        "powers": [{"id": "Strength", "amount": "5"}, "invalid_power"],
                        "orbs": [{"name": "Lightning", "evoke_amount": "8"}, 123]
                    },
                    "monsters": [
                        {
                            "name": "Cultist",
                            "powers": [{"id": "Ritual", "amount": "3"}]
                        }
                    ],
                    "hand": [
                        {"id": "Strike_R", "cost": "1", "type": "ATTACK"}
                    ]
                }
            }
        }

        sanitized = sanitize_game_state(raw)
        gs = sanitized["game_state"]
        cs = gs["combat_state"]

        self.assertEqual(len(gs["deck"]), 1)
        self.assertEqual(gs["deck"][0]["id"], "123")
        self.assertEqual(len(gs["relics"]), 1)
        self.assertEqual(gs["relics"][0]["counter"], 9)

        player = cs["player"]
        self.assertEqual(len(player["powers"]), 1)
        self.assertEqual(player["powers"][0]["amount"], 5)
        self.assertEqual(len(player["orbs"]), 1)
        self.assertEqual(player["orbs"][0]["evoke_amount"], 8)

        monster = cs["monsters"][0]
        self.assertEqual(len(monster["powers"]), 1)
        self.assertEqual(monster["powers"][0]["amount"], 3)

        card = cs["hand"][0]
        self.assertEqual(card["cost"], 1)

    def test_socket_graceful_shutdown(self):
        """
        Ensures that CommBridge in socket mode unblocks and terminates cleanly
        when stop() is called, without hanging indefinitely on accept().
        """
        from comm_bridge import CommBridge
        from types import SimpleNamespace
        import time

        cfg = SimpleNamespace(mode="socket", socket_host="127.0.0.1", socket_port=29519, send_ready_on_start=False)
        bridge = CommBridge(config=cfg)
        bridge.start()
        time.sleep(0.1)
        self.assertTrue(bridge._running)

        bridge.stop()
        if bridge._thread:
            bridge._thread.join(timeout=2.0)
            self.assertFalse(bridge._thread.is_alive())

    def test_dynamic_draw_pile_expansion(self):
        """
        Player has 2 energy. Hand has Pommel Strike (9 dmg, draw 1, cost 1).
        Enemy has 15 HP and attacks for 15 damage.
        Draw pile has Strike_R (6 dmg, cost 1).
        Pommel Strike deals 9 dmg, draws Strike_R, which is then played for 6 dmg -> lethal!
        Attack cancelled -> 0 HP loss!
        """
        combat_state = {
            "player": {"current_hp": 80, "max_hp": 80, "block": 0, "energy": 2, "powers": [], "relics": []},
            "monsters": [{
                "name": "Cultist",
                "current_hp": 15,
                "max_hp": 50,
                "block": 0,
                "intent": "ATTACK",
                "move_adjusted_damage": 15,
                "move_hits": 1,
                "is_gone": False,
                "half_dead": False,
                "powers": []
            }],
            "hand": [{"id": "Pommel Strike", "name": "Pommel Strike", "cost": 1, "type": "ATTACK"}],
            "draw_pile": [{"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"}]
        }
        plan = self.solver.solve(combat_state)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.monsters_killed, 1)
        self.assertEqual(plan.projected_incoming_damage, 0)
        self.assertEqual(plan.projected_hp_loss, 0)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[0].card_info.name, "Pommel Strike")
        self.assertEqual(plan.steps[1].card_info.name, "Strike")

    def test_exhaust_feel_no_pain_and_dark_embrace(self):
        """
        Player has Feel No Pain (amount 1, +3 block on exhaust) and Dark Embrace (amount 1, +1 draw on exhaust).
        Player plays Seeing Red (cost 1, gain 2 energy, exhaust True).
        Seeing Red exhausts -> gives +3 block and draws Defend_R (5 block, cost 1).
        Player then plays Defend_R -> total block = 3 + 5 = 8 block!
        """
        combat_state = {
            "player": {
                "current_hp": 80, "max_hp": 80, "block": 2, "energy": 1,
                "powers": [{"id": "Feel No Pain", "amount": 1}, {"id": "Dark Embrace", "amount": 1}],
                "relics": []
            },
            "monsters": [{
                "name": "Jaw Worm", "current_hp": 40, "max_hp": 40, "block": 0,
                "intent": "ATTACK", "move_adjusted_damage": 8, "move_hits": 1,
                "is_gone": False, "half_dead": False, "powers": []
            }],
            "hand": [{"id": "Seeing Red", "name": "Seeing Red", "cost": 1, "type": "SKILL"}],
            "draw_pile": [{"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL"}]
        }
        plan = self.solver.solve(combat_state)
        self.assertIsNotNone(plan)
        self.assertGreaterEqual(plan.projected_block, 8)
        self.assertEqual(plan.projected_hp_loss, 0)

    def test_corruption_zero_cost_skills(self):
        """
        Player has Corruption power (Skills cost 0 and exhaust).
        Hand has Impervious (cost 2 -> 0) and Shrug It Off (cost 1 -> 0).
        Player only has 1 energy, yet can play both skills!
        """
        combat_state = {
            "player": {
                "current_hp": 80, "max_hp": 80, "block": 0, "energy": 1,
                "powers": [{"id": "Corruption", "amount": 1}],
                "relics": []
            },
            "monsters": [{
                "name": "Louse", "current_hp": 20, "max_hp": 20, "block": 0,
                "intent": "ATTACK", "move_adjusted_damage": 10, "move_hits": 1,
                "is_gone": False, "half_dead": False, "powers": []
            }],
            "hand": [
                {"id": "Impervious", "name": "Impervious", "cost": 2, "type": "SKILL"},
                {"id": "Shrug It Off", "name": "Shrug It Off", "cost": 1, "type": "SKILL"}
            ]
        }
        plan = self.solver.solve(combat_state)
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.steps), 2)
        # Impervious (30) + Shrug It Off (8) = 38 block
        self.assertGreaterEqual(plan.projected_block, 38)
        self.assertEqual(plan.projected_hp_loss, 0)

    def test_block_potion_prevents_damage(self):
        """A Block Potion should be considered when cards alone cannot block the attack."""
        combat_state = {
            "player": {"current_hp": 50, "max_hp": 50, "block": 0, "energy": 0, "powers": []},
            "monsters": [{
                "name": "Jaw Worm", "current_hp": 40, "max_hp": 40, "block": 0,
                "intent": "ATTACK", "move_adjusted_damage": 10, "move_hits": 1,
                "powers": []
            }],
            "hand": [],
            "potions": [{"id": "Block Potion", "name": "格挡药水", "amount": 12}],
        }
        plan = self.solver.solve(combat_state)
        self.assertEqual(plan.projected_hp_loss, 0)
        self.assertEqual(plan.projected_block, 12)
        self.assertEqual(plan.potion_uses, ["格挡药水"])

    def test_fire_potion_lethal_cancels_attack(self):
        """A Fire Potion should be able to kill an attacking enemy without energy."""
        combat_state = {
            "player": {"current_hp": 50, "max_hp": 50, "block": 0, "energy": 0, "powers": []},
            "monsters": [{
                "name": "Cultist", "current_hp": 20, "max_hp": 20, "block": 0,
                "intent": "ATTACK", "move_adjusted_damage": 15, "move_hits": 1,
                "powers": []
            }],
            "hand": [],
            "potions": [{"id": "Fire Potion", "name": "火焰药水", "amount": 20}],
        }
        plan = self.solver.solve(combat_state)
        self.assertEqual(plan.monsters_killed, 1)
        self.assertEqual(plan.projected_hp_loss, 0)
        self.assertEqual(plan.potion_uses, ["火焰药水"])

    def test_time_eater_stops_at_twelfth_card(self):
        """Time Eater must end the turn after the twelfth played card."""
        self.solver.config.max_search_depth = 20
        combat_state = {
            "player": {
                "current_hp": 80, "max_hp": 80, "block": 2, "energy": 1,
                "powers": [], "cards_played_this_turn": 0
            },
            "monsters": [{
                "id": "Time Eater", "name": "Time Eater", "current_hp": 999,
                "max_hp": 999, "block": 0, "intent": "ATTACK",
                "move_adjusted_damage": 0, "move_hits": 1, "powers": []
            }],
            "hand": [
                {"id": "Anger", "name": "Anger", "cost": 0, "type": "ATTACK"}
                for _ in range(13)
            ]
        }
        plan = self.solver.solve(combat_state)
        self.assertEqual(len(plan.steps), 12)
        self.assertIn("时光扭曲", plan.steps[-1].notes)
        self.assertIn("时光吞噬者", plan.end_of_turn_forecast)

    def test_awakened_one_curiosity_increases_damage(self):
        """Playing a Power against Awakened One grants it one Strength."""
        monster = SimMonster(
            index=0, id="Awakened One", name="Awakened One", current_hp=100,
            max_hp=100, block=0, intent="ATTACK", move_adjusted_damage=10,
            is_attacking=True
        )
        player = SimPlayer(current_hp=80, max_hp=80, block=0, energy=3)
        power = resolve_card_info({"id": "Demon Form", "name": "Demon Form", "cost": 3, "type": "POWER"})

        next_player, next_monsters, step, drawn, draw, discard = self.solver._simulate_play_card(
            player, [monster], 0, power, None
        )
        plan = self.solver._evaluate_state(next_player, next_monsters, [step], 10)
        self.assertEqual(next_monsters[0].awakened_one_bonus, 1)
        self.assertEqual(plan.projected_incoming_damage, 11)
        self.assertIn("觉醒者好奇", plan.end_of_turn_forecast)

    def test_awakened_one_curiosity_influences_dfs_choice(self):
        """The solver should prefer mitigation over an unnecessary Power card."""
        combat_state = {
            "player": {"current_hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "monsters": [{
                "id": "Awakened One", "name": "Awakened One", "current_hp": 100,
                "max_hp": 100, "block": 0, "intent": "ATTACK",
                "move_adjusted_damage": 10, "move_hits": 1, "powers": []
            }],
            "hand": [
                {"id": "Demon Form", "name": "Demon Form", "cost": 3, "type": "POWER"},
                {"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL"}
            ]
        }
        plan = self.solver.solve(combat_state)
        self.assertEqual(plan.projected_hp_loss, 5)
        self.assertEqual([step.card_info.name for step in plan.steps], ["Defend"])

    def test_corrupt_heart_beat_of_death_counts_card_damage(self):
        """Beat of Death must damage the player for each played card."""
        combat_state = {
            "player": {"current_hp": 80, "max_hp": 80, "block": 0, "energy": 1, "powers": []},
            "monsters": [{
                "id": "Corrupt Heart", "name": "Corrupt Heart", "current_hp": 6,
                "max_hp": 750, "block": 0, "intent": "ATTACK",
                "move_adjusted_damage": 10, "move_hits": 1, "powers": []
            }],
            "hand": [{"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"}]
        }
        plan = self.solver.solve(combat_state)
        self.assertEqual([step.card_info.name for step in plan.steps], ["Strike"])
        self.assertEqual(plan.projected_hp_loss, 1)
        self.assertIn("死之律动", plan.steps[0].notes)

    def test_corrupt_heart_invincible_caps_damage(self):
        """Invincible must cap effective damage dealt during the turn."""
        heart = SimMonster(
            index=0, id="Corrupt Heart", name="Corrupt Heart", current_hp=100,
            max_hp=750, block=0, intent="ATTACK", move_adjusted_damage=0,
            is_attacking=True, invincible_cap=5
        )
        player = SimPlayer(current_hp=80, max_hp=80, block=0, energy=3)
        strike = resolve_card_info({"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"})

        next_player, next_monsters, step, drawn, draw, discard = self.solver._simulate_play_card(
            player, [heart], 0, strike, 0
        )
        self.assertEqual(next_monsters[0].current_hp, 95)
        self.assertEqual(step.damage_dealt, 5)

    def test_enemy_artifact_negates_vulnerable(self):
        """
        Enemy has Artifact 1.
        Player plays Bash (8 dmg, 2 vuln).
        Artifact consumes the Vulnerable. Enemy takes 8 dmg, vuln remains 0.
        Subsequent Strike deals 6 dmg (not 6 * 1.5 = 9).
        """
        cultist = SimMonster(
            index=0, id="Cultist", name="Cultist", current_hp=30, max_hp=50, block=0,
            intent="ATTACK", move_adjusted_damage=10, is_attacking=True, artifact=1
        )
        player = SimPlayer(current_hp=80, max_hp=80, block=0, energy=3)
        bash = resolve_card_info({"id": "Bash", "name": "Bash", "cost": 2, "type": "ATTACK"})
        strike = resolve_card_info({"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"})

        # Play Bash
        p1, m1, s1, drawn, dp, dcp = self.solver._simulate_play_card(player, [cultist], 0, bash, 0)
        self.assertEqual(m1[0].artifact, 0)
        self.assertEqual(m1[0].vulnerable_turns, 0)
        self.assertEqual(m1[0].current_hp, 22)

        # Play Strike
        p2, m2, s2, drawn, dp, dcp = self.solver._simulate_play_card(p1, m1, 1, strike, 0)
        self.assertEqual(m2[0].current_hp, 16)  # 22 - 6 = 16 (no vuln multiplier)

    def test_enemy_curl_up_and_thorns(self):
        """
        Enemy has Curl Up 5 and Thorns 3.
        Player has 20 HP, 0 block.
        Player plays Strike (6 dmg).
        Enemy curls up (+5 block), absorbing 5 dmg, taking 1 dmg.
        Enemy Thorns deals 3 damage back to player (HP drops to 17).
        """
        louse = SimMonster(
            index=0, id="Louse", name="Louse", current_hp=15, max_hp=15, block=0,
            intent="ATTACK", move_adjusted_damage=5, is_attacking=True,
            curl_up=5, thorns=3
        )
        player = SimPlayer(current_hp=20, max_hp=20, block=0, energy=3)
        strike = resolve_card_info({"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"})

        p1, m1, s1, drawn, dp, dcp = self.solver._simulate_play_card(player, [louse], 0, strike, 0)
        # Curl up triggered
        self.assertEqual(m1[0].curl_up, 0)
        # 6 dmg - 5 curl block = 1 dmg to HP (15 - 1 = 14)
        self.assertEqual(m1[0].current_hp, 14)
        # Thorns reflected 3 dmg to player (20 - 3 = 17)
        self.assertEqual(p1.current_hp, 17)

    def test_card_aliases_and_registry_resolution(self):
        """
        Verifies exact resolution of internal game/mod IDs and newly registered cards.
        """
        claw = resolve_card_info({"id": "Gash"})
        self.assertEqual(claw.card_type, "ATTACK")
        self.assertEqual(claw.base_damage, 3)

        adren = resolve_card_info({"id": "Adrenaline", "upgraded": True})
        self.assertEqual(adren.energy_gain, 2)
        self.assertEqual(adren.draw_cards, 2)
        self.assertTrue(adren.exhausts)

        ball = resolve_card_info({"id": "Ball Lightning"})
        self.assertEqual(ball.base_damage, 7)
        self.assertEqual(ball.channel_orb, "Lightning")
        self.assertEqual(ball.channel_count, 1)

        apoth = resolve_card_info({"id": "Apotheosis"})
        self.assertEqual(apoth.cost, 2)
        self.assertTrue(apoth.exhausts)

        sneaky = resolve_card_info({"id": "Underhanded Strike"})
        self.assertEqual(sneaky.base_damage, 12)

    def test_mechanic_vulnerable_and_weak_status_timing(self):
        """
        验证易伤 (vulnerable) 与虚弱 (weak) 机制的数值计算与时序断言：
        1. 打出 Bash 赋予 2 回合易伤 (vulnerable)，敌方 vulnerable_turns == 2，输出 notes 含 '易伤'；
        2. 易伤状态下后续攻击享受 1.5 倍伤害；
        3. 打出 Clothesline 赋予 2 回合虚弱 (weak)，敌方 weak_turns == 2，输出 notes 含 '虚弱'；
        4. 敌方虚弱状态下攻击意图伤害降低 25%。
        """
        player = SimPlayer(current_hp=80, max_hp=80, block=0, energy=4)
        monster = SimMonster(
            index=0, id="Cultist", name="Cultist", current_hp=50, max_hp=50, block=0,
            intent="ATTACK", move_adjusted_damage=12, is_attacking=True
        )
        bash = resolve_card_info({"id": "Bash", "name": "Bash", "cost": 2, "type": "ATTACK"})
        clothesline = resolve_card_info({"id": "Clothesline", "name": "Clothesline", "cost": 2, "type": "ATTACK"})

        # 1. 验证 Bash 施加易伤 (vulnerable)
        p1, m1, s1, d1, dp1, dcp1 = self.solver._simulate_play_card(player, [monster], 0, bash, 0)
        self.assertEqual(m1[0].vulnerable_turns, 2)
        self.assertIn("易伤", s1.notes)
        self.assertEqual(s1.damage_dealt, 8)

        # 2. 验证 Clothesline 在易伤下造成 12 * 1.5 = 18 点伤害，并施加虚弱 (weak)
        p2, m2, s2, d2, dp2, dcp2 = self.solver._simulate_play_card(p1, m1, 1, clothesline, 0)
        self.assertEqual(s2.damage_dealt, 18)
        self.assertEqual(m2[0].weak_turns, 2)
        self.assertIn("虚弱", s2.notes)

        # 3. 验证虚弱对敌方攻击的削弱 (12 * 0.75 = 9)
        plan = self.solver._evaluate_state(p2, m2, [s1, s2], 12)
        self.assertEqual(plan.projected_incoming_damage, 9)

    def test_mechanic_strength_and_dexterity_scaling(self):
        """
        验证力量 (strength) 与敏捷 (dexterity) 状态增长与数值增幅：
        1. 打出 Inflame 获得力量 (strength)，player.strength == 2，notes 含 '力量'；
        2. 打出 Strike 伤害由 6 提升至 6 + 2 = 8；
        3. 打出 Footwork 获得敏捷 (dexterity)，player.dexterity == 2，notes 含 '敏捷'；
        4. 打出 Defend 格挡由 5 提升至 5 + 2 = 7。
        """
        player = SimPlayer(current_hp=80, max_hp=80, block=0, energy=4)
        monster = SimMonster(
            index=0, id="Louse", name="Louse", current_hp=30, max_hp=30, block=0,
            intent="ATTACK", move_adjusted_damage=5, is_attacking=True
        )
        inflame = resolve_card_info({"id": "Inflame", "name": "Inflame", "cost": 1, "type": "POWER"})
        footwork = resolve_card_info({"id": "Footwork", "name": "Footwork", "cost": 1, "type": "POWER"})
        strike = resolve_card_info({"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"})
        defend = resolve_card_info({"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL"})

        # 力量 (strength)
        p1, m1, s1, _, _, _ = self.solver._simulate_play_card(player, [monster], 0, inflame, None)
        self.assertEqual(p1.strength, 2)
        self.assertIn("力量", s1.notes)

        p2, m2, s2, _, _, _ = self.solver._simulate_play_card(p1, m1, 1, strike, 0)
        self.assertEqual(s2.damage_dealt, 8)  # 6 + 2 力量

        # 敏捷 (dexterity)
        p3, m3, s3, _, _, _ = self.solver._simulate_play_card(p2, m2, 2, footwork, None)
        self.assertEqual(p3.dexterity, 2)
        self.assertIn("敏捷", s3.notes)

        p4, m4, s4, _, _, _ = self.solver._simulate_play_card(p3, m3, 3, defend, None)
        self.assertEqual(s4.block_gained, 7)  # 5 + 2 敏捷

    def test_mechanic_energy_gain_and_cards_drawing(self):
        """
        验证能量增益 (energy) 与动态抽牌 (draw) 协同：
        1. 初始能量 1，打出 Bloodletting 回复 2 点能量 (energy)，剩余能量为 1 - 0 + 2 = 3，notes 含 '能量'；
        2. 打出 Pommel Strike 抽牌 (draw)，从 draw_pile 中抽出一张牌放入手牌，notes 含 '抽'。
        """
        player = SimPlayer(current_hp=80, max_hp=80, block=0, energy=1)
        monster = SimMonster(
            index=0, id="Jaw Worm", name="Jaw Worm", current_hp=40, max_hp=40, block=0,
            intent="ATTACK", move_adjusted_damage=8, is_attacking=True
        )
        bloodletting = resolve_card_info({"id": "Bloodletting", "name": "Bloodletting", "cost": 0, "type": "SKILL"})
        pommel = resolve_card_info({"id": "Pommel Strike", "name": "Pommel Strike", "cost": 1, "type": "ATTACK"})
        strike = resolve_card_info({"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"})

        # 回能 (energy)
        p1, m1, s1, _, _, _ = self.solver._simulate_play_card(player, [monster], 0, bloodletting, None)
        self.assertEqual(p1.energy, 3)
        self.assertIn("能量", s1.notes)

        # 抽牌 (draw)
        p2, m2, s2, drawn, next_dp, _ = self.solver._simulate_play_card(p1, m1, 1, pommel, 0, draw_pile=[strike])
        self.assertEqual(len(drawn), 1)
        self.assertEqual(drawn[0][1].name, "Strike")
        self.assertIn("抽", s2.notes)

    def test_mechanic_defect_orbs_channel_evoke_and_focus(self):
        """
        验证故障机器人充能球生成 (channel_orb / channel_count)、激发 (evoke_orbs) 与集中 (focus)：
        1. 打出 Defragment 获得 1 点集中 (focus)，player.focus == 1，notes 含 '集中'；
        2. 打出 Ball Lightning 生成 1 个闪电充能球 (channel_orb, channel_count)，player.orbs 包含 'Lightning'，notes 含 '球'；
        3. 打出 Dualcast 双重激发 (evoke) 最前方的球，闪电球每次激发造成 8 + 1 (集中) = 9 点伤害，共 18 点伤害，notes 含 '激发'。
        """
        player = SimPlayer(current_hp=75, max_hp=75, block=0, energy=4)
        monster = SimMonster(
            index=0, id="Cultist", name="Cultist", current_hp=40, max_hp=40, block=0,
            intent="ATTACK", move_adjusted_damage=6, is_attacking=True
        )
        defrag = resolve_card_info({"id": "Defragment", "name": "Defragment", "cost": 1, "type": "POWER"})
        ball_lightning = resolve_card_info({"id": "Ball Lightning", "name": "Ball Lightning", "cost": 1, "type": "ATTACK"})
        dualcast = resolve_card_info({"id": "Dualcast", "name": "Dualcast", "cost": 1, "type": "SKILL"})

        # 集中 (focus)
        p1, m1, s1, _, _, _ = self.solver._simulate_play_card(player, [monster], 0, defrag, None)
        self.assertEqual(p1.focus, 1)
        self.assertIn("集中", s1.notes)

        # 生成充能球 (channel_orb, channel_count)
        p2, m2, s2, _, _, _ = self.solver._simulate_play_card(p1, m1, 1, ball_lightning, 0)
        self.assertEqual(p2.orbs, ["Lightning"])
        self.assertIn("球", s2.notes)

        # 激发 (evoke_orbs)
        p3, m3, s3, _, _, _ = self.solver._simulate_play_card(p2, m2, 2, dualcast, 0)
        self.assertEqual(len(p3.orbs), 0)
        self.assertEqual(s3.damage_dealt, 18)  # 2 * (8 + 1 集中)
        self.assertIn("激发", s3.notes)

    def test_mechanic_card_exhaust_and_stance_transitions(self):
        """
        验证卡牌消耗 (exhausts) 与观者姿态切换 (stance)：
        1. 打出 Seeing Red，具有消耗 (exhaust) 属性，s1.notes 包含 '消耗'；
        2. 打出 Crescendo 进入【愤怒】姿态 (stance)，伤害与承伤翻倍，notes 包含 '姿态'；
        3. 打出 Tranquility 进入【平静】姿态 (stance)；
        4. 退出平静姿态返还 +2 能量。
        """
        player = SimPlayer(current_hp=80, max_hp=80, block=0, energy=3)
        monster = SimMonster(
            index=0, id="Jaw Worm", name="Jaw Worm", current_hp=40, max_hp=40, block=0,
            intent="ATTACK", move_adjusted_damage=6, is_attacking=True
        )
        seeing_red = resolve_card_info({"id": "Seeing Red", "name": "Seeing Red", "cost": 1, "type": "SKILL"})
        crescendo = resolve_card_info({"id": "Crescendo", "name": "Crescendo", "cost": 1, "type": "SKILL"})
        vigilance = resolve_card_info({"id": "Vigilance", "name": "Vigilance", "cost": 2, "type": "SKILL"})
        empty_body = resolve_card_info({"id": "Empty Body", "name": "Empty Body", "cost": 1, "type": "SKILL"})

        # 消耗 (exhausts)
        p1, m1, s1, _, _, _ = self.solver._simulate_play_card(player, [monster], 0, seeing_red, None)
        self.assertTrue(seeing_red.exhausts)
        self.assertIn("消耗", s1.notes)

        # 姿态 (stance) - 愤怒
        p2, m2, s2, _, _, _ = self.solver._simulate_play_card(p1, m1, 1, crescendo, None)
        self.assertEqual(p2.stance, "Wrath")
        self.assertIn("姿态", s2.notes)

        # 姿态 (stance) - 平静
        p3, m3, s3, _, _, _ = self.solver._simulate_play_card(p2, m2, 2, vigilance, None)
        self.assertEqual(p3.stance, "Calm")
        self.assertIn("姿态", s3.notes)

        # 姿态 (stance) - 退出平静返还 +2 能量
        p4, m4, s4, _, _, _ = self.solver._simulate_play_card(p3, m3, 3, empty_body, None)
        self.assertEqual(p4.stance, "None")
        self.assertEqual(p4.energy, p3.energy - 1 + 2)
        self.assertIn("姿态", s4.notes)

    def test_relic_bronze_scales_and_torii_simulation(self):
        """
        验证高危战术遗物仿真：
        1. 铜制鳞片 (Bronze Scales): 敌人攻击时反弹 3 点伤害；
        2. 鸟居 (Torii): 受到未格挡攻击伤害 <= 5 时削减至 1 点。
        """
        # 测试 1: 鸟居削减伤害 (5 点未格挡伤害削减为 1 点)
        combat_state = {
            "player": {"current_hp": 80, "max_hp": 80, "block": 0, "energy": 3},
            "relics": [{"id": "Torii"}],
            "monsters": [{"id": "Cultist", "current_hp": 40, "max_hp": 50, "intent": "ATTACK", "move_adjusted_damage": 5, "move_hits": 1}],
            "hand": [],
        }
        plan = self.solver.solve(combat_state)
        self.assertEqual(plan.projected_incoming_damage, 5)
        self.assertEqual(plan.projected_hp_loss, 1)  # 5 减免至 1!
        self.assertIn("鸟居减免至1", plan.end_of_turn_forecast)

        # 测试 2: 铜制鳞片反伤 (敌人 4 段攻击，每段受到 3 点反伤，共 12 点)
        combat_state_scales = {
            "player": {"current_hp": 80, "max_hp": 80, "block": 20, "energy": 3},
            "relics": [{"id": "Bronze Scales"}],
            "monsters": [{"id": "Byrd", "name": "Byrd", "current_hp": 25, "max_hp": 25, "block": 0, "intent": "ATTACK", "move_adjusted_damage": 2, "move_hits": 4}],
            "hand": [],
        }
        plan_scales = self.solver.solve(combat_state_scales)
        self.assertIn("受荆棘反伤12", plan_scales.end_of_turn_forecast)

    def test_relic_necronomicon_and_unceasing_top(self):
        """
        验证核心回牌与倍伤遗物：
        1. 死灵之书 (Necronomicon): 每回合第一张耗能 >= 2 的攻击牌连击打出两次；
        2. 陀螺 (Unceasing Top): 手牌耗尽且牌库有牌时触发抽牌并展开求解。
        """
        # 1. 死灵之书双发
        player = SimPlayer(current_hp=80, max_hp=80, block=0, energy=3, has_necronomicon=True)
        monster = SimMonster(index=0, id="Cultist", name="Cultist", current_hp=50, max_hp=50, block=0)
        carnage = resolve_card_info({"id": "Carnage", "name": "Carnage", "cost": 2, "type": "ATTACK"})
        p_res, m_res, step, _, _, _ = self.solver._simulate_play_card(player, [monster], 0, carnage, 0)
        self.assertTrue(p_res.necronomicon_triggered)
        self.assertIn("死灵之书双发", step.notes)
        self.assertEqual(step.damage_dealt, 40)  # 20 * 2 = 40

        # 2. 陀螺 (Unceasing Top) 触发
        combat_state_top = {
            "player": {"current_hp": 80, "max_hp": 80, "block": 0, "energy": 3},
            "relics": [{"id": "Unceasing Top"}],
            "monsters": [{"id": "Louse", "current_hp": 12, "max_hp": 15, "intent": "ATTACK", "move_adjusted_damage": 6}],
            "hand": [{"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"}],
            "draw_pile": [{"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"}],
        }
        plan_top = self.solver.solve(combat_state_top)
        # 打出一张 Strike 杀不死 (6伤)，陀螺自动抽第二张 Strike 打出击杀 12HP 虱虫！
        self.assertEqual(plan_top.monsters_killed, 1)
        self.assertEqual(plan_top.total_damage_dealt, 12)
        self.assertEqual(len(plan_top.steps), 2)
        self.assertIn("陀螺抽牌", plan_top.steps[0].notes)

    def test_relic_energy_and_draw_counters(self):
        """
        验证计数型遗物时序：
        1. 提灯 (Lantern): 第 1 回合初始能量 +1；
        2. 开心小花 (Happy Flower): counter 为 2 时开局初始能量 +1；
        3. 双节棍 (Nunchaku): 打出第 10 张攻击牌额外获得 1 点能量；
        4. 墨水瓶 (InkBottle): 打出第 10 张牌触发抽 1 张牌；
        5. 游标卡尺 (Calipers): 回合末多余格挡保留 (总格挡 - 15)。
        """
        # 1 & 2: Lantern & Happy Flower
        combat_state = {
            "player": {"current_hp": 80, "max_hp": 80, "block": 0, "energy": 3},
            "relics": [{"id": "Lantern"}, {"id": "Happy Flower", "counter": 2}],
            "turn": 1,
            "monsters": [{"id": "Cultist", "current_hp": 40, "max_hp": 50}],
            "hand": [],
        }
        plan = self.solver.solve(combat_state)
        # 3 base + 1 Lantern + 1 Happy Flower = 5 energy
        self.assertEqual(plan.remaining_energy, 5)

        # 3: Nunchaku
        p = SimPlayer(current_hp=80, max_hp=80, block=0, energy=1, has_nunchaku=True, nunchaku_count=9)
        m = SimMonster(index=0, id="Cultist", name="Cultist", current_hp=50, max_hp=50, block=0)
        strike = resolve_card_info({"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"})
        p_res, _, step_nun, _, _, _ = self.solver._simulate_play_card(p, [m], 0, strike, 0)
        self.assertIn("双节棍", step_nun.notes)
        self.assertEqual(p_res.energy, 1 - 1 + 1)  # 1 cost + 1 nunchaku refund

        # 4: InkBottle
        p_ib = SimPlayer(current_hp=80, max_hp=80, block=0, energy=2, has_ink_bottle=True, ink_bottle_count=9)
        defend = resolve_card_info({"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL"})
        draw_pile = [strike]
        p_ib_res, _, step_ib, newly_drawn, _, _ = self.solver._simulate_play_card(p_ib, [m], 0, defend, None, draw_pile=draw_pile)
        self.assertIn("墨水瓶", step_ib.notes)
        self.assertEqual(len(newly_drawn), 1)

        # 5: Calipers
        p_cal = SimPlayer(current_hp=80, max_hp=80, block=40, energy=0, has_calipers=True)
        m_idle = SimMonster(index=0, id="Cultist", name="Cultist", current_hp=50, max_hp=50, block=0, intent="DEFEND")
        plan_cal = self.solver._evaluate_state(p_cal, [m_idle], [], 0)
        # 40 block - 15 = 25 retained
        self.assertIn("游标卡尺保留: 25甲", plan_cal.end_of_turn_forecast)

    def test_expanded_potions_tactical_evaluation(self):
        """
        验证扩展药水体系数值与时序：
        1. 幽灵药水 (Ghost in a Jar): 获得无实体 (Intangible)，受击伤害锁定为 1；
        2. 迅捷药水 (Swift Potion): 抽 3 张手牌加入分支探索。
        """
        # 1. 幽灵药水
        combat_state_ghost = {
            "player": {"current_hp": 50, "max_hp": 80, "block": 0, "energy": 3},
            "monsters": [{"id": "Gremlin Nob", "current_hp": 80, "max_hp": 80, "intent": "ATTACK", "move_adjusted_damage": 30, "move_hits": 1}],
            "hand": [],
            "potions": [{"id": "GhostInAJar", "name": "幽灵药水"}],
        }
        plan_ghost = self.solver.solve(combat_state_ghost)
        self.assertEqual(plan_ghost.projected_hp_loss, 1)  # 30 伤直降为 1 伤！
        self.assertEqual(plan_ghost.potion_uses, ["幽灵药水"])

        # 2. 迅捷药水 (Swift Potion) 抽 3 牌促成斩杀
        combat_state_swift = {
            "player": {"current_hp": 80, "max_hp": 80, "block": 0, "energy": 3},
            "monsters": [{"id": "Cultist", "current_hp": 18, "max_hp": 50, "intent": "ATTACK", "move_adjusted_damage": 12}],
            "hand": [],
            "draw_pile": [
                {"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"},
                {"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"},
                {"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK"},
            ],
            "potions": [{"id": "Swift Potion", "name": "迅捷药水"}],
        }
        plan_swift = self.solver.solve(combat_state_swift)
        self.assertEqual(plan_swift.monsters_killed, 1)
        self.assertEqual(plan_swift.projected_hp_loss, 0)
        self.assertEqual(plan_swift.total_damage_dealt, 18)

    def test_boss_state_machines_and_scaling(self):
        """
        验证 Boss 状态机与进阶难度数值：
        1. 时光吞噬者 (Time Eater): 初始 counter 9 + 打出 3 张牌触发时光扭曲，回合终止且力量+2；
        2. 觉醒者 (Awakened One): 一阶段 HP 归零触发二阶段重生 (清空负面、恢复满血、力量+2)；
        3. 腐化之心 (Corrupt Heart): A20 进阶死之律动为 2、无敌上限 200。
        """
        # 1. 时光吞噬者：起始 counter 为 9，打出 3 张牌正好触发时光扭曲
        combat_state_te = {
            "player": {"current_hp": 80, "max_hp": 80, "block": 0, "energy": 5},
            "monsters": [{
                "id": "TimeEater", "name": "Time Eater", "current_hp": 200, "max_hp": 456,
                "intent": "ATTACK", "move_adjusted_damage": 10, "move_hits": 1,
                "powers": [{"id": "Time Warp", "amount": 9}]
            }],
            "hand": [
                {"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL"},
                {"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL"},
                {"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL"},
                {"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL"},
            ]
        }
        plan_te = self.solver.solve(combat_state_te)
        # 最多只能打出 3 张牌即达到 12 上限终止！
        self.assertLessEqual(len(plan_te.steps), 3)
        self.assertIn("时光扭曲", plan_te.steps[2].notes)

        # 2. 觉醒者二阶段重生
        p_atk = SimPlayer(current_hp=80, max_hp=80, block=0, energy=2)
        ao = SimMonster(index=0, id="AwakenedOne", name="Awakened One", current_hp=10, max_hp=300, block=0, awakened_phase=1, curiosity=1)
        carnage = resolve_card_info({"id": "Carnage", "name": "Carnage", "cost": 2, "type": "ATTACK"})
        _, m_res, step_ao, _, _, _ = self.solver._simulate_play_card(p_atk, [ao], 0, carnage, 0)
        self.assertEqual(m_res[0].awakened_phase, 2)
        self.assertEqual(m_res[0].current_hp, 300)
        self.assertEqual(m_res[0].strength, 2)
        self.assertIn("二阶段重生", step_ao.notes)

        # 3. 腐化之心进阶 20 (Beat of Death = 2, Invincible = 200)
        combat_state_heart = {
            "ascension_level": 20,
            "player": {"current_hp": 80, "max_hp": 80, "block": 0, "energy": 3},
            "monsters": [{
                "id": "CorruptHeart", "name": "Corrupt Heart", "current_hp": 750, "max_hp": 800,
                "intent": "ATTACK", "move_adjusted_damage": 2, "move_hits": 15,
                "powers": [{"id": "Invincible", "amount": 200}, {"id": "Beat of Death", "amount": 2}]
            }],
            "hand": [{"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL"}]
        }
        plan_heart = self.solver.solve(combat_state_heart)
        self.assertIsNotNone(plan_heart)
        # 打出一张牌触发死之律动 2 点直伤
        self.assertIn("死之律动2伤", plan_heart.steps[0].notes)

if __name__ == "__main__":
    unittest.main()
