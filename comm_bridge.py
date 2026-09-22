"""
CommunicationMod Bridge for Slay the Spire.
Handles JSON communication with Slay the Spire's CommunicationMod over:
1. Stdin/Stdout (standard child-process mode)
2. Socket (network/proxy mode)
3. Mock injection (standalone testing and live UI demo)
"""
import sys
import json
import socket
import select
import logging
import threading
from typing import Dict, Any, Callable, List, Optional
from config import CONFIG

logger = logging.getLogger("CommBridge")

def _safe_int(val: Any, default: int) -> int:
    try:
        if val is None:
            return default
        return int(val)
    except (ValueError, TypeError):
        return default

def _safe_str(val: Any, default: str) -> str:
    if val is None or not isinstance(val, (str, int, float)):
        return default
    return str(val)

def sanitize_game_state(raw_data: Any) -> Dict[str, Any]:
    """
    Validates and sanitizes CommunicationMod protocol JSON payload.
    Ensures safe fallbacks and strict type coercion for missing/malformed fields
    across different game/mod versions.
    """
    if not isinstance(raw_data, dict):
        logger.warning(f"Malformed raw_data received (not a dict): {type(raw_data)}")
        return {"game_state": {}}

    data = dict(raw_data)
    game_state = data.get("game_state")
    if not isinstance(game_state, dict):
        game_state = {}
        data["game_state"] = game_state

    # Top-level state normalization with strict type coercion
    game_state["floor"] = _safe_int(game_state.get("floor"), 1)
    game_state["act"] = _safe_int(game_state.get("act"), 1)
    game_state["class"] = _safe_str(game_state.get("class"), "IRONCLAD")
    game_state["current_hp"] = _safe_int(game_state.get("current_hp"), 80)
    game_state["max_hp"] = max(1, _safe_int(game_state.get("max_hp"), 80))
    game_state["gold"] = max(0, _safe_int(game_state.get("gold"), 99))
    if not isinstance(game_state.get("deck"), list):
        game_state["deck"] = []
    if not isinstance(game_state.get("relics"), list):
        game_state["relics"] = []
    if not isinstance(game_state.get("screen_state"), dict):
        game_state["screen_state"] = {}

    # Combat state normalization
    combat_state = game_state.get("combat_state")
    if isinstance(combat_state, dict):
        # Sanitize player
        player = combat_state.get("player")
        if not isinstance(player, dict):
            player = {}
            combat_state["player"] = player
        player["current_hp"] = _safe_int(player.get("current_hp"), game_state["current_hp"])
        player["max_hp"] = max(1, _safe_int(player.get("max_hp"), game_state["max_hp"]))
        player["block"] = max(0, _safe_int(player.get("block"), 0))
        player["energy"] = max(0, _safe_int(player.get("energy"), 3))
        if not isinstance(player.get("powers"), list):
            player["powers"] = []
        if not isinstance(player.get("orbs"), list):
            player["orbs"] = []

        # Sanitize monsters
        monsters = combat_state.get("monsters")
        if not isinstance(monsters, list):
            monsters = []
            combat_state["monsters"] = monsters
        valid_monsters = []
        for m in monsters:
            if isinstance(m, dict):
                m["current_hp"] = max(0, _safe_int(m.get("current_hp"), 0))
                m["max_hp"] = max(1, _safe_int(m.get("max_hp"), 1))
                m["block"] = max(0, _safe_int(m.get("block"), 0))
                m["intent"] = _safe_str(m.get("intent"), "UNKNOWN")
                m["move_adjusted_damage"] = max(0, _safe_int(m.get("move_adjusted_damage", m.get("move_base_damage")), 0))
                m["move_hits"] = max(1, _safe_int(m.get("move_hits"), 1))
                m["is_gone"] = bool(m.get("is_gone", False))
                m["half_dead"] = bool(m.get("half_dead", False))
                if not isinstance(m.get("powers"), list):
                    m["powers"] = []
                valid_monsters.append(m)
        combat_state["monsters"] = valid_monsters

        # Sanitize hand, piles
        for pile_key in ["hand", "draw_pile", "discard_pile", "exhaust_pile"]:
            pile = combat_state.get(pile_key)
            if not isinstance(pile, list):
                combat_state[pile_key] = []
            else:
                combat_state[pile_key] = [c for c in pile if isinstance(c, dict)]

        combat_state["turn"] = max(1, _safe_int(combat_state.get("turn"), 1))

    return data

class CommBridge:
    def __init__(self, config=None):
        self.config = config or CONFIG.comm
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.latest_game_state: Optional[Dict[str, Any]] = None
        self.latest_raw_msg: Optional[Dict[str, Any]] = None

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]):
        """Registers a callback to receive parsed game states."""
        self.listeners.append(callback)

    def start(self):
        """Starts the communication listener thread."""
        self._running = True
        if self.config.mode == "stdin":
            self._thread = threading.Thread(target=self._stdin_loop, daemon=True, name="CommMod-Stdin")
            self._thread.start()
            if self.config.send_ready_on_start:
                self.send_command("ready")
        elif self.config.mode == "socket":
            self._thread = threading.Thread(target=self._socket_loop, daemon=True, name="CommMod-Socket")
            self._thread.start()
        elif self.config.mode == "mock":
            logger.info("CommBridge started in mock mode.")

    def stop(self):
        """Stops the communication bridge."""
        self._running = False

    def send_command(self, cmd: str):
        """Sends a command to CommunicationMod via stdout."""
        try:
            sys.stdout.write(f"{cmd}\n")
            sys.stdout.flush()
            logger.debug(f"Sent command to CommMod: {cmd}")
        except Exception as e:
            logger.error(f"Failed to send command to stdout: {e}")

    def inject_state(self, raw_data: Dict[str, Any]):
        """Directly injects a raw state message (used in mock/testing mode)."""
        self._handle_incoming_json(raw_data)

    def _handle_incoming_json(self, data: Dict[str, Any]):
        """Parses incoming CommunicationMod message and distributes to listeners."""
        sanitized_data = sanitize_game_state(data)
        self.latest_raw_msg = sanitized_data
        game_state = sanitized_data.get("game_state", {})
        self.latest_game_state = game_state

        for listener in self.listeners:
            try:
                listener(sanitized_data)
            except Exception as e:
                logger.error(f"Error in CommBridge listener: {e}", exc_info=True)

    def _stdin_loop(self):
        """Reads JSON lines from sys.stdin."""
        logger.info("CommBridge listening on sys.stdin...")
        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    self._handle_incoming_json(data)
                except json.JSONDecodeError as jde:
                    logger.warning(f"Invalid JSON from stdin: {line[:100]}... Error: {jde}")
            except Exception as e:
                logger.error(f"Exception in stdin loop: {e}")
                break

    def _socket_loop(self):
        """Listens on a local TCP socket for game state JSON strings."""
        host = self.config.socket_host
        port = self.config.socket_port
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((host, port))
        server_sock.listen(1)
        logger.info(f"CommBridge listening on socket {host}:{port}...")

        while self._running:
            try:
                conn, addr = server_sock.accept()
                logger.info(f"Connected to CommMod socket from {addr}")
                buffer = ""
                with conn:
                    while self._running:
                        data = conn.recv(4096)
                        if not data:
                            break
                        buffer += data.decode("utf-8", errors="ignore")
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if line:
                                try:
                                    parsed = json.loads(line)
                                    self._handle_incoming_json(parsed)
                                except Exception as e:
                                    logger.warning(f"Socket JSON error: {e}")
            except Exception as e:
                if self._running:
                    logger.error(f"Socket server error: {e}")
        server_sock.close()
