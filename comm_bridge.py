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
        self.latest_raw_msg = data
        game_state = data.get("game_state", {})
        self.latest_game_state = game_state

        for listener in self.listeners:
            try:
                listener(data)
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
