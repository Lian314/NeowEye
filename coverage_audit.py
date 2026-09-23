"""Audit data coverage separately from combat simulation coverage."""
import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set

from card_db import CARD_STAT_REGISTRY
from knowledge_base import EO_DATA_DIR, GLOBAL_KB, RELIC_ZH_MAP, WATCHER_CARDS


CARD_FIELD_SPECS = {
    "base_damage": {"registry": ("dmg", "dmg+"), "tests": ("total_damage_dealt", "projected_hp_loss")},
    "hits": {"registry": ("hits", "hits+"), "tests": ("hits", "damage")},
    "base_block": {"registry": ("blk", "blk+"), "tests": ("block", "projected_block")},
    "vulnerable_applied": {"registry": ("vuln", "vuln+"), "tests": ("vulnerable", "易伤")},
    "weak_applied": {"registry": ("weak", "weak+"), "tests": ("weak", "虚弱")},
    "strength_applied": {"registry": ("str", "str+"), "tests": ("strength", "力量")},
    "dexterity_applied": {"registry": ("dex", "dex+"), "tests": ("dexterity", "敏捷")},
    "draw_cards": {"registry": ("draw", "draw+"), "tests": ("draw", "抽")},
    "energy_gain": {"registry": ("energy", "energy+"), "tests": ("energy", "能量")},
    "poison_applied": {"registry": ("poison", "poison+"), "tests": ("poison", "毒")},
    "channel_orb": {"registry": ("channel_orb",), "tests": ("orb", "球")},
    "channel_count": {"registry": ("channel_cnt", "channel_cnt+"), "tests": ("orb", "球")},
    "evoke_orbs": {"registry": ("evoke",), "tests": ("evoke", "激发")},
    "focus_applied": {"registry": ("focus", "focus+"), "tests": ("focus", "集中")},
    "exhausts": {"registry": ("exhaust",), "tests": ("exhaust", "消耗")},
    "stance": {"registry": (), "tests": ("stance", "姿态")},
}

COMBAT_RELICS = {
    "Anchor", "Bronze Scales", "Calipers", "Happy Flower", "Ice Cream",
    "Incense Burner", "InkBottle", "Kunai", "Lantern", "Necronomicon",
    "Nunchaku", "Orichalcum", "Ornamental Fan", "Paper Crane", "Paper Frog",
    "Pen Nib", "Shuriken", "StrikeDummy", "Sundial", "Torii", "Unceasing Top",
}

COMBAT_POTIONS = {
    "Block Potion", "Dexterity Potion", "Strength Potion", "Energy Potion",
    "Fire Potion", "Explosive Potion", "Weak Potion", "FearPotion", "Poison Potion",
    "Ancient Potion", "GhostInAJar", "LiquidBronze", "SteroidPotion", "SpeedPotion",
    "FocusPotion", "EssenceOfSteel", "Swift Potion", "Fruit Juice", "BloodPotion",
    "Health Potion", "FairyPotion", "Regen Potion",
}


def _normalise(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _keys(data: Any) -> Set[str]:
    if isinstance(data, dict):
        return set(data.keys())
    if isinstance(data, list):
        return {
            str(item.get("id") or item.get("ID") or item.get("name"))
            for item in data if isinstance(item, dict)
        }
    return set()


def _load_json(name: str) -> Any:
    return json.loads((Path(EO_DATA_DIR) / f"{name}.json").read_text(encoding="utf-8"))


def _attribute_reads(source_path: Path) -> Set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }


def _test_text() -> str:
    test_dir = Path(__file__).parent / "tests"
    return "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted(test_dir.glob("test_*.py"))
    )


