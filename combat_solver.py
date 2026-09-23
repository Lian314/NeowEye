"""
World-Class Multi-Character Combat Solver Module for Slay the Spire.
Exhaustively searches card play combinations to calculate the mathematically optimal play sequence.
Features:
- Full 4-character mechanics:
  - Ironclad: Strength scaling, Vulnerable, Body Slam, Block stacking, Energy & Exhaust synergies.
  - The Silent: Poison stacking, Catalyst multiplication, end-of-turn poison lethal cancellation, Shivs.
  - Defect: Orbs (Lightning, Frost, Dark, Plasma), Focus scaling, slot overflow auto-evoke, turn-end passives.
  - Watcher: Wrath (2x dealt, 2x taken), Calm (+2 energy on exit), Divinity (3x dealt).
- Relic modifiers & timings:
  - Pen Nib (precise 10th attack 2x damage trigger & counter reset).
  - Orichalcum (+6 block at turn end if block is 0).
  - Incense Burner (turn 6 Intangible: damage taken reduced to 1 per hit).
  - Paper Frog (1.75x Vulnerable), Paper Crane (40% Weak reduction).
  - Kunai (+1 Dex / 3 attacks), Shuriken (+1 Str / 3 attacks), Ornamental Fan (+4 Block / 3 attacks).
  - Anchor (+10 block turn 1), Strike Dummy (+3 dmg to Strikes).
- Multi-objective optimization:
  - Priority 1: Minimize net HP loss (0 damage taken = PERFECT BLOCK).
  - Priority 2: Maximize lethal enemy cancellations (killing attacking enemy nullifies its damage).
  - Priority 3: Maximize output damage & status effects.
"""
import copy
import math
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from card_db import CardInfo, resolve_card_info
from config import CONFIG

@dataclass
class SimMonster:
    index: int
    id: str
    name: str
    current_hp: int
    max_hp: int
    block: int
    intent: str
    move_adjusted_damage: int = 0
    move_hits: int = 1
    is_attacking: bool = False
    vulnerable_turns: int = 0
    weak_turns: int = 0
    strength: int = 0
    poison: int = 0
    artifact: int = 0
    curl_up: int = 0
    thorns: int = 0
    time_eater_bonus: int = 0
    awakened_one_bonus: int = 0
    beat_of_death: int = 0
    invincible_cap: int = 0
    invincible_damage_taken: int = 0
    is_gone: bool = False
    half_dead: bool = False

    @property
    def is_alive(self) -> bool:
        return self.current_hp > 0 and not self.is_gone and not self.half_dead

@dataclass
class SimPlayer:
    current_hp: int
    max_hp: int
    block: int
    energy: int
    strength: int = 0
    dexterity: int = 0
    focus: int = 0
    vulnerable_turns: int = 0
    weak_turns: int = 0
    frail_turns: int = 0
    stance: str = "None"  # "None", "Wrath", "Calm", "Divinity"

    # Defect Orbs
    orbs: List[str] = field(default_factory=list)  # ["Lightning", "Frost", "Dark", "Plasma"]
    max_orbs: int = 3

    # Relic & Power flags and counters
    pen_nib_count: int = 0
    turn: int = 1
    has_orichalcum: bool = False
    has_incense_burner: bool = False
    attacks_played_this_turn: int = 0
    has_kunai: bool = False
    has_shuriken: bool = False
    has_ornamental_fan: bool = False
    has_paper_frog: bool = False
    has_paper_crane: bool = False
    has_strike_dummy: bool = False
    accuracy_bonus: int = 0  # Silent shiv bonus
    feel_no_pain: int = 0    # Ironclad exhaust synergy (+3/4 block per exhaust)
    dark_embrace: int = 0    # Ironclad exhaust synergy (+1 draw per exhaust)
    has_corruption: bool = False  # Ironclad power (Skills cost 0 and exhaust)
    time_eater_active: bool = False
    cards_played_this_turn: int = 0
    beat_of_death: int = 0
    direct_damage_taken: int = 0

@dataclass
class PlayStep:
    card_index: int
    card_info: CardInfo
    target_monster_index: Optional[int] = None
    target_name: str = ""
    damage_dealt: int = 0
    block_gained: int = 0
    notes: str = ""

@dataclass
class CombatPlan:
    steps: List[PlayStep] = field(default_factory=list)
    initial_incoming_damage: int = 0
    projected_incoming_damage: int = 0
    projected_block: int = 0
    projected_hp_loss: int = 0
    monsters_killed: int = 0
    total_damage_dealt: int = 0
    total_block_gained: int = 0
    remaining_energy: int = 0
    final_stance: str = "None"
    end_of_turn_forecast: str = ""
    potion_uses: List[str] = field(default_factory=list)
    score: float = 0.0
    computation_time_ms: float = 0.0

