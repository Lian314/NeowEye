"""
Realistic Slay the Spire game states for testing, demonstrations, and offline verification.
Modeled after actual CommunicationMod JSON outputs.
"""
from typing import Dict, Any

# Scenario 1: Ironclad vs Cultist (Turn 2, Cultist attacking for 12 damage)
# Player has 80 HP, 0 Block, 3 Energy
# Hand: Bash (cost 2, 8 dmg, 2 vuln), Defend (cost 1, 5 block), Defend (cost 1, 5 block), Strike (cost 1, 6 dmg)
# Goal: Optimizer should calculate best line: Defend + Defend + Strike (Block 10, deal 6 dmg, take 2 dmg)
# OR if upgraded or different cards, maximize mitigation.
SCENARIO_CULTIST_ATTACKING: Dict[str, Any] = {
    "available_commands": ["play", "end"],
    "ready_for_command": True,
    "in_game": True,
    "game_state": {
        "screen_type": "NONE",
        "floor": 1,
        "act": 1,
        "class": "IRONCLAD",
        "current_hp": 80,
        "max_hp": 80,
        "gold": 99,
        "deck": [
            {"id": "Strike_R", "name": "Strike"},
            {"id": "Strike_R", "name": "Strike"},
            {"id": "Strike_R", "name": "Strike"},
            {"id": "Defend_R", "name": "Defend"},
            {"id": "Defend_R", "name": "Defend"},
            {"id": "Bash", "name": "Bash"}
        ],
        "relics": [{"id": "Burning Blood", "name": "Burning Blood"}],
        "combat_state": {
            "turn": 2,
            "player": {
                "current_hp": 80,
                "max_hp": 80,
                "block": 0,
                "energy": 3,
                "powers": []
            },
            "hand": [
                {"id": "Bash", "name": "Bash", "cost": 2, "type": "ATTACK", "target": "ENEMY", "is_playable": True},
                {"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL", "target": "SELF", "is_playable": True},
                {"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL", "target": "SELF", "is_playable": True},
                {"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK", "target": "ENEMY", "is_playable": True},
                {"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK", "target": "ENEMY", "is_playable": True}
            ],
            "monsters": [
                {
                    "id": "Cultist",
                    "name": "邪教徒 (Cultist)",
                    "current_hp": 48,
                    "max_hp": 50,
                    "block": 0,
                    "intent": "ATTACK",
                    "move_adjusted_damage": 12,
                    "move_hits": 1,
                    "powers": [{"id": "Ritual", "amount": 3}]
                }
            ]
        }
    }
}

# Scenario 2: Lethal Opportunity
# Cultist has only 14 HP left, attacking for 15 damage!
# Hand has Bash (cost 2, 8 dmg, 2 vuln) and Strike (cost 1, 6 dmg -> with vuln deals 9 dmg = 17 dmg > 14 HP lethal!)
# If player plays Bash + Strike, Cultist DIES BEFORE ATTACKING -> 0 damage taken!
# Mathematical optimizer must recognize lethal eliminates 15 incoming damage!
SCENARIO_LETHAL_CULTIST: Dict[str, Any] = {
    "available_commands": ["play", "end"],
    "ready_for_command": True,
    "in_game": True,
    "game_state": {
        "screen_type": "NONE",
        "floor": 2,
        "act": 1,
        "class": "IRONCLAD",
        "current_hp": 65,
        "max_hp": 80,
        "gold": 115,
        "deck": [],
        "relics": [{"id": "Burning Blood", "name": "Burning Blood"}],
        "combat_state": {
            "turn": 3,
            "player": {
                "current_hp": 65,
                "max_hp": 80,
                "block": 0,
                "energy": 3,
                "powers": []
            },
            "hand": [
                {"id": "Bash", "name": "Bash", "cost": 2, "type": "ATTACK", "target": "ENEMY", "is_playable": True},
                {"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK", "target": "ENEMY", "is_playable": True},
                {"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL", "target": "SELF", "is_playable": True}
            ],
            "monsters": [
                {
                    "id": "Cultist",
                    "name": "邪教徒 (Cultist)",
                    "current_hp": 15,
                    "max_hp": 50,
                    "block": 0,
                    "intent": "ATTACK",
                    "move_adjusted_damage": 15,
                    "move_hits": 1,
                    "powers": []
                }
            ]
        }
    }
}

