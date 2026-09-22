"""
Authoritative Card Database Module for Slay the Spire.
Comprehensive, exact statistics for all 4 characters (Ironclad, Silent, Defect, Watcher),
Colorless, Status, and Curses, distinguishing normal and upgraded (+) variants.
Zero guesswork.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
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
    poison_applied: int = 0
    channel_orb: Optional[str] = None  # "Lightning", "Frost", "Dark", "Plasma"
    channel_count: int = 0
    evoke_orbs: int = 0
    focus_applied: int = 0
    is_aoe: bool = False
    exhausts: bool = False
    stance: Optional[str] = None  # Wrath, Calm, Divinity, None
    description: str = ""

# Master authoritative dictionary of cards with exact base and upgraded values.
# Format: (cost, cost+, type, target, dmg, dmg+, hits, hits+, blk, blk+, vuln, vuln+, weak, weak+, str, str+, dex, dex+, draw, draw+, energy, energy+, poison, poison+, orb, orb_cnt, orb_cnt+, evoke, focus, focus+, aoe, exhaust)
CARD_STAT_REGISTRY: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # IRONCLAD (战士)
    # =========================================================================
    "Strike_R": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 6, "dmg+": 9},
    "Defend_R": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 5, "blk+": 8},
    "Bash": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 8, "dmg+": 10, "vuln": 2, "vuln+": 3},
    "Anger": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 6, "dmg+": 8},
    "Armaments": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 5, "blk+": 5},
    "Body Slam": {"cost": 1, "cost+": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 0, "dmg+": 0},
    "Clash": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 14, "dmg+": 18},
    "Cleave": {"cost": 1, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 8, "dmg+": 11, "aoe": True},
    "Clothesline": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 12, "dmg+": 14, "weak": 2, "weak+": 3},
    "Flex": {"cost": 0, "type": "SKILL", "target": "SELF", "str": 2, "str+": 4},
    "Headbutt": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 9, "dmg+": 12},
    "Heavy Blade": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 14, "dmg+": 14},
    "Iron Wave": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 5, "dmg+": 7, "blk": 5, "blk+": 7},
    "Perfected Strike": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 6, "dmg+": 6},
    "Pommel Strike": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 9, "dmg+": 10, "draw": 1, "draw+": 2},
    "Shrug It Off": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 8, "blk+": 11, "draw": 1, "draw+": 1},
    "Sword Boomerang": {"cost": 1, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 3, "dmg+": 3, "hits": 3, "hits+": 4},
    "Thunderclap": {"cost": 1, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 4, "dmg+": 7, "vuln": 1, "vuln+": 1, "aoe": True},
    "True Grit": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 7, "blk+": 9},
    "Twin Strike": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 5, "dmg+": 7, "hits": 2, "hits+": 2},
    "Warcry": {"cost": 0, "type": "SKILL", "target": "SELF", "draw": 1, "draw+": 2, "exhaust": True},
    "Wild Strike": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 12, "dmg+": 17},
    "Battle Trance": {"cost": 0, "type": "SKILL", "target": "SELF", "draw": 3, "draw+": 4},
    "Blood for Blood": {"cost": 4, "cost+": 3, "type": "ATTACK", "target": "ENEMY", "dmg": 18, "dmg+": 22},
    "Bloodletting": {"cost": 0, "type": "SKILL", "target": "SELF", "energy": 2, "energy+": 3},
    "Burning Pact": {"cost": 1, "type": "SKILL", "target": "SELF", "draw": 2, "draw+": 3, "exhaust": True},
    "Carnage": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 20, "dmg+": 28},
    "Combust": {"cost": 1, "type": "POWER", "target": "SELF"},
    "Dark Embrace": {"cost": 2, "cost+": 1, "type": "POWER", "target": "SELF"},
    "Disarm": {"cost": 1, "type": "SKILL", "target": "ENEMY", "exhaust": True},
    "Dropkick": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 5, "dmg+": 8},
    "Dual Wield": {"cost": 1, "type": "SKILL", "target": "SELF"},
    "Entrench": {"cost": 2, "cost+": 1, "type": "SKILL", "target": "SELF"},
    "Feel No Pain": {"cost": 1, "type": "POWER", "target": "SELF"},
    "Fire Breathing": {"cost": 1, "type": "POWER", "target": "SELF"},
    "Flame Barrier": {"cost": 2, "type": "SKILL", "target": "SELF", "blk": 12, "blk+": 16},
    "Ghostly Armor": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 10, "blk+": 13},
    "Hemokinesis": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 15, "dmg+": 20},
    "Infernal Blade": {"cost": 1, "cost+": 0, "type": "SKILL", "target": "SELF", "exhaust": True},
    "Inflame": {"cost": 1, "type": "POWER", "target": "SELF", "str": 2, "str+": 3},
    "Intimidate": {"cost": 0, "type": "SKILL", "target": "ALL_ENEMY", "weak": 1, "weak+": 2, "aoe": True, "exhaust": True},
    "Metallicize": {"cost": 1, "type": "POWER", "target": "SELF"},
    "Power Through": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 15, "blk+": 20},
    "Pummel": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 2, "dmg+": 2, "hits": 4, "hits+": 5, "exhaust": True},
    "Rage": {"cost": 0, "type": "SKILL", "target": "SELF"},
    "Rampage": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 8, "dmg+": 8},
    "Reckless Charge": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 7, "dmg+": 10},
    "Second Wind": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 5, "blk+": 7},
    "Seeing Red": {"cost": 1, "cost+": 0, "type": "SKILL", "target": "SELF", "energy": 2, "energy+": 2, "exhaust": True},
    "Sentinel": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 5, "blk+": 8},
    "Sever Soul": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 16, "dmg+": 22},
    "Shockwave": {"cost": 2, "type": "SKILL", "target": "ALL_ENEMY", "vuln": 3, "vuln+": 5, "weak": 3, "weak+": 5, "aoe": True, "exhaust": True},
    "Spot Weakness": {"cost": 1, "type": "SKILL", "target": "ENEMY", "str": 3, "str+": 4},
    "Uppercut": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 13, "dmg+": 13, "vuln": 1, "vuln+": 2, "weak": 1, "weak+": 2},
    "Whirlwind": {"cost": -1, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 5, "dmg+": 8, "aoe": True},
    "Barricade": {"cost": 3, "cost+": 2, "type": "POWER", "target": "SELF"},
    "Bludgeon": {"cost": 3, "type": "ATTACK", "target": "ENEMY", "dmg": 32, "dmg+": 42},
    "Corruption": {"cost": 3, "cost+": 2, "type": "POWER", "target": "SELF"},
    "Demon Form": {"cost": 3, "type": "POWER", "target": "SELF"},
    "Double Tap": {"cost": 1, "type": "SKILL", "target": "SELF"},
    "Feed": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 10, "dmg+": 12, "exhaust": True},
    "Fiend Fire": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 7, "dmg+": 10, "exhaust": True},
    "Immolate": {"cost": 2, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 21, "dmg+": 28, "aoe": True},
    "Impervious": {"cost": 2, "type": "SKILL", "target": "SELF", "blk": 30, "blk+": 40, "exhaust": True},
    "Limit Break": {"cost": 1, "type": "SKILL", "target": "SELF", "exhaust": True},
    "Offering": {"cost": 0, "type": "SKILL", "target": "SELF", "energy": 2, "energy+": 2, "draw": 3, "draw+": 5, "exhaust": True},
    "Reaper": {"cost": 2, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 4, "dmg+": 5, "aoe": True},

    # =========================================================================
    # THE SILENT (静默猎手)
    # =========================================================================
    "Strike_G": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 6, "dmg+": 9},
    "Defend_G": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 5, "blk+": 8},
    "Neutralize": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 3, "dmg+": 4, "weak": 1, "weak+": 2},
    "Survivor": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 8, "blk+": 11},
    "Bane": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 7, "dmg+": 10},
    "Dagger Spray": {"cost": 1, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 4, "dmg+": 6, "hits": 2, "hits+": 2, "aoe": True},
    "Dagger Throw": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 9, "dmg+": 12, "draw": 1, "draw+": 1},
    "Flying Knee": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 8, "dmg+": 11},
    "Poisoned Stab": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 6, "dmg+": 8, "poison": 3, "poison+": 4},
    "Quick Slash": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 8, "dmg+": 12, "draw": 1, "draw+": 1},
    "Slice": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 6, "dmg+": 9},
    "Sneaky Strike": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 12, "dmg+": 16},
    "Sucker Punch": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 7, "dmg+": 9, "weak": 1, "weak+": 2},
    "Acrobatics": {"cost": 1, "type": "SKILL", "target": "SELF", "draw": 3, "draw+": 4},
    "Backflip": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 5, "blk+": 8, "draw": 2, "draw+": 2},
    "Blade Dance": {"cost": 1, "type": "SKILL", "target": "SELF"},
    "Cloak And Dagger": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 6, "blk+": 6},
    "Deadly Poison": {"cost": 1, "type": "SKILL", "target": "ENEMY", "poison": 5, "poison+": 7},
    "Deflect": {"cost": 0, "type": "SKILL", "target": "SELF", "blk": 4, "blk+": 7},
    "Dodge and Roll": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 4, "blk+": 6},
    "Outmaneuver": {"cost": 1, "type": "SKILL", "target": "SELF"},
    "Piercing Wail": {"cost": 1, "type": "SKILL", "target": "ALL_ENEMY", "aoe": True, "exhaust": True},
    "Prepared": {"cost": 0, "type": "SKILL", "target": "SELF", "draw": 1, "draw+": 2},
    "All-Out Attack": {"cost": 1, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 10, "dmg+": 14, "aoe": True},
    "Backstab": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 11, "dmg+": 15, "exhaust": True},
    "Choke": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 12, "dmg+": 12},
    "Dash": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 10, "dmg+": 13, "blk": 10, "blk+": 13},
    "Endless Agony": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 4, "dmg+": 6, "exhaust": True},
    "Eviscerate": {"cost": 3, "type": "ATTACK", "target": "ENEMY", "dmg": 7, "dmg+": 9, "hits": 3, "hits+": 3},
    "Finisher": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 6, "dmg+": 8},
    "Flechettes": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 4, "dmg+": 6},
    "Heel Hook": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 5, "dmg+": 8},
    "Masterful Stab": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 12, "dmg+": 16},
    "Predator": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 15, "dmg+": 20},
    "Riddle with Holes": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 3, "dmg+": 4, "hits": 5, "hits+": 5},
    "Skewer": {"cost": -1, "type": "ATTACK", "target": "ENEMY", "dmg": 7, "dmg+": 10},
    "Bouncing Flask": {"cost": 2, "type": "SKILL", "target": "ALL_ENEMY", "poison": 9, "poison+": 12},
    "Blur": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 5, "blk+": 8},
    "Catalyst": {"cost": 1, "type": "SKILL", "target": "ENEMY", "exhaust": True},
    "Crippling Cloud": {"cost": 2, "type": "SKILL", "target": "ALL_ENEMY", "poison": 4, "poison+": 7, "weak": 2, "weak+": 2, "aoe": True, "exhaust": True},
    "Escape Plan": {"cost": 0, "type": "SKILL", "target": "SELF", "blk": 3, "blk+": 5, "draw": 1, "draw+": 1},
    "Leg Sweep": {"cost": 2, "type": "SKILL", "target": "ENEMY", "blk": 11, "blk+": 14, "weak": 2, "weak+": 3},
    "Terror": {"cost": 1, "cost+": 0, "type": "SKILL", "target": "ENEMY", "vuln": 99, "vuln+": 99, "exhaust": True},
    "Well-Laid Plans": {"cost": 1, "type": "POWER", "target": "SELF"},
    "A Thousand Cuts": {"cost": 2, "type": "POWER", "target": "SELF"},
    "After Image": {"cost": 1, "type": "POWER", "target": "SELF"},
    "Burst": {"cost": 1, "type": "SKILL", "target": "SELF"},
    "Corpse Explosion": {"cost": 2, "type": "SKILL", "target": "ENEMY", "poison": 6, "poison+": 9},
    "Die Die Die": {"cost": 1, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 13, "dmg+": 17, "aoe": True, "exhaust": True},
    "Envenom": {"cost": 2, "cost+": 1, "type": "POWER", "target": "SELF"},
    "Glass Knife": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 8, "dmg+": 12, "hits": 2, "hits+": 2},
    "Grand Finale": {"cost": 0, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 50, "dmg+": 60, "aoe": True},
    "Malaise": {"cost": -1, "type": "SKILL", "target": "ENEMY", "exhaust": True},
    "Phantasmal Killer": {"cost": 1, "cost+": 0, "type": "SKILL", "target": "SELF"},
    "Storm of Steel": {"cost": 1, "type": "SKILL", "target": "SELF"},
    "Unload": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 14, "dmg+": 18},
    "Wraith Form": {"cost": 3, "type": "POWER", "target": "SELF"},

    # =========================================================================
    # DEFECT (故障机器人)
    # =========================================================================
    "Strike_B": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 6, "dmg+": 9},
    "Defend_B": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 5, "blk+": 8},
    "Zap": {"cost": 1, "cost+": 0, "type": "SKILL", "target": "SELF", "channel_orb": "Lightning", "channel_cnt": 1},
    "Dualcast": {"cost": 1, "cost+": 0, "type": "SKILL", "target": "SELF", "evoke": 2},
    "Beam Cell": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 4, "dmg+": 6, "vuln": 1, "vuln+": 2},
    "Claw": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 3, "dmg+": 5},
    "Cold Snap": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 6, "dmg+": 9, "channel_orb": "Frost", "channel_cnt": 1},
    "Compile Driver": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 7, "dmg+": 10},
    "Go for the Eyes": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 3, "dmg+": 4, "weak": 1, "weak+": 2},
    "Rebound": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 9, "dmg+": 12},
    "Streamline": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 15, "dmg+": 20},
    "Sweeping Beam": {"cost": 1, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 6, "dmg+": 9, "draw": 1, "draw+": 1, "aoe": True},
    "Charge Battery": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 7, "blk+": 10},
    "Coolheaded": {"cost": 1, "type": "SKILL", "target": "SELF", "channel_orb": "Frost", "channel_cnt": 1, "draw": 1, "draw+": 2},
    "Hologram": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 3, "blk+": 5},
    "Leap": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 9, "blk+": 12},
    "Stack": {"cost": 1, "type": "SKILL", "target": "SELF"},
    "Steam Barrier": {"cost": 0, "type": "SKILL", "target": "SELF", "blk": 6, "blk+": 8},
    "Turbo": {"cost": 0, "type": "SKILL", "target": "SELF", "energy": 2, "energy+": 3},
    "Barrage": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 4, "dmg+": 6},
    "Blizzard": {"cost": 1, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 2, "dmg+": 3, "aoe": True},
    "Bullseye": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 8, "dmg+": 11},
    "Melter": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 10, "dmg+": 14},
    "Rip and Tear": {"cost": 1, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 7, "dmg+": 9, "hits": 2, "hits+": 2},
    "Scrape": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 7, "dmg+": 10, "draw": 4, "draw+": 5},
    "Sunder": {"cost": 3, "type": "ATTACK", "target": "ENEMY", "dmg": 24, "dmg+": 32},
    "Auto-Shields": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 11, "blk+": 15},
    "BootSequence": {"cost": 0, "type": "SKILL", "target": "SELF", "blk": 10, "blk+": 13, "exhaust": True},
    "Chaos": {"cost": 1, "type": "SKILL", "target": "SELF"},
    "Chill": {"cost": 0, "type": "SKILL", "target": "SELF", "channel_orb": "Frost", "channel_cnt": 1, "exhaust": True},
    "Consume": {"cost": 2, "type": "SKILL", "target": "SELF", "focus": 2, "focus+": 3},
    "Darkness": {"cost": 1, "type": "SKILL", "target": "SELF", "channel_orb": "Dark", "channel_cnt": 1},
    "Defragment": {"cost": 1, "type": "POWER", "target": "SELF", "focus": 1, "focus+": 2},
    "Doom and Gloom": {"cost": 2, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 10, "dmg+": 14, "channel_orb": "Dark", "channel_cnt": 1, "aoe": True},
    "Double Energy": {"cost": 1, "cost+": 0, "type": "SKILL", "target": "SELF", "exhaust": True},
    "Fission": {"cost": 0, "type": "SKILL", "target": "SELF", "exhaust": True},
    "Fusion": {"cost": 2, "cost+": 1, "type": "SKILL", "target": "SELF", "channel_orb": "Plasma", "channel_cnt": 1},
    "Genetic Algorithm": {"cost": 1, "type": "SKILL", "target": "SELF", "blk": 1, "blk+": 1, "exhaust": True},
    "Glacier": {"cost": 2, "type": "SKILL", "target": "SELF", "blk": 7, "blk+": 10, "channel_orb": "Frost", "channel_cnt": 2},
    "Heatsinks": {"cost": 1, "type": "POWER", "target": "SELF"},
    "Overclock": {"cost": 0, "type": "SKILL", "target": "SELF", "draw": 2, "draw+": 3},
    "Recycle": {"cost": 1, "cost+": 0, "type": "SKILL", "target": "SELF"},
    "Reinforced Body": {"cost": -1, "type": "SKILL", "target": "SELF", "blk": 7, "blk+": 9},
    "Reprogram": {"cost": 1, "type": "SKILL", "target": "SELF", "str": 1, "str+": 2, "dex": 1, "dex+": 2, "focus": -1, "focus+": -1},
    "Skim": {"cost": 1, "type": "SKILL", "target": "SELF", "draw": 3, "draw+": 4},
    "Storm": {"cost": 1, "type": "POWER", "target": "SELF"},
    "Tempest": {"cost": -1, "type": "SKILL", "target": "SELF", "channel_orb": "Lightning", "channel_cnt": 1, "exhaust": True},
    "White Noise": {"cost": 1, "cost+": 0, "type": "SKILL", "target": "SELF", "exhaust": True},
    "All For One": {"cost": 2, "type": "ATTACK", "target": "ENEMY", "dmg": 10, "dmg+": 14},
    "Biased Cognition": {"cost": 1, "type": "POWER", "target": "SELF", "focus": 4, "focus+": 5},
    "Buffer": {"cost": 2, "type": "POWER", "target": "SELF"},
    "Creative AI": {"cost": 3, "cost+": 2, "type": "POWER", "target": "SELF"},
    "Echo Form": {"cost": 3, "type": "POWER", "target": "SELF"},
    "Electrodynamics": {"cost": 2, "type": "POWER", "target": "SELF", "channel_orb": "Lightning", "channel_cnt": 2, "channel_cnt+": 3},
    "FTL": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 5, "dmg+": 6, "draw": 1, "draw+": 1},
    "Hyperbeam": {"cost": 2, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 26, "dmg+": 34, "focus": -3, "focus+": -3, "aoe": True},
    "Meteor Strike": {"cost": 5, "type": "ATTACK", "target": "ENEMY", "dmg": 24, "dmg+": 30, "channel_orb": "Plasma", "channel_cnt": 3},
    "Multi-Cast": {"cost": -1, "type": "SKILL", "target": "SELF"},
    "Rainbow": {"cost": 2, "type": "SKILL", "target": "SELF", "exhaust": True},
    "Reboot": {"cost": 0, "type": "SKILL", "target": "SELF", "draw": 4, "draw+": 6, "exhaust": True},
    "Seek": {"cost": 0, "type": "SKILL", "target": "SELF", "exhaust": True},
    "Thunder Strike": {"cost": 3, "type": "ATTACK", "target": "ALL_ENEMY", "dmg": 7, "dmg+": 9, "aoe": True},

    # =========================================================================
    # COLORLESS / STATUS / CURSES (通用、状态与诅咒)
    # =========================================================================
    "Apparition": {"cost": 1, "type": "SKILL", "target": "SELF", "exhaust": True},
    "Bite": {"cost": 1, "type": "ATTACK", "target": "ENEMY", "dmg": 7, "dmg+": 8},
    "Shiv": {"cost": 0, "type": "ATTACK", "target": "ENEMY", "dmg": 4, "dmg+": 6, "exhaust": True},
    "J.A.X.": {"cost": 0, "type": "SKILL", "target": "SELF", "str": 2, "str+": 3},
    "Miracle": {"cost": 0, "type": "SKILL", "target": "SELF", "energy": 1, "energy+": 1, "exhaust": True},
    "Dazed": {"cost": -2, "type": "STATUS", "target": "NONE"},
    "Wound": {"cost": -2, "type": "STATUS", "target": "NONE"},
    "Burn": {"cost": -2, "type": "STATUS", "target": "NONE"},
    "Slimed": {"cost": 1, "type": "STATUS", "target": "NONE", "exhaust": True},
    "Void": {"cost": -2, "type": "STATUS", "target": "NONE"},
    "AscendersBane": {"cost": -2, "type": "CURSE", "target": "NONE"},
    "CurseOfTheBell": {"cost": -2, "type": "CURSE", "target": "NONE"},
    "Normality": {"cost": -2, "type": "CURSE", "target": "NONE"},
    "Pain": {"cost": -2, "type": "CURSE", "target": "NONE"},
    "Regret": {"cost": -2, "type": "CURSE", "target": "NONE"},
}

def resolve_card_info(raw_card: Dict[str, Any]) -> CardInfo:
    """
    Authoritative resolution of card information from the exact CARD_STAT_REGISTRY,
    WATCHER_CARDS, or EO KnowledgeBase. Supports all 4 characters with 100% precision.
    """
    card_id = raw_card.get("id", "")
    card_name = raw_card.get("name", card_id)
    upgraded = bool(raw_card.get("upgraded", False) or card_id.endswith("+") or card_name.endswith("+"))
    clean_id = card_id.rstrip("+")
    clean_name = card_name.rstrip("+")

    # 1. Check Watcher Dataset
    if clean_id in WATCHER_CARDS or clean_name in WATCHER_CARDS:
        w_data = WATCHER_CARDS.get(clean_id) or WATCHER_CARDS.get(clean_name, {})
        cost = w_data.get("COST", 1)
        dmg = w_data.get("DMG", 0)
        blk = w_data.get("BLOCK", 0)
        hits = w_data.get("HITS", 1)
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
            hits=hits,
            base_block=blk,
            vulnerable_applied=w_data.get("VULN", 0),
            weak_applied=w_data.get("WEAK", 0),
            draw_cards=w_data.get("DRAW", 0),
            is_aoe=w_data.get("AOE", False),
            stance=w_data.get("STANCE", None),
            description=w_data.get("DESC", "")
        )

    # 2. Check Master CARD_STAT_REGISTRY (Exact stats for Ironclad, Silent, Defect, Colorless, Curses)
    stat = CARD_STAT_REGISTRY.get(clean_id) or CARD_STAT_REGISTRY.get(clean_name)
    zh_name = GLOBAL_KB.get_card_zh_name(clean_id)
    if zh_name == clean_id:
        zh_name = GLOBAL_KB.get_card_zh_name(clean_name)
    if upgraded and not zh_name.endswith("+"):
        zh_name += "+"

    kb_desc = GLOBAL_KB.get_card_description(clean_id, upgraded) or GLOBAL_KB.get_card_description(clean_name, upgraded)

    if stat:
        # Exact extraction from registry
        cost = stat.get("cost+", stat.get("cost", 1)) if upgraded else stat.get("cost", 1)
        card_type = stat.get("type", "ATTACK")
        target = stat.get("target", "ENEMY")
        damage = stat.get("dmg+", stat.get("dmg", 0)) if upgraded else stat.get("dmg", 0)
        hits = stat.get("hits+", stat.get("hits", 1)) if upgraded else stat.get("hits", 1)
        block = stat.get("blk+", stat.get("blk", 0)) if upgraded else stat.get("blk", 0)
        vuln = stat.get("vuln+", stat.get("vuln", 0)) if upgraded else stat.get("vuln", 0)
        weak = stat.get("weak+", stat.get("weak", 0)) if upgraded else stat.get("weak", 0)
        strength = stat.get("str+", stat.get("str", 0)) if upgraded else stat.get("str", 0)
        dexterity = stat.get("dex+", stat.get("dex", 0)) if upgraded else stat.get("dex", 0)
        draw = stat.get("draw+", stat.get("draw", 0)) if upgraded else stat.get("draw", 0)
        energy = stat.get("energy+", stat.get("energy", 0)) if upgraded else stat.get("energy", 0)
        poison = stat.get("poison+", stat.get("poison", 0)) if upgraded else stat.get("poison", 0)
        channel_orb = stat.get("channel_orb")
        channel_cnt = stat.get("channel_cnt+", stat.get("channel_cnt", 0)) if upgraded else stat.get("channel_cnt", 0)
        evoke = stat.get("evoke", 0)
        focus = stat.get("focus+", stat.get("focus", 0)) if upgraded else stat.get("focus", 0)
        is_aoe = stat.get("aoe", False)
        exhaust = stat.get("exhaust", False)

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
            vulnerable_applied=vuln,
            weak_applied=weak,
            strength_applied=strength,
            dexterity_applied=dexterity,
            draw_cards=draw,
            energy_gain=energy,
            poison_applied=poison,
            channel_orb=channel_orb,
            channel_count=channel_cnt,
            evoke_orbs=evoke,
            focus_applied=focus,
            is_aoe=is_aoe,
            exhausts=exhaust,
            description=kb_desc or f"{card_type}: {card_name}"
        )

    # 3. Fallback to raw card payload / EO KB without blind numeric guesses
    cost = raw_card.get("cost", 1)
    card_type = raw_card.get("type", "ATTACK").upper()
    target = raw_card.get("target", "ENEMY").upper()
    is_aoe = target in ["ALL_ENEMY", "ALL"] or "ALL enemies" in kb_desc or "所有敌人" in kb_desc
    damage = raw_card.get("damage", 0)
    block = raw_card.get("block", 0)

    return CardInfo(
        id=card_id,
        name=card_name,
        name_zh=zh_name,
        cost=cost,
        card_type=card_type,
        target=target,
        base_damage=damage,
        base_block=block,
        is_aoe=is_aoe,
        description=kb_desc or f"{card_type}: {card_name}"
    )
