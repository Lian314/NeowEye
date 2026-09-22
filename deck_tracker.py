"""
Deck Tracker and Draw Probability Engine for Slay the Spire.
Tracks:
- Draw Pile (抽牌堆)
- Discard Pile (弃牌堆)
- Exhaust Pile (消耗堆)
Calculates exact hypergeometric probabilities for drawing Block, Lethal, and Curses next turn.
Provides pro tactical warnings (e.g. "Only 32% chance of block next turn, stall or retain block now!").
"""
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from card_db import resolve_card_info

@dataclass
class DeckStats:
    total_draw_count: int
    total_discard_count: int
    total_exhaust_count: int

    # Draw pile breakdown
    draw_attacks: int = 0
    draw_skills: int = 0
    draw_powers: int = 0
    draw_curses_status: int = 0
    draw_block_cards: int = 0

    # Probabilities for drawing 5 cards next turn
    prob_draw_block: float = 0.0
    prob_draw_attack: float = 0.0
    prob_draw_curse_status: float = 0.0

    # Categorized lists with card names
    draw_pile_cards: List[str] = field(default_factory=list)
    discard_pile_cards: List[str] = field(default_factory=list)
    exhaust_pile_cards: List[str] = field(default_factory=list)

    # Actionable tactical advice
    tactical_advice: str = ""

class DeckTracker:
    def __init__(self):
        pass

    def analyze_deck(
        self,
        combat_state: Dict[str, Any],
        draw_count_next_turn: int = 5
    ) -> DeckStats:
        """
        Analyzes combat_state draw/discard/exhaust piles and computes draw probabilities.
        """
        draw_pile = combat_state.get("draw_pile", [])
        discard_pile = combat_state.get("discard_pile", [])
        exhaust_pile = combat_state.get("exhaust_pile", [])

        total_draw = len(draw_pile)
        total_discard = len(discard_pile)
        total_exhaust = len(exhaust_pile)

        # Parse draw pile cards
        draw_attacks = 0
        draw_skills = 0
        draw_powers = 0
        draw_curses = 0
        draw_blocks = 0
        draw_names = []

        for c in draw_pile:
            info = resolve_card_info(c)
            draw_names.append(info.name_zh)
            if info.card_type == "ATTACK":
                draw_attacks += 1
            elif info.card_type == "SKILL":
                draw_skills += 1
                if info.base_block > 0:
                    draw_blocks += 1
            elif info.card_type == "POWER":
                draw_powers += 1
            elif info.card_type in ["STATUS", "CURSE"]:
                draw_curses += 1

        discard_names = [resolve_card_info(c).name_zh for c in discard_pile]
        exhaust_names = [resolve_card_info(c).name_zh for c in exhaust_pile]

        # Calculate hypergeometric probabilities for next turn
        N = total_draw
        D = min(draw_count_next_turn, N) if N > 0 else 0

        prob_block = self._calc_hypergeometric_prob(N, draw_blocks, D) if N > 0 else 0.0
        prob_attack = self._calc_hypergeometric_prob(N, draw_attacks, D) if N > 0 else 0.0
        prob_curse = self._calc_hypergeometric_prob(N, draw_curses, D) if N > 0 else 0.0

        # Tactical advice generation
        advice = []
        if N > 0:
            if prob_block < 0.40 and draw_blocks > 0:
                advice.append(f"⚠️ 下回合抽到格挡牌概率仅 {round(prob_block * 100)}%！本回合建议优先保留防御或打出过牌！")
            elif prob_block >= 0.85:
                advice.append(f"🛡️ 下回合抽到格挡概率高 ({round(prob_block * 100)}%)，防守充裕，可放心输出。")

            if prob_curse > 0.50:
                advice.append(f"🛑 下回合有 {round(prob_curse * 100)}% 概率抽到诅咒/废牌，注意防鬼抽！")

            if N <= 3:
                advice.append(f"🔄 抽牌堆仅剩 {N} 张，下下回合将触发重洗！")
        else:
            advice.append("🔄 抽牌堆为空，下回合将重洗弃牌堆。")

        return DeckStats(
            total_draw_count=total_draw,
            total_discard_count=total_discard,
            total_exhaust_count=total_exhaust,
            draw_attacks=draw_attacks,
            draw_skills=draw_skills,
            draw_powers=draw_powers,
            draw_curses_status=draw_curses,
            draw_block_cards=draw_blocks,
            prob_draw_block=prob_block,
            prob_draw_attack=prob_attack,
            prob_draw_curse_status=prob_curse,
            draw_pile_cards=draw_names,
            discard_pile_cards=discard_names,
            exhaust_pile_cards=exhaust_names,
            tactical_advice=" ".join(advice)
        )

    def _calc_hypergeometric_prob(self, N: int, K: int, n: int) -> float:
        """
        Probability of drawing at least 1 success: 1 - C(N-K, n) / C(N, n).
        """
        if N <= 0 or n <= 0 or K <= 0:
            return 0.0
        if K >= N or n >= N:
            return 1.0

        # C(N - K, n) / C(N, n)
        if N - K < n:
            return 1.0

        try:
            ways_no_success = math.comb(N - K, n)
            total_ways = math.comb(N, n)
            if total_ways == 0:
                return 0.0
            return 1.0 - (ways_no_success / total_ways)
        except Exception:
            return 0.0
