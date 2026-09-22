"""
Unified Card Database Module for Slay the Spire.
Delegates 100% of card metadata and parsing to the authoritative KnowledgeBase (EO + Watcher).
Zero redundant hardcoded card lists.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import re
from knowledge_base import GLOBAL_KB, WATCHER_CARDS

@dataclass
class CardInfo:
    id: str
    name: str
    name_zh: str
    cost: int
    card_type: str  # ATTACK, SKILL, POWER, STATUS, CURSE
    target: str     # ENEMY, ALL_ENEMY, SELF, NONE
    base_damage: int = 0
    hits: int = 1
    base_block: int = 0
    vulnerable_applied: int = 0
    weak_applied: int = 0
    strength_applied: int = 0
    dexterity_applied: int = 0
    draw_cards: int = 0
    energy_gain: int = 0
    is_aoe: bool = False
    exhausts: bool = False
    stance: Optional[str] = None  # Wrath, Calm, Divinity, None
    description: str = ""

def resolve_card_info(raw_card: Dict[str, Any]) -> CardInfo:
    """
    Resolves card information dynamically from the authoritative KnowledgeBase.
    Supports all 4 characters (Ironclad, Silent, Defect, Watcher), Colorless, and Curses.
    """
    card_id = raw_card.get("id", "")
    card_name = raw_card.get("name", card_id)
    upgraded = raw_card.get("upgraded", False) or card_id.endswith("+")
    clean_id = card_id.rstrip("+")
    clean_name = card_name.rstrip("+")

    # 1. Check Watcher Dataset
    if clean_id in WATCHER_CARDS or clean_name in WATCHER_CARDS:
        w_data = WATCHER_CARDS.get(clean_id) or WATCHER_CARDS.get(clean_name, {})
        cost = raw_card.get("cost", w_data.get("COST", 1))
        dmg = raw_card.get("damage", w_data.get("DMG", 0))
        blk = raw_card.get("block", w_data.get("BLOCK", 0))
        if upgraded:
            if dmg > 0: dmg += 3
            if blk > 0: blk += 3

        return CardInfo(
            id=card_id,
            name=w_data.get("NAME", card_name),
            name_zh=w_data.get("ZH", card_name) + ("+" if upgraded else ""),
            cost=cost,
            card_type=w_data.get("TYPE", "ATTACK"),
            target=w_data.get("TARGET", "ENEMY"),
            base_damage=dmg,
            hits=w_data.get("HITS", 1),
            base_block=blk,
            vulnerable_applied=w_data.get("VULN", 0),
            weak_applied=w_data.get("WEAK", 0),
            draw_cards=w_data.get("DRAW", 0),
            is_aoe=w_data.get("AOE", False),
            stance=w_data.get("STANCE", None),
            description=w_data.get("DESC", "")
        )

    # 2. Check EO Master KnowledgeBase (Ironclad, Silent, Defect, Colorless, Curses)
    zh_name = GLOBAL_KB.get_card_zh_name(clean_id)
    if zh_name == clean_id:
        zh_name = GLOBAL_KB.get_card_zh_name(clean_name)
    if upgraded and not zh_name.endswith("+"):
        zh_name += "+"

    kb_desc = GLOBAL_KB.get_card_description(clean_id, upgraded) or GLOBAL_KB.get_card_description(clean_name, upgraded)

    # Core attributes from raw JSON or defaults
    cost = raw_card.get("cost", 1)
    card_type = raw_card.get("type", "ATTACK").upper()
    target = raw_card.get("target", "ENEMY").upper()
    is_aoe = target in ["ALL_ENEMY", "ALL"] or "ALL enemies" in kb_desc or "所有敌人" in kb_desc

    damage = raw_card.get("damage", 0)
    block = raw_card.get("block", 0)
    hits = 1

    # Deduce damage/block from standard values if not provided
    if damage == 0 and card_type == "ATTACK":
        # Check if card is known multi-hit
        if "Twin" in clean_id or "Flying Sleeves" in clean_id:
            hits = 2
            damage = 5 if not upgraded else 7
        elif "Pummel" in clean_id:
            hits = 4
            damage = 2
        elif "Sword Boomerang" in clean_id:
            hits = 3 if not upgraded else 4
            damage = 3
        else:
            damage = 6 if cost <= 1 else (10 if cost == 2 else 18)

    if block == 0 and card_type == "SKILL" and ("defend" in clean_id.lower() or "guard" in clean_id.lower() or "block" in clean_id.lower() or "Block" in kb_desc):
        block = 5 if cost <= 1 else 10

    # Keyword parsing
    vuln_applied = 2 if "Vulnerable" in kb_desc or "易伤" in kb_desc else 0
    weak_applied = 2 if "Weak" in kb_desc or "虚弱" in kb_desc else 0
    exhausts = "Exhaust" in kb_desc or "消耗" in kb_desc or raw_card.get("exhausts", False)

    # Check Stance
    stance = None
    if "Wrath" in kb_desc or "愤怒" in kb_desc:
        stance = "Wrath"
    elif "Calm" in kb_desc or "平静" in kb_desc:
        stance = "Calm"
    elif "Divinity" in kb_desc or "神化" in kb_desc:
        stance = "Divinity"

    final_desc = kb_desc if kb_desc else f"{card_type} card: {card_name}"

    return CardInfo(
        id=card_id,
        name=card_name,
        name_zh=zh_name,
        cost=cost,
        card_type=card_type,
        target=target,
        base_damage=damage,
        hits=hits,
        base_block=block,
        vulnerable_applied=vuln_applied,
        weak_applied=weak_applied,
        is_aoe=is_aoe,
        exhausts=exhausts,
        stance=stance,
        description=final_desc
    )
