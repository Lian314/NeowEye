"""
Main Orchestrator for Slay the Spire Real-time Tactical Assistant.
Coordinates CommunicationMod Bridge, Combat Solver, Macro Advisor (Laya), and Desktop Overlay HUD.
"""
import sys
import argparse
import logging
import threading
from typing import Dict, Any, Optional

from config import CONFIG
from comm_bridge import CommBridge
from combat_solver import CombatSolver
from macro_advisor import MacroAdvisor
from laya_client import LayaClient
from overlay_hud import OverlayHUD
from relic_tracker import RelicTracker
from deck_tracker import DeckTracker
from test_mock_scenarios import MOCK_SCENARIOS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)  # Log to stderr so stdout is reserved for CommunicationMod!
    ]
)
logger = logging.getLogger("Main")

class SpireTacticalAssistant:
    def __init__(self, mode: str = "stdin"):
        CONFIG.comm.mode = mode
        self.mode = mode

        # Core components
        self.laya_client = LayaClient(CONFIG.laya)
        self.combat_solver = CombatSolver(CONFIG.combat)
        self.macro_advisor = MacroAdvisor(self.laya_client)
        self.relic_tracker = RelicTracker()
        self.deck_tracker = DeckTracker()
        self.comm_bridge = CommBridge(CONFIG.comm)

        # UI Overlay HUD
        self.hud = OverlayHUD(on_scenario_select=self.on_mock_scenario_selected)
        self.hud.set_scenarios(list(MOCK_SCENARIOS.keys()))

        # Register bridge listener
        self.comm_bridge.add_listener(self.on_game_state_received)

    def start(self):
        """Starts the assistant."""
        logger.info(f"Starting Slay the Spire Tactical Assistant in [{self.mode}] mode...")
        self.comm_bridge.start()

        # If starting in mock mode, load the first scenario by default
        if self.mode == "mock" or not sys.stdin.isatty():
            first_scenario_name = list(MOCK_SCENARIOS.keys())[0]
            self.on_mock_scenario_selected(first_scenario_name)

        # Run UI mainloop on main thread
        self.hud.run()

    def on_game_state_received(self, raw_data: Dict[str, Any]):
        """Handler for incoming state messages from CommunicationMod."""
        game_state = raw_data.get("game_state", {})
        if not game_state:
            return

        screen_type = game_state.get("screen_type", "NONE")
        combat_state = game_state.get("combat_state")

        # Extract player summary
        char = game_state.get("class", "IRONCLAD")
        act = game_state.get("act", 1)
        floor = game_state.get("floor", 1)
        gold = game_state.get("gold", 99)

        if combat_state:
            p = combat_state.get("player", {})
            hp = p.get("current_hp", 80)
            max_hp = p.get("max_hp", 80)
            energy = p.get("energy", 3)
        else:
            hp = game_state.get("current_hp", 80)
            max_hp = game_state.get("max_hp", 80)
            energy = 0

        relics = game_state.get("relics", [])
        turn = combat_state.get("turn", 1) if combat_state else 1

        # Update HUD header
        self.hud.root.after(0, lambda: self.hud.update_game_info(char, act, floor, hp, max_hp, energy, gold))

        # Check Relic Alerts (Incense Burner 5/6, Pen Nib 9/10, etc.)
        relic_alerts = self.relic_tracker.analyze_relics(relics, turn)
        self.hud.root.after(0, lambda: self.hud.update_relic_alerts(relic_alerts))

        # 1. Combat State -> In-combat Mathematical Optimizer & Deck Tracker
        if combat_state and (screen_type == "NONE" or screen_type == "COMBAT"):
            plan = self.combat_solver.solve(combat_state, relics=relics)
            self.hud.root.after(0, lambda: self.hud.show_combat_plan(plan))

            # Deck draw probabilities
            deck_stats = self.deck_tracker.analyze_deck(combat_state)
            self.hud.root.after(0, lambda: self.hud.show_deck_tab(deck_stats))

        # 2. Card Reward Screen -> Laya Decision Engine
        elif screen_type == "CARD_REWARD":
            def _async_card_eval():
                decision = self.macro_advisor.evaluate_card_reward(game_state)
                self.hud.root.after(0, lambda: self.hud.show_macro_decision(decision))

            threading.Thread(target=_async_card_eval, daemon=True).start()

        # 3. Map Routing Screen -> Laya Decision Engine
        elif screen_type == "MAP":
            def _async_map_eval():
                decision = self.macro_advisor.evaluate_map_routing(game_state)
                self.hud.root.after(0, lambda: self.hud.show_macro_decision(decision))

            threading.Thread(target=_async_map_eval, daemon=True).start()

        # 4. Rest Site Screen -> Laya Decision Engine
        elif screen_type == "REST":
            def _async_rest_eval():
                decision = self.macro_advisor.evaluate_rest_site(game_state)
                self.hud.root.after(0, lambda: self.hud.show_macro_decision(decision))

            threading.Thread(target=_async_rest_eval, daemon=True).start()

    def on_mock_scenario_selected(self, scenario_name: str):
        """Injects a mock scenario into the assistant pipeline."""
        if scenario_name in MOCK_SCENARIOS:
            logger.info(f"Injecting mock scenario: {scenario_name}")
            data = MOCK_SCENARIOS[scenario_name]
            self.comm_bridge.inject_state(data)

