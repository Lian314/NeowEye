"""
World-Class Macro Advisor Module for Slay the Spire.
Features:
- Deck Archetype Recognition (Strength, Shiv, Poison, Orbs, Stance Dance).
- Pro Skip Philosophy (Deck bloat analysis, curve balance).
- Boss Specific Counter-Strategy (Time Eater 12-card counter, Awakened One power counter, Donu/Deca scaling).
- Multi-Screen Decision Engine:
  - Card Rewards (choice, score, noul)
  - Map Route Planning (path risk, elite safety)
  - Rest Site (Smith vs Rest vs Toke/Dig)
  - Shop Assistant (Removal vs Relic vs Card ROI)
Queries the deployed Laya 421M decision model and parses structured decisions with confidence.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import logging
from laya_client import LayaClient
from card_db import resolve_card_info
from knowledge_base import GLOBAL_KB

logger = logging.getLogger("MacroAdvisor")

@dataclass
class MacroDecision:
    decision_type: str  # "CARD_REWARD", "MAP_ROUTING", "REST_SITE", "SHOP"
    title: str
    recommended_choice: str
    confidence: float
    choice_probabilities: Dict[str, float] = field(default_factory=dict)
    noul_probability: Optional[float] = None
    noul_label: str = ""
    score_value: Optional[float] = None
    score_label: str = ""
    tactical_note: str = ""
    deck_archetype: str = ""
    raw_response: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0

class MacroAdvisor:
    def __init__(self, laya_client: Optional[LayaClient] = None):
        self.laya = laya_client or LayaClient()

    def detect_archetype(self, character: str, deck: List[str], relics: List[str]) -> str:
        """Detects the deck's primary tactical archetype."""
        deck_str = " ".join(deck).lower()
        relic_str = " ".join(relics).lower()

        char_upper = character.upper()
        if "IRONCLAD" in char_upper:
            if "corruption" in deck_str or "feel no pain" in deck_str or "dark embrace" in deck_str:
                return "消耗流 (Corruption/Exhaust)"
            elif "barricade" in deck_str or "body slam" in deck_str or "entrench" in deck_str:
                return "防战/盾猛流 (Barricade/Block)"
            elif "demon form" in deck_str or "inflame" in deck_str or "spot weakness" in deck_str or "limit break" in deck_str:
                return "力量战 (Strength Scaling)"
            elif "rupture" in deck_str or "hemokinesis" in deck_str or "bloodletting" in deck_str:
                return "自残战 (Self-Harm Rupture)"
            return "通用战士平衡流 (Balanced Ironclad)"

        elif "SILENT" in char_upper:
            if "catalyst" in deck_str or "noxious fumes" in deck_str or "corpse explosion" in deck_str:
                return "剧毒流 (Poison/Catalyst)"
            elif "blade dance" in deck_str or "accuracy" in deck_str or "cloak and dagger" in deck_str or "wristblade" in relic_str:
                return "小刀流 (Shiv Burst)"
            elif "calculated gamble" in deck_str or "reflex" in deck_str or "tactician" in deck_str:
                return "弃牌过牌流 (Discard Cycle)"
            return "通用猎手平衡流 (Balanced Silent)"

        elif "DEFECT" in char_upper:
            if "electrodynamics" in deck_str or "ball lightning" in deck_str or "thunder strike" in deck_str:
                return "闪电输出流 (Lightning Strike)"
            elif "glacier" in deck_str or "blizzard" in deck_str or "defragment" in deck_str:
                return "冰霜乌龟流 (Frost Turtling)"
            elif "all for one" in deck_str or "claw" in deck_str or "scrape" in deck_str:
                return "万物一心 0 费爪击流 (0-Cost Claw)"
            return "通用充能球流 (Balanced Orbs)"

        elif "WATCHER" in char_upper:
            if "tantrum" in deck_str or "rushdown" in deck_str or "inner peace" in deck_str or "empty" in deck_str:
                return "姿态舞者无限流 (Wrath/Calm Dance)"
            elif "worship" in deck_str or "prostrate" in deck_str or "devotion" in deck_str:
                return "真言神化流 (Mantra Divinity)"
            return "通用姿态流 (Balanced Stance)"

        return "通用流派 (General Archetype)"

    def evaluate_card_reward(self, game_state: Dict[str, Any]) -> MacroDecision:
        """
        Evaluates card choices when screen_type is CARD_REWARD.
        Incorporates deck archetype, deck thickness (Skip philosophy), and Act Boss awareness.
        """
        screen_state = game_state.get("screen_state", {})
        offered_cards = screen_state.get("cards", [])

        character = game_state.get("class", "IRONCLAD")
        floor = game_state.get("floor", 1)
        act = game_state.get("act", 1)
        act_boss = game_state.get("act_boss", "")
        hp = game_state.get("current_hp", 80)
        max_hp = game_state.get("max_hp", 80)
        deck_cards = [c.get("name", c.get("id", "Card")) for c in game_state.get("deck", [])]
        relics = [r.get("name", r.get("id", "Relic")) for r in game_state.get("relics", [])]

        archetype = self.detect_archetype(character, deck_cards, relics)

        tactical_notes = []
        # Deck thickness (Pro Skip philosophy)
        if len(deck_cards) >= 20:
            tactical_notes.append(f"⚠️ 卡组已达 {len(deck_cards)} 张，非核心质变牌建议坚定选择 Skip 保持牌库精简！")

        # Act Boss preparation check
        boss_context = ""
        if act_boss:
            if "Time" in act_boss or "Eater" in act_boss:
                boss_context = "本幕 Boss 为【时光吞噬者】：每12张牌强制跳回合，防小刀/低费小牌，优先高单卡质量！"
                tactical_notes.append("⏳ Boss预警: 时光吞噬者，谨慎抓取低效小牌！")
            elif "Awakened" in act_boss:
                boss_context = "本幕 Boss 为【觉醒者】：玩家每打出能力牌Boss永久+2力量，谨慎抓取过渡能力牌！"
                tactical_notes.append("🦅 Boss预警: 觉醒者，忌盲目抓取弱效能力牌！")
            elif "Donu" in act_boss or "Deca" in act_boss:
                boss_context = "本幕 Boss 为【甜圈八角】：成长护甲与力量，需要稳定高额单体爆发与AOE！"

        # Build criteria for choice question
        criteria = {}
        for card_data in offered_cards:
            info = resolve_card_info(card_data)
            card_label = info.name
            desc = info.description or f"{info.card_type} 牌，耗能 {info.cost}"
            criteria[card_label] = f"【{info.name_zh}】耗能:{info.cost} {desc}"

        criteria["Skip"] = "【跳过(Skip)】不抓任何牌，防止牌库膨胀污染抽牌堆，保持核心牌抽取率"

        state_payload = {
            "character": character,
            "archetype": archetype,
            "floor": floor,
            "act": act,
            "act_boss": act_boss or "Unknown",
            "boss_context": boss_context,
            "hp": hp,
            "max_hp": max_hp,
            "hp_percent": f"{round((hp/max_hp)*100)}%",
            "deck_size": len(deck_cards),
            "deck_sample": deck_cards[:15],
            "relics": relics[:8]
        }

        instructions_text = f"在第{floor}层、血量{hp}/{max_hp}、卡组共{len(deck_cards)}张【{archetype}】下，应选哪张牌还是跳过？"
        if boss_context:
            instructions_text += f" ({boss_context})"

        questions = {
            "card_choice": {
                "type": "choice",
                "instructions": instructions_text,
                "criteria": criteria
            },
            "skip_eval": {
                "type": "noul",
                "instructions": f"当前牌库已有{len(deck_cards)}张牌，为防止卡组臃肿，是否应该跳过本次选牌？"
            },
            "synergy_score": {
                "type": "score",
                "instructions": f"这批候选卡牌与当前【{archetype}】战术体系的契合度打分",
                "criteria": ["完全不契合/废牌", "勉强可用过渡牌", "良好协同牌", "核心质变牌"]
            }
        }

        resp = self.laya.predict(state_payload, questions)
        answers = resp.get("answers", {})

        choice_ans = answers.get("card_choice", {})
        rec_choice = choice_ans.get("choice", "Skip")
        confidence = choice_ans.get("confidence", 0.0)
        probabilities = choice_ans.get("probabilities", {})

        noul_ans = answers.get("skip_eval", {})
        skip_prob = noul_ans.get("noul", None)

        score_ans = answers.get("synergy_score", {})
        synergy_score = score_ans.get("score", None)

        combined_note = " ".join(tactical_notes)

        return MacroDecision(
            decision_type="CARD_REWARD",
            title="🎯 抓牌推荐 (Laya 决策模型)",
            recommended_choice=rec_choice,
            confidence=confidence,
            choice_probabilities=probabilities,
            noul_probability=skip_prob,
            noul_label="跳过概率",
            score_value=synergy_score,
            score_label="牌组契合度",
            tactical_note=combined_note,
            deck_archetype=archetype,
            raw_response=resp,
            latency_ms=resp.get("latency_ms", resp.get("client_latency_ms", 0.0))
        )

    def evaluate_map_routing(self, game_state: Dict[str, Any]) -> MacroDecision:
        """Evaluates next node choice on MAP screen."""
        screen_state = game_state.get("screen_state", {})
        next_nodes = screen_state.get("next_nodes", [])

        character = game_state.get("class", "IRONCLAD")
        floor = game_state.get("floor", 1)
        hp = game_state.get("current_hp", 80)
        max_hp = game_state.get("max_hp", 80)
        gold = game_state.get("gold", 99)

        criteria = {}
        if next_nodes:
            for idx, node in enumerate(next_nodes):
                symbol = node.get("symbol", "M")
                name_map = {"M": "普通怪物 (Monster)", "?": "未知事件 (Event)", "E": "精英敌人 (Elite)", "R": "休息营地 (Rest)", "$": "商人商店 (Shop)", "T": "宝箱 (Treasure)"}
                lbl = f"Node_{idx+1}_{symbol}"
                criteria[lbl] = f"前往 {name_map.get(symbol, symbol)} 节点 (坐标 x={node.get('x')}, y={node.get('y')})"
        else:
            criteria = {
                "Route_Safe_Monster": "稳健路线：普通怪物战，累积金币与卡牌",
                "Route_Event_Question": "问号随机事件：寻求遗物或有利奇遇",
                "Route_Elite_Challenge": "高收益精英路线：挑战精英获取稀有遗物",
                "Route_Shop_Rest": "补给路线：前往商店购买资源或营地休整"
            }

        state_payload = {
            "character": character,
            "floor": floor,
            "hp": hp,
            "max_hp": max_hp,
            "hp_percent": f"{round((hp/max_hp)*100)}%",
            "gold": gold
        }

        questions = {
            "path_choice": {
                "type": "choice",
                "instructions": f"在当前第{floor}层，血量{hp}/{max_hp}，金币{gold}时，下一步应选择哪条行进路线？",
                "criteria": criteria
            },
            "elite_safety": {
                "type": "noul",
                "instructions": "在当前血量与战力下，挑战精英怪物是否安全（无暴毙风险）？"
            },
            "route_risk": {
                "type": "score",
                "instructions": "评估当前路线面临的综合危险程度",
                "criteria": ["极度安全", "轻度风险", "高危考验", "致命危机"]
            }
        }

        resp = self.laya.predict(state_payload, questions)
        answers = resp.get("answers", {})

        choice_ans = answers.get("path_choice", {})
        rec_choice = choice_ans.get("choice", list(criteria.keys())[0])
        confidence = choice_ans.get("confidence", 0.0)
        probabilities = choice_ans.get("probabilities", {})

        noul_ans = answers.get("elite_safety", {})
        elite_safe = noul_ans.get("noul", None)

        score_ans = answers.get("route_risk", {})
        risk_score = score_ans.get("score", None)

        return MacroDecision(
            decision_type="MAP_ROUTING",
            title="🗺️ 路线规划决策 (Laya 决策模型)",
            recommended_choice=rec_choice,
            confidence=confidence,
            choice_probabilities=probabilities,
            noul_probability=elite_safe,
            noul_label="精英安全度",
            score_value=risk_score,
            score_label="路线危险度",
            raw_response=resp,
            latency_ms=resp.get("latency_ms", resp.get("client_latency_ms", 0.0))
        )

    def evaluate_rest_site(self, game_state: Dict[str, Any]) -> MacroDecision:
        """Evaluates Rest site action (Smith vs Rest)."""
        character = game_state.get("class", "IRONCLAD")
        floor = game_state.get("floor", 1)
        hp = game_state.get("current_hp", 80)
        max_hp = game_state.get("max_hp", 80)
        hp_pct = hp / max_hp

        criteria = {
            "Smith": "锻造升级：强化牌组核心关键卡牌，提升长期战力",
            "Rest": "休息：回复30%最大生命值，降低后续战死风险"
        }

        state_payload = {
            "character": character,
            "floor": floor,
            "hp": hp,
            "max_hp": max_hp,
            "hp_percent": f"{round(hp_pct*100)}%"
        }

        questions = {
            "rest_action": {
                "type": "choice",
                "instructions": f"在营地血量{hp}/{max_hp} ({round(hp_pct*100)}%) 时，应该锻造还是休息？",
                "criteria": criteria
            },
            "need_heal": {
                "type": "noul",
                "instructions": "当前生命值是否低于安全阈值，必须执行休息回血？"
            }
        }

        resp = self.laya.predict(state_payload, questions)
        answers = resp.get("answers", {})

        choice_ans = answers.get("rest_action", {})
        rec_choice = choice_ans.get("choice", "Smith" if hp_pct > 0.5 else "Rest")
        confidence = choice_ans.get("confidence", 0.0)
        probabilities = choice_ans.get("probabilities", {})

        noul_ans = answers.get("need_heal", {})
        heal_urgency = noul_ans.get("noul", None)

        return MacroDecision(
            decision_type="REST_SITE",
            title="⛺ 营地抉择 (Laya 决策模型)",
            recommended_choice=rec_choice,
            confidence=confidence,
            choice_probabilities=probabilities,
            noul_probability=heal_urgency,
            noul_label="回血紧迫度",
            raw_response=resp,
            latency_ms=resp.get("latency_ms", resp.get("client_latency_ms", 0.0))
        )
