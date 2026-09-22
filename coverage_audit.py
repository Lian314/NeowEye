"""Audit data coverage separately from combat simulation coverage."""
import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from card_db import CARD_STAT_REGISTRY
from knowledge_base import EO_DATA_DIR, GLOBAL_KB, RELIC_ZH_MAP, WATCHER_CARDS


CARD_INFO_TO_SOLVER = {
    "base_damage": True,
    "hits": True,
    "base_block": True,
    "vulnerable_applied": True,
    "weak_applied": True,
    "strength_applied": True,
    "dexterity_applied": True,
    "draw_cards": True,
    "energy_gain": True,
    "poison_applied": True,
    "channel_orb": True,
    "channel_count": True,
    "evoke_orbs": True,
    "focus_applied": True,
    "exhausts": True,
    "stance": True,
}

COMBAT_RELICS = {
    "Anchor", "Incense Burner", "Kunai", "Orichalcum", "Ornamental Fan",
    "Paper Crane", "Paper Frog", "Pen Nib", "StrikeDummy", "Shuriken",
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

    solver_gaps = sorted(field for field, supported in CARD_INFO_TO_SOLVER.items() if not supported)
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
        "solver_gaps": solver_gaps,
        "relic_coverage": {
            "translated_count": len(raw_relics) - len(untranslated_relics),
            "untranslated_count": len(untranslated_relics),
            "untranslated": untranslated_relics,
            "combat_simulated": sorted(COMBAT_RELICS),
        },
    }


def _render(report: Dict[str, Any]) -> str:
    source = report["source_counts"]
    cards = report["card_coverage"]
    relics = report["relic_coverage"]
    solver_gap_lines = [f"- {field}" for field in report["solver_gaps"]] or ["- None"]
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
        "CardInfo fields not consumed by CombatSolver:",
        *solver_gap_lines,
        "",
        "Relic coverage:",
        f"- Translated: {relics['translated_count']}/{source['relics']}",
        f"- Behaviour simulated in combat solver: {len(relics['combat_simulated'])}",
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