def install_config():
    """
    Automatically configures CommunicationMod's config.properties to point to this executable.
    Creates %LOCALAPPDATA%/ModTheSpire/CommunicationMod/config.properties if it doesn't exist.
    """
    import os
    if getattr(sys, 'frozen', False):
        exe_path = os.path.abspath(sys.executable)
    else:
        exe_path = os.path.abspath(sys.argv[0])

    safe_exe_path = exe_path.replace("\\", "/")
    command_line = f'"{safe_exe_path}" --mode stdin'

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        local_app_data = os.path.expanduser("~\\AppData\\Local")

    target_dir = os.path.join(local_app_data, "ModTheSpire", "CommunicationMod")
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, "config.properties")

    # Read existing config if any
    existing_lines = []
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                existing_lines = f.readlines()
        except Exception:
            pass

    has_command = False
    has_run_at_start = False
    has_verbose = False
    new_lines = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith("command="):
            new_lines.append(f"command={command_line}\n")
            has_command = True
        elif stripped.startswith("runAtGameStart="):
            new_lines.append("runAtGameStart=true\n")
            has_run_at_start = True
        elif stripped.startswith("verbose="):
            new_lines.append(line)
            has_verbose = True
        else:
            new_lines.append(line)

    if not has_command:
        new_lines.append(f"command={command_line}\n")
    if not has_run_at_start:
        new_lines.append("runAtGameStart=true\n")
    if not has_verbose:
        new_lines.append("verbose=false\n")

    with open(target_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    console_msg = (
        f"[OK] NeowEye 战术辅助器配置成功！\n"
        f"配置文件路径: {target_file}\n"
        f"绑定程序路径: {command_line}\n"
        f"【使用说明】:\n"
        f"1. 确保杀戮尖塔已安装/订阅 CommunicationMod 与 ModTheSpire\n"
        f"2. 从 Steam 启动游戏时选择 [Play with Mods]\n"
        f"3. 勾选 CommunicationMod 启动，NeowEye 战术悬浮窗将全自动呼出！"
    )
    print(console_msg)
    return target_file

def main():
    parser = argparse.ArgumentParser(description="Slay the Spire Real-time Tactical Assistant")
    parser.add_argument(
        "--mode",
        choices=["stdin", "socket", "mock"],
        default="stdin",
        help="Bridge mode: stdin (CommunicationMod child process), socket, or mock"
    )
    parser.add_argument(
        "--install-config",
        action="store_true",
        help="Automatically configure CommunicationMod config.properties to point to this executable"
    )
    args = parser.parse_args()

    if args.install_config:
        install_config()
        return

    app = SpireTacticalAssistant(mode=args.mode)
    app.start()

if __name__ == "__main__":
    main()

