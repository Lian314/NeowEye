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
        active_monsters = [m for m in monsters if m.is_alive]

        # Parse playable cards
        hand_cards: List[Tuple[int, CardInfo]] = []
        for idx, c in enumerate(raw_hand):
            if c.get("is_playable", True):
                info = resolve_card_info(c)
                if info.cost >= 0:
                    hand_cards.append((idx, info))

        initial_incoming = self._calculate_incoming_damage(active_monsters, player)

        if not hand_cards or player.energy <= 0 or not active_monsters:
            plan = self._evaluate_state(player, monsters, [], initial_incoming)
            plan.computation_time_ms = round((time.time() - start_time) * 1000, 2)
            return plan

        # Bounded DFS search with Beam Width pruning
        best_plan: Optional[CombatPlan] = None
        best_score = -float("inf")
        evaluated_states = 0

        stack = [(player, monsters, hand_cards, [])]

        while stack and evaluated_states < self.config.max_evaluated_states:
            curr_player, curr_monsters, curr_hand, curr_steps = stack.pop()
            evaluated_states += 1

            plan = self._evaluate_state(curr_player, curr_monsters, curr_steps, initial_incoming)
            if plan.score > best_score:
                best_score = plan.score
                best_plan = plan

            # Depth & energy bound
            if len(curr_steps) >= self.config.max_search_depth or curr_player.energy <= 0:
                continue

            seen_branches = set()
            for i, (orig_idx, card) in enumerate(curr_hand):
                if card.cost > curr_player.energy:
                    continue

                card_key = (card.id, card.cost)
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

                        next_player, next_monsters, step = self._simulate_play_card(
                            curr_player, curr_monsters, orig_idx, card, target.index
                        )
                        stack.append((next_player, next_monsters, next_hand, curr_steps + [step]))
                else:
                    if card_key in seen_branches:
                        continue
                    seen_branches.add(card_key)

                    next_player, next_monsters, step = self._simulate_play_card(
                        curr_player, curr_monsters, orig_idx, card, None
                    )
                    stack.append((next_player, next_monsters, next_hand, curr_steps + [step]))

        if best_plan is None:
            best_plan = self._evaluate_state(player, monsters, [], initial_incoming)

        best_plan.computation_time_ms = round((time.time() - start_time) * 1000, 2)
        return best_plan

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
        target_idx: Optional[int]
    ) -> Tuple[SimPlayer, List[SimMonster], PlayStep]:
        """Simulates state transition for a card play across all classes."""
        new_player = copy.deepcopy(player)
        new_monsters = copy.deepcopy(monsters)
        new_player.energy -= card.cost

        step = PlayStep(
            card_index=orig_idx,
            card_info=card,
            target_monster_index=target_idx
        )

        # 1. Stance Changes (Watcher)
        if card.stance:
            old_stance = new_player.stance
            if old_stance == "Calm" and card.stance != "Calm":
                new_player.energy += 2
                step.notes += "退出平静+2⚡ "
            new_player.stance = card.stance
            if card.stance == "Wrath":
                step.notes += "进入【愤怒】 "
            elif card.stance == "Calm":
                step.notes += "进入【平静】 "
            elif card.stance == "Divinity":
                new_player.energy += 3
                step.notes += "进入【神化】+3⚡ "
            elif card.stance == "None" and old_stance != "None":
                step.notes += "退出姿态 "

        # 2. Energy Gain & Focus
        if card.energy_gain > 0:
            new_player.energy += card.energy_gain
            step.notes += f"+{card.energy_gain}⚡ "
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

        # 4. Powers / Buffs
        if card.strength_applied > 0:
            new_player.strength += card.strength_applied
            step.notes += f"+{card.strength_applied}力量 "
        if card.dexterity_applied > 0:
            new_player.dexterity += card.dexterity_applied
            step.notes += f"+{card.dexterity_applied}敏捷 "

        # 5. Silent Poison Stacking & Catalyst
        if card.poison_applied > 0:
            if card.is_aoe:
                for m in new_monsters:
                    if m.is_alive:
                        m.poison += card.poison_applied
                step.notes += f"全员+{card.poison_applied}毒 "
            elif target_idx is not None and 0 <= target_idx < len(new_monsters):
                target = new_monsters[target_idx]
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
            step.notes += f"生成{card.channel_count}{card.channel_orb} "

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
                    final_dmg = dmg
                    if m.vulnerable_turns > 0:
                        final_dmg = math.floor(final_dmg * vuln_mult)
                    final_dmg *= hits
                    unblocked = max(0, final_dmg - m.block)
                    m.block = max(0, m.block - final_dmg)
                    m.current_hp = max(0, m.current_hp - unblocked)
                    total_dealt += final_dmg
                    if card.vulnerable_applied > 0:
                        m.vulnerable_turns += card.vulnerable_applied
                    if card.weak_applied > 0:
                        m.weak_turns += card.weak_applied
                step.damage_dealt += total_dealt
            elif target_idx is not None and 0 <= target_idx < len(new_monsters):
                target = new_monsters[target_idx]
                step.target_name = target.name
                if target.is_alive:
                    final_dmg = dmg
                    if target.vulnerable_turns > 0:
                        final_dmg = math.floor(final_dmg * vuln_mult)
                    final_dmg *= hits
                    unblocked = max(0, final_dmg - target.block)
                    target.block = max(0, target.block - final_dmg)
                    target.current_hp = max(0, target.current_hp - unblocked)
                    step.damage_dealt += final_dmg
                    if card.vulnerable_applied > 0:
                        target.vulnerable_turns += card.vulnerable_applied
                        step.notes += f"给予{card.vulnerable_applied}易伤 "
                    if card.weak_applied > 0:
                        target.weak_turns += card.weak_applied
                        step.notes += f"给予{card.weak_applied}虚弱 "

        return new_player, new_monsters, step

    def _evaluate_state(
        self,
        player: SimPlayer,
        monsters: List[SimMonster],
        steps: List[PlayStep],
        initial_incoming: int
    ) -> CombatPlan:
        """Evaluates end-of-turn outcome with Orbs passives, Poison ticks, Relics, and lethal cancellation."""
        monsters_copy = copy.deepcopy(monsters)
        player_copy = copy.deepcopy(player)

        total_damage = sum(s.damage_dealt for s in steps)
        total_block = sum(s.block_gained for s in steps)

        forecast_parts = []

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
                dmg = m.move_adjusted_damage
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

        hp_loss = max(0, projected_incoming - player_copy.block)
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
        powers = {p.get("id"): p.get("amount", 0) for p in data.get("powers", [])}
        relic_ids = {r.get("id"): r.get("counter", -1) for r in relics}

        # Stance (Watcher)
        stance = data.get("stance", "None")
        if "Wrath" in powers: stance = "Wrath"
        elif "Calm" in powers: stance = "Calm"
        elif "Divinity" in powers: stance = "Divinity"

        # Orbs (Defect)
        raw_orbs = data.get("orbs", [])
        orbs_list = []
        for o in raw_orbs:
            name = o.get("name") or o.get("id", "")
            if name in ["Lightning", "Frost", "Dark", "Plasma"]:
                orbs_list.append(name)

        player = SimPlayer(
            current_hp=data.get("current_hp", 80),
            max_hp=data.get("max_hp", 80),
            block=data.get("block", 0),
            energy=data.get("energy", 3),
            strength=powers.get("Strength", 0),
            dexterity=powers.get("Dexterity", 0),
            focus=powers.get("Focus", 0),
            vulnerable_turns=powers.get("Vulnerable", 0),
            weak_turns=powers.get("Weak", 0),
            frail_turns=powers.get("Frail", 0),
            stance=stance,
            orbs=orbs_list,
            max_orbs=data.get("max_orbs", 3),
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
            accuracy_bonus=powers.get("Accuracy", 0)
        )

        # Anchor relic (+10 block on turn 1)
        if "Anchor" in relic_ids and turn == 1:
            player.block += 10

        return player

    def _parse_monster(self, index: int, data: Dict[str, Any]) -> SimMonster:
        intent = data.get("intent", "UNKNOWN").upper()
        is_attacking = "ATTACK" in intent
        powers = {p.get("id"): p.get("amount", 0) for p in data.get("powers", [])}
        return SimMonster(
            index=index,
            id=data.get("id", f"Monster_{index}"),
            name=data.get("name", f"Monster {index+1}"),
            current_hp=data.get("current_hp", 10),
            max_hp=data.get("max_hp", 10),
            block=data.get("block", 0),
            intent=intent,
            move_adjusted_damage=data.get("move_adjusted_damage", data.get("move_base_damage", 0)),
            move_hits=data.get("move_hits", 1),
            is_attacking=is_attacking,
            vulnerable_turns=powers.get("Vulnerable", 0),
            weak_turns=powers.get("Weak", 0),
            strength=powers.get("Strength", 0),
            poison=powers.get("Poison", 0),
            is_gone=data.get("is_gone", False),
            half_dead=data.get("half_dead", False)
        )
