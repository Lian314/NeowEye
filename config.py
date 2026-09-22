"""
Configuration module for Slay the Spire Real-time Tactical Assistant.
Includes Laya Decision Engine settings, CommunicationMod options, and Overlay HUD appearance.
"""
from dataclasses import dataclass, field
import os

@dataclass
class LayaConfig:
    # Optional remote Laya decision engine endpoint (configurable via environment variables)
    api_url: str = os.getenv("LAYA_API_URL", "http://localhost:8000/predict")
    health_url: str = os.getenv("LAYA_HEALTH_URL", "http://localhost:8000/health")
    model: str = "multilingual"  # Model checkpoint name
    timeout_sec: float = 10.0
    verify_ssl: bool = False
    cache_enabled: bool = True   # Avoid re-querying identical state

    # Edge / Local ONNX inference settings
    engine_mode: str = "auto"    # "auto" (prefer local if model file exists, else remote), "local", or "remote"
    local_model_path: str = "models/laya_int8.onnx"
    local_tokenizer_path: str = "models/tokenizer.json"
    intra_op_threads: int = 2    # Number of CPU threads for ONNX Runtime

@dataclass
class CombatSolverConfig:
    # Maximum permutation depth or search branch limit
    max_search_depth: int = 6
    max_evaluated_states: int = 5000
    # Weights for multi-objective optimization
    weight_prevent_damage: float = 1000.0  # Top priority: 0 net HP loss
    weight_kill_enemy: float = 200.0       # Second priority: kill attacking/dangerous enemies
    weight_damage_dealt: float = 1.0       # Third priority: deal damage to remaining monsters
    weight_retained_block: float = 0.5     # Fourth priority: keep excess block (if barricade/calipers)
    weight_conserve_energy: float = 0.2    # Save energy if no useful play

@dataclass
class OverlayConfig:
    # Window dimensions and position
    width: int = 380
    height: int = 560
    initial_x: int = 40
    initial_y: int = 80
    # Transparency & Topmost
    alpha: float = 0.92          # Window opacity (0.0 - 1.0)
    always_on_top: bool = True   # HWND_TOPMOST
    click_through: bool = False  # Set to True to allow clicks to pass through to game
    # Color scheme (Dark Cyberpunk / Slay the Spire theme)
    bg_color: str = "#12141c"
    card_bg: str = "#1c2030"
    accent_color: str = "#e55039"      # Crimson Ironclad
    accent_green: str = "#2ed573"     # Block / Safe / Emerald
    accent_blue: str = "#1e90ff"      # Energy / Mana / Sapphire
    accent_gold: str = "#ffa502"      # Relic / Gold / Score
    accent_purple: str = "#9b59b6"    # Rare / Power / Void
    text_primary: str = "#f1f2f6"
    text_secondary: str = "#a4b0be"
    border_color: str = "#2f3542"

@dataclass
class CommModConfig:
    # Mode: "stdin" (CommunicationMod child process), "socket", or "mock"
    mode: str = "stdin"
    socket_host: str = "127.0.0.1"
    socket_port: int = 7777
    # Auto-ready signal on startup
    send_ready_on_start: bool = True

@dataclass
class AppConfig:
    laya: LayaConfig = field(default_factory=LayaConfig)
    combat: CombatSolverConfig = field(default_factory=CombatSolverConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    comm: CommModConfig = field(default_factory=CommModConfig)

# Global singleton config
CONFIG = AppConfig()