# Scenario 3: Multi-Monster Encounter (2 Acid Slimes)
# Monster 0: Acid Slime M (HP 8, attacking for 8 dmg)
# Monster 1: Acid Slime S (HP 12, buffing/licking)
# Hand: Strike (cost 1, 6 dmg), Defend (cost 1, 5 block), Twin Strike (cost 1, 5x2 = 10 dmg)
# Playing Twin Strike on Monster 0 eliminates Monster 0 (and its 8 damage!), then Defend + Strike on Monster 1.
SCENARIO_MULTI_SLIMES: Dict[str, Any] = {
    "available_commands": ["play", "end"],
    "ready_for_command": True,
    "in_game": True,
    "game_state": {
        "screen_type": "NONE",
        "floor": 4,
        "act": 1,
        "class": "IRONCLAD",
        "current_hp": 70,
        "max_hp": 80,
        "gold": 140,
        "deck": [],
        "relics": [],
        "combat_state": {
            "turn": 1,
            "player": {
                "current_hp": 70,
                "max_hp": 80,
                "block": 0,
                "energy": 3,
                "powers": []
            },
            "hand": [
                {"id": "Twin Strike", "name": "Twin Strike", "cost": 1, "type": "ATTACK", "target": "ENEMY", "is_playable": True},
                {"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL", "target": "SELF", "is_playable": True},
                {"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK", "target": "ENEMY", "is_playable": True}
            ],
            "monsters": [
                {
                    "id": "AcidSlime_M",
                    "name": "酸液史莱姆(中)",
                    "current_hp": 8,
                    "max_hp": 28,
                    "block": 0,
                    "intent": "ATTACK",
                    "move_adjusted_damage": 8,
                    "move_hits": 1,
                    "powers": []
                },
                {
                    "id": "AcidSlime_S",
                    "name": "酸液史莱姆(小)",
                    "current_hp": 12,
                    "max_hp": 12,
                    "block": 0,
                    "intent": "DEBUFF",
                    "move_adjusted_damage": 0,
                    "move_hits": 0,
                    "powers": []
                }
            ]
        }
    }
}

# Scenario 4: Card Reward Screen (Macro Decision via Laya)
SCENARIO_CARD_REWARD: Dict[str, Any] = {
    "available_commands": ["choose"],
    "ready_for_command": True,
    "in_game": True,
    "game_state": {
        "screen_type": "CARD_REWARD",
        "floor": 3,
        "act": 1,
        "class": "IRONCLAD",
        "current_hp": 72,
        "max_hp": 80,
        "gold": 156,
        "deck": [
            {"id": "Strike_R", "name": "Strike"},
            {"id": "Strike_R", "name": "Strike"},
            {"id": "Defend_R", "name": "Defend"},
            {"id": "Defend_R", "name": "Defend"},
            {"id": "Bash", "name": "Bash"},
            {"id": "Iron Wave", "name": "Iron Wave"}
        ],
        "relics": [{"id": "Burning Blood", "name": "Burning Blood"}],
        "screen_state": {
            "cards": [
                {"id": "Carnage", "name": "Carnage", "cost": 2, "type": "ATTACK", "upgraded": False},
                {"id": "Twin Strike", "name": "Twin Strike", "cost": 1, "type": "ATTACK", "upgraded": False},
                {"id": "True Grit", "name": "True Grit", "cost": 1, "type": "SKILL", "upgraded": False}
            ],
            "bowl_available": False,
            "skip_available": True
        }
    }
}

# Scenario 5: Map Route Planning Screen
SCENARIO_MAP_ROUTING: Dict[str, Any] = {
    "available_commands": ["choose"],
    "ready_for_command": True,
    "in_game": True,
    "game_state": {
        "screen_type": "MAP",
        "floor": 6,
        "act": 1,
        "class": "IRONCLAD",
        "current_hp": 48,
        "max_hp": 80,
        "gold": 185,
        "deck": [],
        "relics": [{"id": "Burning Blood", "name": "Burning Blood"}],
        "screen_state": {
            "next_nodes": [
                {"x": 1, "y": 7, "symbol": "E"},
                {"x": 3, "y": 7, "symbol": "M"},
                {"x": 5, "y": 7, "symbol": "?"}
            ]
        }
    }
}