def _mechanic_evidence(registry_fields: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
    solver_path = Path(__file__).parent / "combat_solver.py"
    solver_reads = _attribute_reads(solver_path)
    tests = _test_text()
    evidence = {}
    for field, spec in CARD_FIELD_SPECS.items():
        registry_present = not spec["registry"] or any(
            registry_fields.get(registry_field, 0) > 0
            for registry_field in spec["registry"]
        )
        solver_consumed = field in solver_reads
        test_tokens = spec["tests"]
        test_verified = all(token.lower() in tests.lower() for token in test_tokens)
        evidence[field] = {
            "L1_data_parsed": registry_present,
            "L2_solver_consumed": solver_consumed,
            "L3_test_evidence": test_verified,
            "status": (
                "verified" if registry_present and solver_consumed and test_verified
                else "partial" if registry_present and solver_consumed
                else "data_only" if registry_present
                else "missing"
            ),
        }
    return evidence


def build_report() -> Dict[str, Any]:
    raw_cards = _keys(_load_json("cards"))
    raw_relics = _keys(_load_json("relics"))
    raw_powers = _keys(_load_json("powers"))
    raw_monsters = _keys(_load_json("monsters"))

    card_sources = {
        _normalise(card_id): source
        for source, values in (
            ("registry", CARD_STAT_REGISTRY.keys()),
            ("watcher", WATCHER_CARDS.keys()),
        )
        for card_id in values
    }
    unresolved_cards = sorted(
        card_id for card_id in raw_cards if _normalise(card_id) not in card_sources
    )

    registry_fields: Dict[str, int] = {}
    for stat in CARD_STAT_REGISTRY.values():
        for field in stat:
            registry_fields[field] = registry_fields.get(field, 0) + 1

    mechanic_evidence = _mechanic_evidence(registry_fields)
    translated_relics = {
        _normalise(relic_id) for relic_id in RELIC_ZH_MAP
    }
    untranslated_relics = sorted(
        relic_id for relic_id in raw_relics
        if _normalise(relic_id) not in translated_relics
    )

    return {
        "source_counts": {
            "cards": len(raw_cards),
            "relics": len(raw_relics),
            "powers": len(raw_powers),
            "monsters": len(raw_monsters),
            "orbs": len(_keys(_load_json("orbs"))),
            "potions": len(_keys(_load_json("potions"))),
        },
        "card_coverage": {
            "registry": len(CARD_STAT_REGISTRY),
            "watcher": len(WATCHER_CARDS),
            "unresolved_count": len(unresolved_cards),
            "unresolved": unresolved_cards,
        },
        "registry_fields": dict(sorted(registry_fields.items())),
        "mechanic_evidence": mechanic_evidence,
        "relic_coverage": {
            "translated_count": len(raw_relics) - len(untranslated_relics),
            "untranslated_count": len(untranslated_relics),
            "untranslated": untranslated_relics,
            "combat_simulated": sorted(COMBAT_RELICS),
        },
        "potion_coverage": {
            "simulated_count": len(COMBAT_POTIONS),
            "total_count": len(_keys(_load_json("potions"))),
            "simulated": sorted(COMBAT_POTIONS),
        },
    }


def _render(report: Dict[str, Any]) -> str:
    source = report["source_counts"]
    cards = report["card_coverage"]
    relics = report["relic_coverage"]
    potions = report["potion_coverage"]
    evidence_lines = [
        f"- {field}: {details['status']} "
        f"(L1={details['L1_data_parsed']}, "
        f"L2={details['L2_solver_consumed']}, "
        f"L3={details['L3_test_evidence']})"
        for field, details in report["mechanic_evidence"].items()
    ]
    unresolved_card_lines = [f"- {card}" for card in cards["unresolved"]] or ["- None"]
    lines = [
        "NeowEye Coverage Audit",
        "=======================",
        "",
        "Source data:",
        *(f"- {name}: {count}" for name, count in source.items()),
        "",
        "Card rule coverage:",
        f"- Exact registry entries: {cards['registry']}",
        f"- Watcher entries: {cards['watcher']}",
        f"- Unresolved after name normalisation: {cards['unresolved_count']}",
        "",
        "Mechanic evidence (L1 data / L2 solver / L3 tests):",
        *evidence_lines,
        "",
        "Relic coverage:",
        f"- Translated: {relics['translated_count']}/{source['relics']}",
        f"- Behaviour simulated in combat solver: {len(relics['combat_simulated'])}",
        "",
        "Potion coverage:",
        f"- Simulated in combat solver: {potions['simulated_count']}/{potions['total_count']}",
        "",
        "Unresolved cards:",
        *unresolved_card_lines,
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit NeowEye data and mechanic coverage")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else _render(report))


if __name__ == "__main__":
    main()