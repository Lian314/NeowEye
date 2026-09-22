"""
Unit tests for Local Laya ONNX Engine and LayaClient Auto-Switching.
Verifies:
1. LocalLayaEngine properly loads ONNX model and tokenizer.
2. Formats state text and executes ONNX inference.
3. Computes Softmax probabilities for 'choice', Sigmoid for 'noul', and scaled float for 'score'.
4. LayaClient seamless switching between local ONNX and remote HTTP.
"""
import unittest
import os
from config import LayaConfig
from local_laya_engine import LocalLayaEngine
from laya_client import LayaClient

class TestLocalLayaEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure dummy model exists for testing
        cls.model_path = "models/laya_int8.onnx"
        cls.tokenizer_path = "models/tokenizer.json"
        if not os.path.exists(cls.model_path) or not os.path.exists(cls.tokenizer_path):
            from export_laya_onnx import create_dummy_test_model
            create_dummy_test_model("models")

    def setUp(self):
        self.engine = LocalLayaEngine(
            model_path=self.model_path,
            tokenizer_path=self.tokenizer_path
        )
        self.assertTrue(self.engine.is_available(), "LocalLayaEngine should be available.")

    def test_state_text_formatting(self):
        state = {
            "character": "IRONCLAD",
            "floor": 12,
            "act": 1,
            "hp": 65,
            "max_hp": 80,
            "deck_size": 18,
            "deck_sample": ["Strike", "Defend", "Bash", "Carnage"],
            "relics": ["Burning Blood", "Anchor"]
        }
        text = self.engine.format_state_text(state)
        self.assertIn("IRONCLAD", text)
        self.assertIn("HP: 65/80", text)
        self.assertIn("Carnage", text)
        self.assertIn("Anchor", text)

    def test_local_choice_prediction(self):
        state = {"character": "IRONCLAD", "floor": 5, "hp": 70, "max_hp": 80}
        questions = {
            "card_choice": {
                "type": "choice",
                "instructions": "Which card should Ironclad pick?",
                "criteria": {
                    "Carnage": "Deal 20 damage, Ethereal",
                    "Iron Wave": "Gain 5 block, deal 5 damage",
                    "Skip": "Do not pick any card"
                }
            }
        }
        res = self.engine.predict(state, questions)
        self.assertEqual(res["engine"], "local_onnx")
        self.assertIn("answers", res)
        self.assertIn("card_choice", res["answers"])

        ans = res["answers"]["card_choice"]
        self.assertIn("choice", ans)
        self.assertIn("confidence", ans)
        self.assertIn("probabilities", ans)

        # Verify choice is one of the candidates
        self.assertIn(ans["choice"], ["Carnage", "Iron Wave", "Skip"])
        # Verify probabilities sum to ~1.0
        prob_sum = sum(ans["probabilities"].values())
        self.assertAlmostEqual(prob_sum, 1.0, places=2)
        # Verify latency is reported and fast (< 100ms)
        self.assertLess(res["latency_ms"], 100)

    def test_local_noul_and_score_predictions(self):
        state = {"character": "THE_SILENT", "floor": 10, "hp": 50, "max_hp": 70}
        questions = {
            "skip_eval": {
                "type": "noul",
                "instructions": "Should the player skip this card reward?"
            },
            "synergy_score": {
                "type": "score",
                "instructions": "Rate synergy with Poison archetype"
            }
        }
        res = self.engine.predict(state, questions)
        self.assertEqual(res["engine"], "local_onnx")

        # Noul validation
        noul_val = res["answers"]["skip_eval"]["noul"]
        self.assertIsInstance(noul_val, float)
        self.assertGreaterEqual(noul_val, 0.0)
        self.assertLessEqual(noul_val, 1.0)

        # Score validation
        score_val = res["answers"]["synergy_score"]["score"]
        self.assertIsInstance(score_val, float)
        self.assertGreaterEqual(score_val, 1.0)
        self.assertLessEqual(score_val, 5.0)

    def test_laya_client_auto_mode(self):
        """Verify LayaClient with engine_mode='auto' uses local ONNX engine."""
        cfg = LayaConfig(
            engine_mode="auto",
            local_model_path=self.model_path,
            local_tokenizer_path=self.tokenizer_path
        )
        client = LayaClient(cfg)
        health = client.check_health()
        self.assertTrue(health["online"])
        self.assertEqual(health["engine"], "local_onnx")

        state = {"character": "DEFECT", "floor": 1, "hp": 75, "max_hp": 75}
        questions = {
            "pick": {
                "type": "choice",
                "instructions": "Pick starting card",
                "criteria": ["Ball Lightning", "Zap", "Skip"]
            }
        }
        resp = client.predict(state, questions)
        self.assertEqual(resp.get("engine"), "local_onnx")
        self.assertIn("pick", resp["answers"])

if __name__ == "__main__":
    unittest.main()
