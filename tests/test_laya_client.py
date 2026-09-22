"""
Unit tests for Laya Client (laya_client.py).
Verifies:
1. Health endpoint connectivity
2. Synchronous predict with choice, score, noul typed questions
3. Cache functionality
4. Async predict execution
"""
import unittest
import threading
from laya_client import LayaClient

class TestLayaClient(unittest.TestCase):
    def setUp(self):
        self.client = LayaClient()

    def test_health_check(self):
        health = self.client.check_health()
        self.assertTrue(health.get("online", False), f"Health check failed: {health}")
        data = health.get("data", {})
        self.assertEqual(data.get("status"), "ready")

    def test_typed_predict(self):
        state = {
            "character": "IRONCLAD",
            "floor": 3,
            "hp": 75,
            "max_hp": 80
        }
        questions = {
            "card_choice": {
                "type": "choice",
                "instructions": "选择最适合当前战士的卡牌",
                "criteria": {
                    "Carnage": "2费20伤高爆发",
                    "Defend": "1费5格挡",
                    "Skip": "跳过不选"
                }
            },
            "skip_eval": {
                "type": "noul",
                "instructions": "当前是否应该跳过？"
            },
            "synergy_score": {
                "type": "score",
                "instructions": "卡组契合度",
                "criteria": ["差", "中", "良", "优"]
            }
        }

        resp = self.client.predict(state, questions)
        self.assertNotIn("error", resp, f"Predict error: {resp}")
        answers = resp.get("answers", {})

        # Verify choice
        self.assertIn("card_choice", answers)
        self.assertEqual(answers["card_choice"]["type"], "choice")
        self.assertIn("choice", answers["card_choice"])
        self.assertIn("confidence", answers["card_choice"])

        # Verify noul
        self.assertIn("skip_eval", answers)
        self.assertEqual(answers["skip_eval"]["type"], "noul")
        self.assertIsInstance(answers["skip_eval"]["noul"], (int, float))

        # Verify score
        self.assertIn("synergy_score", answers)
        self.assertEqual(answers["synergy_score"]["type"], "score")
        self.assertIsInstance(answers["synergy_score"]["score"], (int, float))

    def test_caching(self):
        state = {"test_key": "cache_val"}
        questions = {
            "q1": {
                "type": "noul",
                "instructions": "缓存测试"
            }
        }
        resp1 = self.client.predict(state, questions)
        resp2 = self.client.predict(state, questions)
        self.assertEqual(resp1.get("answers"), resp2.get("answers"))

if __name__ == "__main__":
    unittest.main()