# Scenario 6: Rest Site Screen
SCENARIO_REST_SITE: Dict[str, Any] = {
    "available_commands": ["choose"],
    "ready_for_command": True,
    "in_game": True,
    "game_state": {
        "screen_type": "REST",
        "floor": 7,
        "act": 1,
        "class": "IRONCLAD",
        "current_hp": 30,
        "max_hp": 80,
        "gold": 210,
        "deck": [
            {"id": "Bash", "name": "Bash", "can_upgrade": True},
            {"id": "Strike_R", "name": "Strike", "can_upgrade": True}
        ],
        "relics": [{"id": "Burning Blood", "name": "Burning Blood"}],
        "screen_state": {
            "has_rested": False
        }
    }
}

# Scenario 7: Relic Counter Combat (Pen Nib 9/10 + Incense Burner 5/6)
SCENARIO_RELIC_ALERT: Dict[str, Any] = {
    "available_commands": ["play", "end"],
    "ready_for_command": True,
    "in_game": True,
    "game_state": {
        "screen_type": "NONE",
        "floor": 12,
        "act": 1,
        "class": "IRONCLAD",
        "current_hp": 55,
        "max_hp": 80,
        "gold": 160,
        "deck": [],
        "relics": [
            {"id": "Incense Burner", "name": "香炉", "counter": 5},
            {"id": "Pen Nib", "name": "钢笔尖", "counter": 9},
            {"id": "Anchor", "name": "锚", "counter": -1}
        ],
        "combat_state": {
            "turn": 2,
            "player": {
                "current_hp": 55,
                "max_hp": 80,
                "block": 0,
                "energy": 3,
                "powers": []
            },
            "hand": [
                {"id": "Strike_R", "name": "Strike", "cost": 1, "type": "ATTACK", "target": "ENEMY", "is_playable": True},
                {"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL", "target": "SELF", "is_playable": True},
                {"id": "Defend_R", "name": "Defend", "cost": 1, "type": "SKILL", "target": "SELF", "is_playable": True}
            ],
            "monsters": [
                {
                    "id": "GremlinNob",
                    "name": "地精大块头 (Gremlin Nob)",
                    "current_hp": 30,
                    "max_hp": 86,
                    "block": 0,
                    "intent": "ATTACK",
                    "move_adjusted_damage": 16,
                    "move_hits": 1,
                    "powers": [{"id": "Enrage", "amount": 2}]
                }
            ]
        }
    }
}

# Scenario 8: Thick Deck & Act 3 Boss Preparation (Time Eater + 26 cards)
SCENARIO_THICK_DECK_BOSS: Dict[str, Any] = {
    "available_commands": ["choose"],
    "ready_for_command": True,
    "in_game": True,
    "game_state": {
        "screen_type": "CARD_REWARD",
        "floor": 42,
        "act": 3,
        "act_boss": "Time Eater",
        "class": "IRONCLAD",
        "current_hp": 68,
        "max_hp": 80,
        "gold": 320,
        "deck": [
            {"id": f"Card_{i}", "name": f"Card_{i}"} for i in range(26)
        ],
        "relics": [
            {"id": "Burning Blood", "name": "Burning Blood"},
            {"id": "Incense Burner", "name": "Incense Burner", "counter": 2}
        ],
        "screen_state": {
            "cards": [
                {"id": "Cleave", "name": "Cleave", "cost": 1, "type": "ATTACK", "upgraded": False},
                {"id": "Wild Strike", "name": "Wild Strike", "cost": 1, "type": "ATTACK", "upgraded": False},
                {"id": "Iron Wave", "name": "Iron Wave", "cost": 1, "type": "ATTACK", "upgraded": False}
            ],
            "bowl_available": False,
            "skip_available": True
        }
    }
}

MOCK_SCENARIOS = {
    "1. 邪教徒高压防御回合 (Cultist 12 dmg)": SCENARIO_CULTIST_ATTACKING,
    "2. 斩杀取消敌意回合 (Cultist 15 dmg -> Lethal 0 dmg)": SCENARIO_LETHAL_CULTIST,
    "3. 双怪分段击杀回合 (2 Acid Slimes)": SCENARIO_MULTI_SLIMES,
    "4. 抓牌奖励界面 (Laya 决策模型)": SCENARIO_CARD_REWARD,
    "5. 地图路线规划 (Laya 决策模型)": SCENARIO_MAP_ROUTING,
    "6. 营地休整抉择 (Laya 决策模型)": SCENARIO_REST_SITE,
    "7. 遗物计数器实战 (香炉5/6 + 钢笔尖9/10双倍)": SCENARIO_RELIC_ALERT,
    "8. 牌库厚度与时光吞噬者针对 (26张厚牌库+Time Eater)": SCENARIO_THICK_DECK_BOSS
}