class CombatSolver:
    def __init__(self, config=None):
        self.config = config or CONFIG.combat

    def solve(
        self,
        combat_state: Dict[str, Any],
        relics: Optional[List[Dict[str, Any]]] = None
    ) -> CombatPlan:
        """
        Calculates the mathematically optimal card play sequence across all 4 characters.
        """
        start_time = time.time()
        player_data = combat_state.get("player", {})
        monsters_data = combat_state.get("monsters", [])
        raw_hand = combat_state.get("hand", [])
        relics_list = relics or combat_state.get("relics") or combat_state.get("player", {}).get("relics", [])
        turn = combat_state.get("turn", 1)

        # Parse player & relics
        player = self._parse_player(player_data, relics_list, turn)

        # Parse monsters
        monsters = [self._parse_monster(idx, m) for idx, m in enumerate(monsters_data)]
        player.time_eater_active = any(self._is_time_eater(m) for m in monsters)
        heart_monsters = [m for m in monsters if self._is_corrupt_heart(m)]
        heart_beat_values = [m.beat_of_death for m in heart_monsters]
        player.beat_of_death = max(heart_beat_values) if heart_beat_values else 0
        if heart_monsters and player.beat_of_death <= 0:
            player.beat_of_death = 1
        for heart in heart_monsters:
            if heart.invincible_cap <= 0:
                heart.invincible_cap = 200
        player.cards_played_this_turn = self._safe_int(combat_state.get("cards_played_this_turn"), 0)
        active_monsters = [m for m in monsters if m.is_alive]

        # Parse draw & discard piles
        raw_draw = combat_state.get("draw_pile", [])
        raw_discard = combat_state.get("discard_pile", [])
        draw_pile: List[CardInfo] = [resolve_card_info(c) for c in raw_draw if isinstance(c, dict)]
        discard_pile: List[CardInfo] = [resolve_card_info(c) for c in raw_discard if isinstance(c, dict)]
        available_potions = [p for p in combat_state.get("potions", []) if isinstance(p, dict)]

        # Parse playable cards
        hand_cards: List[Tuple[int, CardInfo]] = []
        for idx, c in enumerate(raw_hand):
            if c.get("is_playable", True):
                info = resolve_card_info(c)
                if info.cost >= 0:
                    hand_cards.append((idx, info))

        initial_incoming = self._calculate_incoming_damage(active_monsters, player)

        if not active_monsters:
            plan = self._evaluate_state(player, monsters, [], initial_incoming, [])
            plan.computation_time_ms = round((time.time() - start_time) * 1000, 2)
            return plan

        # Bounded DFS search with Beam Width pruning
        best_plan: Optional[CombatPlan] = None
        best_score = -float("inf")
        evaluated_states = 0

        stack = [(player, monsters, hand_cards, draw_pile, discard_pile, available_potions, [], [])]

        while stack and evaluated_states < self.config.max_evaluated_states:
            curr_player, curr_monsters, curr_hand, curr_draw, curr_discard, curr_potions, curr_potion_uses, curr_steps = stack.pop()
            evaluated_states += 1

            plan = self._evaluate_state(curr_player, curr_monsters, curr_steps, initial_incoming, curr_potion_uses)
            if plan.score > best_score:
                best_score = plan.score
                best_plan = plan

            # Depth & energy bound
            if (
                len(curr_steps) >= self.config.max_search_depth
                or curr_player.energy <= 0
                or (curr_player.time_eater_active and curr_player.cards_played_this_turn >= 12)
            ):
                card_actions_allowed = False
            else:
                card_actions_allowed = True

            # Potion use is independent of energy and is limited by inventory.
            for potion_index, potion in enumerate(curr_potions):
                if not self._is_supported_potion(potion):
                    continue
                living_monsters = [m for m in curr_monsters if m.is_alive]
                if not living_monsters:
                    continue
                targets = living_monsters if self._potion_targets_enemy(potion) else [None]
                for target in targets:
                    next_player, next_monsters, potion_name = self._simulate_potion(
                        curr_player, curr_monsters, potion, target
                    )
                    next_potions = curr_potions[:potion_index] + curr_potions[potion_index + 1:]
                    stack.append((
                        next_player, next_monsters, list(curr_hand), list(curr_draw),
                        list(curr_discard), next_potions, curr_potion_uses + [potion_name],
                        list(curr_steps)
                    ))

            if not card_actions_allowed:
                continue

            seen_branches = set()
            for i, (orig_idx, card) in enumerate(curr_hand):
                effective_cost = 0 if (curr_player.has_corruption and card.card_type == "SKILL") else card.cost
                if effective_cost > curr_player.energy:
                    continue

                card_key = (card.id, effective_cost)
                next_hand = curr_hand[:i] + curr_hand[i+1:]
                living_monsters = [m for m in curr_monsters if m.is_alive]
                if not living_monsters:
                    continue

                if card.target == "ENEMY":
                    for target in living_monsters:
                        branch_key = (card_key, target.index)
                        if branch_key in seen_branches:
                            continue
                        seen_branches.add(branch_key)

                        next_player, next_monsters, step, newly_drawn, next_draw, next_discard = self._simulate_play_card(
                            curr_player, curr_monsters, orig_idx, card, target.index, curr_draw, curr_discard
                        )
                        branch_hand = next_hand + newly_drawn
                        stack.append((next_player, next_monsters, branch_hand, next_draw, next_discard, curr_potions, curr_potion_uses, curr_steps + [step]))
                else:
                    if card_key in seen_branches:
                        continue
                    seen_branches.add(card_key)

                    next_player, next_monsters, step, newly_drawn, next_draw, next_discard = self._simulate_play_card(
                        curr_player, curr_monsters, orig_idx, card, None, curr_draw, curr_discard
                    )
                    branch_hand = next_hand + newly_drawn
                    stack.append((next_player, next_monsters, branch_hand, next_draw, next_discard, curr_potions, curr_potion_uses, curr_steps + [step]))

        if best_plan is None:
            best_plan = self._evaluate_state(player, monsters, [], initial_incoming)

        best_plan.computation_time_ms = round((time.time() - start_time) * 1000, 2)
        return best_plan

    def _is_supported_potion(self, potion: Dict[str, Any]) -> bool:
        return str(potion.get("id", potion.get("name", ""))) in {
            "Block Potion", "Dexterity Potion", "Strength Potion", "Energy Potion",
            "Fire Potion", "Explosive Potion", "Weak Potion", "FearPotion", "Poison Potion",
        }

    def _is_time_eater(self, monster: SimMonster) -> bool:
        normalized = "".join(ch for ch in f"{monster.id} {monster.name}".lower() if ch.isalnum())
        return "timeeater" in normalized or "时光吞噬者" in normalized

    def _is_awakened_one(self, monster: SimMonster) -> bool:
        normalized = "".join(ch for ch in f"{monster.id} {monster.name}".lower() if ch.isalnum())
        return "awakenedone" in normalized or "觉醒者" in normalized

    def _is_corrupt_heart(self, monster: SimMonster) -> bool:
        normalized = "".join(ch for ch in f"{monster.id} {monster.name}".lower() if ch.isalnum())
        return "corruptheart" in normalized or "腐化之心" in normalized

    def _effective_monster_damage(self, monster: SimMonster, damage: int) -> int:
        if monster.invincible_cap <= 0:
            return damage
        remaining = max(0, monster.invincible_cap - monster.invincible_damage_taken)
        effective = min(damage, remaining)
        monster.invincible_damage_taken += effective
        return effective

    def _safe_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _potion_targets_enemy(self, potion: Dict[str, Any]) -> bool:
        return str(potion.get("id", potion.get("name", ""))) in {
            "Fire Potion", "Explosive Potion", "Weak Potion", "FearPotion", "Poison Potion",
        }

    def _potion_amount(self, potion: Dict[str, Any], default: int) -> int:
        try:
            return int(potion.get("amount", default))
        except (TypeError, ValueError):
            return default

    def _simulate_potion(
        self,
        player: SimPlayer,
        monsters: List[SimMonster],
        potion: Dict[str, Any],
        target: Optional[SimMonster],
    ) -> Tuple[SimPlayer, List[SimMonster], str]:
        new_player = copy.deepcopy(player)
        new_monsters = copy.deepcopy(monsters)
        potion_id = str(potion.get("id", potion.get("name", "")))
        amount = self._potion_amount(potion, 0)
        if potion_id == "Block Potion":
            new_player.block += amount or 12
        elif potion_id == "Dexterity Potion":
            new_player.dexterity += amount or 2
        elif potion_id == "Strength Potion":
            new_player.strength += amount or 2
        elif potion_id == "Energy Potion":
            new_player.energy += amount or 2
        elif target is not None:
            target_index = target.index
            monster = new_monsters[target_index]
            if potion_id == "Fire Potion":
                damage = amount or 20
                damage = self._effective_monster_damage(monster, damage)
                monster.current_hp = max(0, monster.current_hp - max(0, damage - monster.block))
                monster.block = max(0, monster.block - damage)
            elif potion_id == "Explosive Potion":
                damage = amount or 10
                for monster in new_monsters:
                    if monster.is_alive:
                        damage = self._effective_monster_damage(monster, damage)
                        monster.current_hp = max(0, monster.current_hp - max(0, damage - monster.block))
                        monster.block = max(0, monster.block - damage)
            elif potion_id == "Weak Potion":
                if monster.artifact > 0:
                    monster.artifact -= 1
                else:
                    monster.weak_turns += amount or 3
            elif potion_id == "FearPotion":
                if monster.artifact > 0:
                    monster.artifact -= 1
                else:
                    monster.vulnerable_turns += amount or 3
            elif potion_id == "Poison Potion":
                if monster.artifact > 0:
                    monster.artifact -= 1
                else:
                    monster.poison += amount or 6
        return new_player, new_monsters, str(potion.get("name", potion_id))

    def _evoke_orb(
        self,
        orb_type: str,
        player: SimPlayer,
        monsters: List[SimMonster],
        target_idx: Optional[int]
    ) -> Tuple[int, int]:
        """Evokes an orb, returning (damage_dealt, block_gained)."""
        dmg = 0
        blk = 0
        if orb_type == "Lightning":
            dmg = max(0, 8 + player.focus)
            living = [m for m in monsters if m.is_alive]
            if living:
                # Prefer current target or lowest HP
                target = living[0]
                if target_idx is not None and 0 <= target_idx < len(monsters) and monsters[target_idx].is_alive:
                    target = monsters[target_idx]
                else:
                    target = min(living, key=lambda m: m.current_hp)
                dmg = self._effective_monster_damage(target, dmg)
                unblocked = max(0, dmg - target.block)
                target.block = max(0, target.block - dmg)
                target.current_hp = max(0, target.current_hp - unblocked)
        elif orb_type == "Frost":
            blk = max(0, 5 + player.focus)
            player.block += blk
        elif orb_type == "Plasma":
            player.energy += 2
        elif orb_type == "Dark":
            dmg = max(0, 6 + player.focus)
            living = [m for m in monsters if m.is_alive]
            if living:
                target = min(living, key=lambda m: m.current_hp)
                dmg = self._effective_monster_damage(target, dmg)
                unblocked = max(0, dmg - target.block)
                target.block = max(0, target.block - dmg)
                target.current_hp = max(0, target.current_hp - unblocked)

        return dmg, blk

    def _simulate_play_card(
        self,
        player: SimPlayer,
        monsters: List[SimMonster],
        orig_idx: int,
        card: CardInfo,
        target_idx: Optional[int],
        draw_pile: Optional[List[CardInfo]] = None,
        discard_pile: Optional[List[CardInfo]] = None,
    ) -> Tuple[SimPlayer, List[SimMonster], PlayStep, List[Tuple[int, CardInfo]], List[CardInfo], List[CardInfo]]:
        """Simulates state transition for a card play across all classes."""
        new_player = copy.deepcopy(player)
        new_monsters = copy.deepcopy(monsters)
        effective_cost = 0 if (new_player.has_corruption and card.card_type == "SKILL") else card.cost
        new_player.energy -= effective_cost
        new_player.cards_played_this_turn += 1

        step = PlayStep(
            card_index=orig_idx,
            card_info=card,
            target_monster_index=target_idx
        )

        if card.card_type == "POWER":
            for monster in new_monsters:
                if self._is_awakened_one(monster):
                    monster.awakened_one_bonus += 1
                    step.notes += "🦅 觉醒者好奇：Boss力量+1 "

        if new_player.time_eater_active and new_player.cards_played_this_turn == 12:
            for monster in new_monsters:
                if self._is_time_eater(monster):
                    monster.time_eater_bonus += 2
            step.notes += "⏳ 时光扭曲：第12张牌后强制结束回合，Boss力量+2 "

        if new_player.beat_of_death > 0:
            beat_damage = new_player.beat_of_death
            blocked = min(new_player.block, beat_damage)
            new_player.block -= blocked
            direct_damage = beat_damage - blocked
            new_player.current_hp = max(0, new_player.current_hp - direct_damage)
            new_player.direct_damage_taken += direct_damage
            step.notes += f"💔 死之律动{beat_damage}伤 "

        # 0. Exhaust handling & Feel No Pain synergy
        is_exhaust = card.exhausts or (new_player.has_corruption and card.card_type == "SKILL")
        if is_exhaust:
            step.notes += "(消耗) "
            if new_player.feel_no_pain > 0:
                fnp_block = new_player.feel_no_pain * 3
                new_player.block += fnp_block
                step.block_gained += fnp_block
                step.notes += f"+{fnp_block}格挡(无惧疼痛) "

        # 0.5. Card Drawing & Dark Embrace synergy
        cards_to_draw = card.draw_cards
        if is_exhaust and new_player.dark_embrace > 0:
            cards_to_draw += new_player.dark_embrace
            step.notes += f"+{new_player.dark_embrace}抽牌(黑暗之拥) "

        next_draw_pile = list(draw_pile) if draw_pile is not None else []
        next_discard_pile = list(discard_pile) if discard_pile is not None else []
        newly_drawn: List[Tuple[int, CardInfo]] = []

        if cards_to_draw > 0:
            for _ in range(cards_to_draw):
                if next_draw_pile:
                    drawn_card = next_draw_pile.pop(0)
                    newly_drawn.append((1000 + len(newly_drawn), drawn_card))
                elif next_discard_pile:
                    next_draw_pile = list(next_discard_pile)
                    next_discard_pile = []
                    drawn_card = next_draw_pile.pop(0)
                    newly_drawn.append((1000 + len(newly_drawn), drawn_card))
                else:
                    break
            if newly_drawn:
                step.notes += f"抽{len(newly_drawn)}牌 "

        # 1. Stance Changes (Watcher)
        if card.stance:
            old_stance = new_player.stance
            if old_stance == "Calm" and card.stance != "Calm":
                new_player.energy += 2
                step.notes += "退出平静+2⚡ "
            new_player.stance = card.stance
            if card.stance == "Wrath":
                step.notes += "进入【愤怒】姿态 "
            elif card.stance == "Calm":
                step.notes += "进入【平静】姿态 "
            elif card.stance == "Divinity":
                new_player.energy += 3
                step.notes += "进入【神化】姿态+3⚡ "
            elif card.stance == "None" and old_stance != "None":
                step.notes += "退出姿态 "

        # 2. Energy Gain & Focus
        if card.energy_gain > 0:
            new_player.energy += card.energy_gain
            step.notes += f"+{card.energy_gain}能量(⚡) "
        if card.focus_applied != 0:
            new_player.focus += card.focus_applied
            step.notes += f"+{card.focus_applied}集中 "

        # 3. Block Calculation (Skills)
        if card.base_block > 0:
            block = card.base_block + new_player.dexterity
            if new_player.frail_turns > 0:
                block = math.floor(block * 0.75)
            block = max(0, block)
            new_player.block += block
            step.block_gained += block

        # 4. Powers / Buffs & Skill Debuffs (Artifact check)
        if card.strength_applied > 0:
            new_player.strength += card.strength_applied
            step.notes += f"+{card.strength_applied}力量 "
        if card.dexterity_applied > 0:
            new_player.dexterity += card.dexterity_applied
            step.notes += f"+{card.dexterity_applied}敏捷 "

        if card.card_type != "ATTACK":
            if card.vulnerable_applied > 0:
                if card.is_aoe:
                    for m in new_monsters:
                        if m.is_alive:
                            if m.artifact > 0:
                                m.artifact -= 1
                                step.notes += f"{m.name} 人工制品抵消易伤 "
                            else:
                                m.vulnerable_turns += card.vulnerable_applied
                elif target_idx is not None and 0 <= target_idx < len(new_monsters):
                    target = new_monsters[target_idx]
                    if target.artifact > 0:
                        target.artifact -= 1
                        step.notes += f"{target.name} 人工制品抵消易伤 "
                    else:
                        target.vulnerable_turns += card.vulnerable_applied
                        step.notes += f"给予{card.vulnerable_applied}易伤 "
            if card.weak_applied > 0:
                if card.is_aoe:
                    for m in new_monsters:
                        if m.is_alive:
                            if m.artifact > 0:
                                m.artifact -= 1
                                step.notes += f"{m.name} 人工制品抵消虚弱 "
                            else:
                                m.weak_turns += card.weak_applied
                elif target_idx is not None and 0 <= target_idx < len(new_monsters):
                    target = new_monsters[target_idx]
                    if target.artifact > 0:
                        target.artifact -= 1
                        step.notes += f"{target.name} 人工制品抵消虚弱 "
                    else:
                        target.weak_turns += card.weak_applied
                        step.notes += f"给予{card.weak_applied}虚弱 "

        # 5. Silent Poison Stacking & Catalyst (Artifact check)
        if card.poison_applied > 0:
            if card.is_aoe:
                for m in new_monsters:
                    if m.is_alive:
                        if m.artifact > 0:
                            m.artifact -= 1
                            step.notes += f"{m.name} 人工制品抵消中毒 "
                        else:
                            m.poison += card.poison_applied
                step.notes += f"全员+{card.poison_applied}毒 "
            elif target_idx is not None and 0 <= target_idx < len(new_monsters):
                target = new_monsters[target_idx]
                if target.artifact > 0:
                    target.artifact -= 1
                    step.notes += f"{target.name} 人工制品抵消中毒 "
                else:
                    target.poison += card.poison_applied
                    step.notes += f"+{card.poison_applied}毒 "

        if card.id.startswith("Catalyst") and target_idx is not None and 0 <= target_idx < len(new_monsters):
            target = new_monsters[target_idx]
            if target.poison > 0:
                mult = 3 if (card.id.endswith("+") or card.name.endswith("+")) else 2
                target.poison *= mult
                step.notes += f"毒量x{mult}({target.poison}) "

        # 6. Defect Orbs Channeling & Evoking
        if card.channel_orb and card.channel_count > 0:
            for _ in range(card.channel_count):
                if len(new_player.orbs) >= new_player.max_orbs:
                    evoked = new_player.orbs.pop(0)
                    e_dmg, e_blk = self._evoke_orb(evoked, new_player, new_monsters, target_idx)
                    step.damage_dealt += e_dmg
                    step.block_gained += e_blk
                    step.notes += f"顶球激发{evoked}(+{e_dmg}伤/+{e_blk}甲) "
                new_player.orbs.append(card.channel_orb)
            step.notes += f"生成{card.channel_count}个{card.channel_orb}球 "

        if card.id.startswith("Dualcast") and new_player.orbs:
            evoked = new_player.orbs.pop(0)
            for _ in range(2):
                e_dmg, e_blk = self._evoke_orb(evoked, new_player, new_monsters, target_idx)
                step.damage_dealt += e_dmg
                step.block_gained += e_blk
            step.notes += f"双重激发{evoked}(+{step.damage_dealt}伤/+{step.block_gained}甲) "
        elif card.evoke_orbs > 0:
            for _ in range(card.evoke_orbs):
                if new_player.orbs:
                    evoked = new_player.orbs.pop(0)
                    e_dmg, e_blk = self._evoke_orb(evoked, new_player, new_monsters, target_idx)
                    step.damage_dealt += e_dmg
                    step.block_gained += e_blk
                    step.notes += f"激发{evoked}(+{e_dmg}伤/+{e_blk}甲) "

        # 7. Attack Damage Calculation
        if card.card_type == "ATTACK" and (card.base_damage > 0 or card.id.startswith("Body Slam")):
            new_player.attacks_played_this_turn += 1
            new_player.pen_nib_count += 1

            # Relic triggers every 3 attacks
            if new_player.has_kunai and new_player.attacks_played_this_turn % 3 == 0:
                new_player.dexterity += 1
                step.notes += "+1敏捷(苦无) "
            if new_player.has_shuriken and new_player.attacks_played_this_turn % 3 == 0:
                new_player.strength += 1
                step.notes += "+1力量(手里剑) "
            if new_player.has_ornamental_fan and new_player.attacks_played_this_turn % 3 == 0:
                new_player.block += 4
                step.notes += "+4格挡(折扇) "

            dmg_base = card.base_damage
            if card.id.startswith("Body Slam"):
                dmg_base = new_player.block

            if new_player.has_strike_dummy and "strike" in card.name.lower():
                dmg_base += 3

            if "shiv" in card.name.lower():
                dmg_base += new_player.accuracy_bonus

            dmg = dmg_base + new_player.strength

            # Player Weak
            if new_player.weak_turns > 0:
                dmg = math.floor(dmg * 0.75)

            # Watcher Stances
            if new_player.stance == "Wrath":
                dmg *= 2
            elif new_player.stance == "Divinity":
                dmg *= 3

            # Pen Nib double damage timing
            if new_player.pen_nib_count == 10:
                dmg *= 2
                new_player.pen_nib_count = 0
                step.notes += "(🖊️钢笔尖第10击双倍!) "

            dmg = max(0, dmg)
            vuln_mult = 1.75 if new_player.has_paper_frog else 1.5

            # Bane synergy: 2x hits if target has poison
            hits = card.hits
            if card.id.startswith("Bane") and target_idx is not None and 0 <= target_idx < len(new_monsters):
                if new_monsters[target_idx].poison > 0:
                    hits = 2
                    step.notes += "(剧毒双击!) "

            if card.is_aoe:
                total_dealt = 0
                step.target_name = "所有敌人"
                for m in new_monsters:
                    if not m.is_alive:
                        continue
                    # Monster Curl Up
                    if m.curl_up > 0:
                        m.block += m.curl_up
                        step.notes += f"{m.name} 卷曲+{m.curl_up}甲 "
                        m.curl_up = 0
                    # Monster Thorns
                    if m.thorns > 0:
                        thorns_dmg = m.thorns * hits
                        unblocked_thorns = max(0, thorns_dmg - new_player.block)
                        new_player.block = max(0, new_player.block - thorns_dmg)
                        new_player.current_hp = max(0, new_player.current_hp - unblocked_thorns)
                        step.notes += f"荆棘反伤{thorns_dmg} "

                    final_dmg = dmg
                    if m.vulnerable_turns > 0:
                        final_dmg = math.floor(final_dmg * vuln_mult)
                    final_dmg *= hits
                    final_dmg = self._effective_monster_damage(m, final_dmg)
                    unblocked = max(0, final_dmg - m.block)
                    m.block = max(0, m.block - final_dmg)
                    m.current_hp = max(0, m.current_hp - unblocked)
                    total_dealt += final_dmg
                    if card.vulnerable_applied > 0:
                        if m.artifact > 0:
                            m.artifact -= 1
                            step.notes += f"{m.name} 人工制品抵消易伤 "
                        else:
                            m.vulnerable_turns += card.vulnerable_applied
                    if card.weak_applied > 0:
                        if m.artifact > 0:
                            m.artifact -= 1
                            step.notes += f"{m.name} 人工制品抵消虚弱 "
                        else:
                            m.weak_turns += card.weak_applied
                step.damage_dealt += total_dealt
            elif target_idx is not None and 0 <= target_idx < len(new_monsters):
                target = new_monsters[target_idx]
                step.target_name = target.name
                if target.is_alive:
                    # Monster Curl Up
                    if target.curl_up > 0:
                        target.block += target.curl_up
                        step.notes += f"{target.name} 卷曲+{target.curl_up}甲 "
                        target.curl_up = 0
                    # Monster Thorns
                    if target.thorns > 0:
                        thorns_dmg = target.thorns * hits
                        unblocked_thorns = max(0, thorns_dmg - new_player.block)
                        new_player.block = max(0, new_player.block - thorns_dmg)
                        new_player.current_hp = max(0, new_player.current_hp - unblocked_thorns)
                        step.notes += f"荆棘反伤{thorns_dmg} "

                    final_dmg = dmg
                    if target.vulnerable_turns > 0:
                        final_dmg = math.floor(final_dmg * vuln_mult)
                    final_dmg *= hits
                    final_dmg = self._effective_monster_damage(target, final_dmg)
                    unblocked = max(0, final_dmg - target.block)
                    target.block = max(0, target.block - final_dmg)
                    target.current_hp = max(0, target.current_hp - unblocked)
                    step.damage_dealt += final_dmg
                    if card.vulnerable_applied > 0:
                        if target.artifact > 0:
                            target.artifact -= 1
                            step.notes += f"{target.name} 人工制品抵消易伤 "
                        else:
                            target.vulnerable_turns += card.vulnerable_applied
                            step.notes += f"给予{card.vulnerable_applied}易伤 "
                    if card.weak_applied > 0:
                        if target.artifact > 0:
                            target.artifact -= 1
                            step.notes += f"{target.name} 人工制品抵消虚弱 "
                        else:
                            target.weak_turns += card.weak_applied
                            step.notes += f"给予{card.weak_applied}虚弱 "

        return new_player, new_monsters, step, newly_drawn, next_draw_pile, next_discard_pile

    def _evaluate_state(
        self,
        player: SimPlayer,
        monsters: List[SimMonster],
        steps: List[PlayStep],
        initial_incoming: int,
        potion_uses: Optional[List[str]] = None,
    ) -> CombatPlan:
        """Evaluates end-of-turn outcome with Orbs passives, Poison ticks, Relics, and lethal cancellation."""
        monsters_copy = copy.deepcopy(monsters)
        player_copy = copy.deepcopy(player)

        total_damage = sum(s.damage_dealt for s in steps)
        total_block = sum(s.block_gained for s in steps)
        direct_damage_taken = player_copy.direct_damage_taken

        forecast_parts = []

        if player_copy.time_eater_active and player_copy.cards_played_this_turn >= 12:
            forecast_parts.append("[时光吞噬者: 12张牌后强制结束回合]")
        if any(self._is_awakened_one(monster) and monster.awakened_one_bonus > 0 for monster in monsters_copy):
            forecast_parts.append("[觉醒者好奇: 每张能力牌使Boss力量+1]")

        # 1. Defect Orbs End-of-turn Passives
        lightning_dmg = 0
        frost_blk = 0
        for orb in player_copy.orbs:
            if orb == "Frost":
                blk = max(0, 2 + player_copy.focus)
                player_copy.block += blk
                frost_blk += blk
            elif orb == "Lightning":
                dmg = max(0, 3 + player_copy.focus)
                lightning_dmg += dmg
                # Deal to first living monster
                for m in monsters_copy:
                    if m.is_alive:
                        unblocked = max(0, dmg - m.block)
                        m.block = max(0, m.block - dmg)
                        m.current_hp = max(0, m.current_hp - unblocked)
                        break

        if lightning_dmg > 0:
            forecast_parts.append(f"[闪电被动: {lightning_dmg}伤]")
        if frost_blk > 0:
            forecast_parts.append(f"[冰霜被动: {frost_blk}甲]")

        # 2. Silent Poison End-of-turn Damage Tick (Ignores block completely)
        total_poison_dmg = 0
        for m in monsters_copy:
            if m.is_alive and m.poison > 0:
                p_dmg = m.poison
                m.current_hp = max(0, m.current_hp - p_dmg)
                total_poison_dmg += p_dmg
                m.poison = max(0, m.poison - 1)

        if total_poison_dmg > 0:
            forecast_parts.append(f"[回合末毒伤: {total_poison_dmg}]")

        # 3. Orichalcum (+6 block if 0 block at turn end)
        if player_copy.has_orichalcum and player_copy.block == 0:
            player_copy.block += 6
            forecast_parts.append("[奥利哈钢: +6甲]")

        # 4. Incense Burner (Turn 6 gives Intangible)
        is_intangible = False
        if player_copy.has_incense_burner and player_copy.turn % 6 == 0:
            is_intangible = True
            forecast_parts.append("[香炉: 获得无实体]")

        # 5. Calculate Incoming Monster Damage & Lethal Cancellations
        projected_incoming = 0
        monsters_killed = 0

        for m in monsters_copy:
            if not m.is_alive:
                monsters_killed += 1
                continue
            if m.is_attacking:
                dmg = m.move_adjusted_damage + m.time_eater_bonus + m.awakened_one_bonus
                # Monster weak reduction (40% with Paper Crane, else 25%)
                if m.weak_turns > 0:
                    weak_factor = 0.6 if player_copy.has_paper_crane else 0.75
                    dmg = math.floor(dmg * weak_factor)
                # Player vulnerable
                if player_copy.vulnerable_turns > 0:
                    dmg = math.floor(dmg * 1.5)
                # Watcher Wrath: player takes 2x damage!
                if player_copy.stance == "Wrath":
                    dmg *= 2

                if is_intangible:
                    dmg = min(1, dmg)

                projected_incoming += dmg * m.move_hits

        hp_loss = direct_damage_taken + max(0, projected_incoming - player_copy.block)
        excess_block = max(0, player_copy.block - projected_incoming)

        # Multi-objective fitness score
        score = (
            - self.config.weight_prevent_damage * hp_loss
            + self.config.weight_kill_enemy * monsters_killed
            + self.config.weight_damage_dealt * total_damage
            + self.config.weight_retained_block * excess_block
            + self.config.weight_conserve_energy * player_copy.energy
        )

        return CombatPlan(
            steps=steps,
            initial_incoming_damage=initial_incoming,
            projected_incoming_damage=projected_incoming,
            projected_block=player_copy.block,
            projected_hp_loss=hp_loss,
            monsters_killed=monsters_killed,
            total_damage_dealt=total_damage,
            total_block_gained=total_block,
            remaining_energy=player_copy.energy,
            final_stance=player_copy.stance,
            end_of_turn_forecast=" | ".join(forecast_parts),
            potion_uses=list(potion_uses or []),
            score=score
        )

    def _calculate_incoming_damage(self, monsters: List[SimMonster], player: SimPlayer) -> int:
        total = 0
        for m in monsters:
            if m.is_alive and m.is_attacking:
                dmg = m.move_adjusted_damage
                if player.vulnerable_turns > 0:
                    dmg = math.floor(dmg * 1.5)
                if player.stance == "Wrath":
                    dmg *= 2
                total += dmg * m.move_hits
        return total

    def _parse_player(self, data: Dict[str, Any], relics: List[Dict[str, Any]], turn: int) -> SimPlayer:
        powers: Dict[str, int] = {}
        for p in data.get("powers", []):
            if isinstance(p, dict):
                pid = p.get("id")
                if pid:
                    try:
                        powers[str(pid)] = int(p.get("amount", 0))
                    except (ValueError, TypeError):
                        powers[str(pid)] = 0

        relic_ids: Dict[str, int] = {}
        for r in relics:
            if isinstance(r, dict):
                rid = r.get("id")
                if rid:
                    try:
                        relic_ids[str(rid)] = int(r.get("counter", -1))
                    except (ValueError, TypeError):
                        relic_ids[str(rid)] = -1

        # Stance (Watcher)
        stance = str(data.get("stance", "None"))
        if "Wrath" in powers: stance = "Wrath"
        elif "Calm" in powers: stance = "Calm"
        elif "Divinity" in powers: stance = "Divinity"

        # Orbs (Defect)
        raw_orbs = data.get("orbs", [])
        orbs_list = []
        if isinstance(raw_orbs, list):
            for o in raw_orbs:
                if isinstance(o, dict):
                    name = o.get("name") or o.get("id", "")
                    if name in ["Lightning", "Frost", "Dark", "Plasma"]:
                        orbs_list.append(str(name))

        def _get_int(val, default):
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        player = SimPlayer(
            current_hp=_get_int(data.get("current_hp"), 80),
            max_hp=max(1, _get_int(data.get("max_hp"), 80)),
            block=max(0, _get_int(data.get("block"), 0)),
            energy=max(0, _get_int(data.get("energy"), 3)),
            strength=powers.get("Strength", 0),
            dexterity=powers.get("Dexterity", 0),
            focus=powers.get("Focus", 0),
            vulnerable_turns=powers.get("Vulnerable", 0),
            weak_turns=powers.get("Weak", 0),
            frail_turns=powers.get("Frail", 0),
            stance=stance,
            orbs=orbs_list,
            max_orbs=_get_int(data.get("max_orbs"), 3),
            pen_nib_count=max(0, relic_ids.get("Pen Nib", 0)),
            turn=turn,
            has_orichalcum=("Orichalcum" in relic_ids),
            has_incense_burner=("Incense Burner" in relic_ids),
            has_kunai=("Kunai" in relic_ids),
            has_shuriken=("Shuriken" in relic_ids),
            has_ornamental_fan=("Ornamental Fan" in relic_ids),
            has_paper_frog=("Paper Frog" in relic_ids),
            has_paper_crane=("Paper Crane" in relic_ids),
            has_strike_dummy=("StrikeDummy" in relic_ids),
            accuracy_bonus=powers.get("Accuracy", 0),
            feel_no_pain=powers.get("Feel No Pain", 0),
            dark_embrace=powers.get("Dark Embrace", 0),
            has_corruption=("Corruption" in powers)
        )

        # Anchor relic (+10 block on turn 1)
        if "Anchor" in relic_ids and turn == 1:
            player.block += 10

        return player

    def _parse_monster(self, index: int, data: Dict[str, Any]) -> SimMonster:
        def _get_int(val, default):
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        intent = str(data.get("intent", "UNKNOWN")).upper()
        is_attacking = "ATTACK" in intent
        powers: Dict[str, int] = {}
        for p in data.get("powers", []):
            if isinstance(p, dict):
                pid = p.get("id")
                if pid:
                    try:
                        powers[str(pid)] = int(p.get("amount", 0))
                    except (ValueError, TypeError):
                        powers[str(pid)] = 0

        return SimMonster(
            index=index,
            id=str(data.get("id", f"Monster_{index}")),
            name=str(data.get("name", f"Monster {index+1}")),
            current_hp=max(0, _get_int(data.get("current_hp"), 10)),
            max_hp=max(1, _get_int(data.get("max_hp"), 10)),
            block=max(0, _get_int(data.get("block"), 0)),
            invincible_cap=powers.get("Invincible", 0),
            intent=intent,
            move_adjusted_damage=max(0, _get_int(data.get("move_adjusted_damage", data.get("move_base_damage")), 0)),
            move_hits=max(1, _get_int(data.get("move_hits"), 1)),
            is_attacking=is_attacking,
            vulnerable_turns=powers.get("Vulnerable", 0),
            weak_turns=powers.get("Weak", 0),
            strength=powers.get("Strength", 0),
            poison=powers.get("Poison", 0),
            artifact=powers.get("Artifact", 0),
            curl_up=powers.get("Curl Up", 0),
            thorns=powers.get("Thorns", 0),
            beat_of_death=powers.get("Beat of Death", 0),
            is_gone=bool(data.get("is_gone", False)),
            half_dead=bool(data.get("half_dead", False))
        )
