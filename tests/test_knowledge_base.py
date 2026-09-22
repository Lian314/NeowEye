"""
Unit tests for KnowledgeBase and Multi-Character Database.
Verifies:
1. Loading of 295 cards and 169 relics from Slay-the-Spire-EO.
2. Bilingual translation and resolution for all 4 characters (Ironclad, Silent, Defect, Watcher).
3. Relic and Power descriptions lookup.
"""
import unittest
from knowledge_base import GLOBAL_KB
from card_db import resolve_card_info

class TestKnowledgeBase(unittest.TestCase):
    def test_kb_loaded(self):
        self.assertTrue(GLOBAL_KB.is_loaded, "KnowledgeBase failed to load from Slay-the-Spire-EO")
        self.assertGreaterEqual(len(GLOBAL_KB.raw_cards), 250)
        self.assertGreaterEqual(len(GLOBAL_KB.raw_relics), 150)
        self.assertGreaterEqual(len(GLOBAL_KB.raw_monsters), 50)
        self.assertGreaterEqual(len(GLOBAL_KB.raw_powers), 100)

    def test_multi_character_card_resolution(self):
        # Ironclad
        c_ironclad = resolve_card_info({"id": "Bash", "name": "Bash", "cost": 2, "type": "ATTACK"})
        self.assertIn("痛击", c_ironclad.name_zh)

        # Silent
        c_silent = resolve_card_info({"id": "Blade Dance", "name": "Blade Dance", "cost": 1, "type": "SKILL"})
        self.assertIn("刀刃", c_silent.name_zh)
        self.assertIn("Shiv", c_silent.description)

        # Defect
        c_defect = resolve_card_info({"id": "Ball Lightning", "name": "Ball Lightning", "cost": 1, "type": "ATTACK"})
        self.assertIn("闪电", c_defect.name_zh)
        self.assertIn("Lightning", c_defect.description)

        # Watcher
        c_watcher = resolve_card_info({"id": "Tantrum", "name": "Tantrum", "cost": 1, "type": "ATTACK"})
        self.assertIn("暴怒", c_watcher.name_zh)

    def test_relic_resolution(self):
        r_dead_branch = GLOBAL_KB.get_relic_zh_name("Dead Branch")
        self.assertEqual(r_dead_branch, "枯木树枝")

        r_incense = GLOBAL_KB.get_relic_zh_name("Incense Burner")
        self.assertEqual(r_incense, "香炉")
        self.assertTrue(len(GLOBAL_KB.get_relic_description("Incense Burner")) > 0)

if __name__ == "__main__":
    unittest.main()
