"""
NeowEye Environment Detector and Automatic Configuration Engine.
Provides:
1. Zero-click auto-binding to CommunicationMod config.properties on startup.
2. Multi-strategy Slay the Spire game detection (Registry, all drive scans, running processes, custom path).
3. Mod prerequisite inspection (ModTheSpire, BaseMod, CommunicationMod) across Steam Workshop and local game folders.
4. Fault-tolerant recovery actions (1-click Workshop links, offline mod installer, custom folder picker).
"""
import os
import sys
import json
import re
import webbrowser
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

# Workshop IDs for Slay the Spire (App ID: 646570)
WORKSHOP_MODTHESPIRE_ID = "1605060445"
WORKSHOP_BASEMOD_ID = "1605833019"
WORKSHOP_COMMUNICATIONMOD_ID = "1609159503"

CONFIG_FILE_NAME = "user_config.json"

@dataclass
class DiagnosticResult:
    game_installed: bool = False
    game_path: Optional[str] = None
    game_source: Optional[str] = None  # "steam", "process", "drive_scan", "custom"
    modthespire_installed: bool = False
    basemod_installed: bool = False
    communicationmod_installed: bool = False
    config_bound: bool = False
    config_path: str = ""
    status_code: str = "GAME_NOT_FOUND"  # "READY", "MODS_MISSING", "GAME_NOT_FOUND"
    status_title: str = ""
    status_desc: str = ""
    missing_mods: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def all_mods_installed(self) -> bool:
        return self.modthespire_installed and self.basemod_installed and self.communicationmod_installed


class EnvironmentDetector:
    def __init__(self, app_root: Optional[str] = None):
        if app_root is None:
            if getattr(sys, "frozen", False):
                self.app_root = os.path.dirname(os.path.abspath(sys.executable))
            else:
                self.app_root = os.path.dirname(os.path.abspath(__file__))
        else:
            self.app_root = app_root

        self.user_config_path = os.path.join(self.app_root, CONFIG_FILE_NAME)

    def get_executable_path(self) -> str:
        """Returns the absolute path of NeowEye.exe or main.py."""
        if getattr(sys, "frozen", False):
            return os.path.abspath(sys.executable)
        else:
            # Running as Python script
            return os.path.abspath(os.path.join(self.app_root, "main.py"))

    # =========================================================================
    # 1. Automatic CommunicationMod Binding
    # =========================================================================
    def auto_bind_communication_mod(self, exe_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Automatically updates/writes CommunicationMod's config.properties to point
        to the current NeowEye executable with forward slashes.
        Safe for any location, silent and robust.
        """
        if exe_path is None:
            exe_path = self.get_executable_path()

        safe_path = exe_path.replace("\\", "/")
        target_command = f'"{safe_path}" --mode stdin'

        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            local_app_data = os.path.expanduser("~\\AppData\\Local")

        config_dir = os.path.join(local_app_data, "ModTheSpire", "CommunicationMod")
        config_file = os.path.join(config_dir, "config.properties")

        try:
            os.makedirs(config_dir, exist_ok=True)
            existing_lines = []
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r", encoding="utf-8", errors="ignore") as f:
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
                    new_lines.append(f"command={target_command}\n")
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
                new_lines.append(f"command={target_command}\n")
            if not has_run_at_start:
                new_lines.append("runAtGameStart=true\n")
            if not has_verbose:
                new_lines.append("verbose=false\n")

            with open(config_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            return True, config_file
        except Exception as e:
            return False, str(e)

    # =========================================================================
    # 2. Multi-Strategy Game Detection
    # =========================================================================
    def detect_game(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Attempts to locate Slay the Spire through multiple strategies.
        Returns: (game_path, detection_source) or (None, None)
        """
        # Strategy 0: Custom user-specified path from config
        custom_path = self.load_custom_game_dir()
        if custom_path and self._is_valid_game_dir(custom_path):
            return custom_path, "custom"

        # Strategy 1: Check running process
        proc_path = self._detect_from_running_process()
        if proc_path and self._is_valid_game_dir(proc_path):
            return proc_path, "process"

        # Strategy 2: Check Steam libraries via registry
        steam_libs = self._get_steam_libraries()
        for lib in steam_libs:
            candidate = os.path.join(lib, "steamapps", "common", "SlayTheSpire")
            if self._is_valid_game_dir(candidate):
                return candidate, "steam"

        # Strategy 3: Scan all active drives for common installation paths
        drive_path = self._scan_drives()
        if drive_path and self._is_valid_game_dir(drive_path):
            return drive_path, "drive_scan"

        return None, None

    def _is_valid_game_dir(self, path: str) -> bool:
        """Checks if a directory looks like a valid Slay the Spire installation."""
        if not path or not os.path.isdir(path):
            return False
        # Look for SlayTheSpire.exe, desktop-1.0.jar, or SlayTheSpire.jar
        has_exe = os.path.exists(os.path.join(path, "SlayTheSpire.exe"))
        has_jar = os.path.exists(os.path.join(path, "desktop-1.0.jar")) or os.path.exists(os.path.join(path, "SlayTheSpire.jar"))
        return has_exe or has_jar

    def _detect_from_running_process(self) -> Optional[str]:
        """Detects Slay the Spire from currently running processes on Windows."""
        try:
            # Query tasklist or WMIC
            cmd = 'wmic process where "name like \'%SlayTheSpire%\' or name like \'%java%\'" get ExecutablePath,CommandLine'
            output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            for line in output.splitlines():
                if "SlayTheSpire" in line:
                    match = re.search(r'([A-Za-z]:\\[^"\r\n]+?\\SlayTheSpire)', line, re.IGNORECASE)
                    if match:
                        candidate = match.group(1)
                        if self._is_valid_game_dir(candidate):
                            return candidate
        except Exception:
            pass
        return None

    def _get_steam_libraries(self) -> List[str]:
        """Queries Windows registry to locate Steam installation and all Steam libraries."""
        libraries = []
        steam_path = None

        try:
            import winreg
            keys = [
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            ]
            for root, subkey, val_name in keys:
                try:
                    with winreg.OpenKey(root, subkey) as k:
                        val = winreg.QueryValueEx(k, val_name)[0]
                        if val and os.path.exists(val):
                            steam_path = os.path.abspath(val)
                            break
                except Exception:
                    continue
        except Exception:
            pass

        if steam_path:
            libraries.append(steam_path)
            vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
            if os.path.exists(vdf_path):
                try:
                    with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    paths = re.findall(r'"path"\s+"([^"]+)"', content)
                    for p in paths:
                        clean_p = p.replace("\\\\", "\\")
                        if clean_p not in libraries and os.path.exists(clean_p):
                            libraries.append(clean_p)
                except Exception:
                    pass

        return libraries

    def _scan_drives(self) -> Optional[str]:
        """Scans all active drive letters for Slay the Spire directories."""
        drives = [f"{chr(c)}:\\" for c in range(ord('C'), ord('Z') + 1) if os.path.exists(f"{chr(c)}:\\")]
        common_subdirs = [
            r"Program Files (x86)\Steam\steamapps\common\SlayTheSpire",
            r"Program Files\Steam\steamapps\common\SlayTheSpire",
            r"Steam\steamapps\common\SlayTheSpire",
            r"SteamLibrary\steamapps\common\SlayTheSpire",
            r"Games\Steam\steamapps\common\SlayTheSpire",
            r"Games\SteamLibrary\steamapps\common\SlayTheSpire",
            r"Games\SlayTheSpire",
            r"Game\SlayTheSpire",
            r"SlayTheSpire",
            r"Slay the Spire",
        ]

        for d in drives:
            for sub in common_subdirs:
                candidate = os.path.join(d, sub)
                if self._is_valid_game_dir(candidate):
                    return candidate

        return None

    # =========================================================================
    # 3. Mod Prerequisite Inspection
    # =========================================================================
    def check_mods(self, game_path: Optional[str]) -> Dict[str, bool]:
        """
        Checks if ModTheSpire, BaseMod, and CommunicationMod are installed,
        either in Steam Workshop or inside the game directory.
        """
        res = {
            "modthespire": False,
            "basemod": False,
            "communicationmod": False,
        }

        if not game_path:
            return res

        # 1. Check local game folder
        # ModTheSpire.jar in root
        if os.path.exists(os.path.join(game_path, "ModTheSpire.jar")):
            res["modthespire"] = True

        # mods folder
        mods_dir = os.path.join(game_path, "mods")
        if os.path.isdir(mods_dir):
            try:
                mod_files = [f.lower() for f in os.listdir(mods_dir)]
                for mf in mod_files:
                    if "basemod" in mf and mf.endswith(".jar"):
                        res["basemod"] = True
                    if "communicationmod" in mf and mf.endswith(".jar"):
                        res["communicationmod"] = True
            except Exception:
                pass

        # 2. Check Steam Workshop (if game is under steamapps)
        # Slay the Spire App ID: 646570
        norm_game = os.path.normpath(game_path)
        if "steamapps" in norm_game.lower():
            # Extract steam library root
            parts = norm_game.split(os.sep)
            try:
                steamapps_idx = [p.lower() for p in parts].index("steamapps")
                library_root = os.sep.join(parts[:steamapps_idx])
                workshop_dir = os.path.join(library_root, "steamapps", "workshop", "content", "646570")
                if os.path.isdir(workshop_dir):
                    if os.path.exists(os.path.join(workshop_dir, WORKSHOP_MODTHESPIRE_ID)):
                        res["modthespire"] = True
                    if os.path.exists(os.path.join(workshop_dir, WORKSHOP_BASEMOD_ID)):
                        res["basemod"] = True
                    if os.path.exists(os.path.join(workshop_dir, WORKSHOP_COMMUNICATIONMOD_ID)):
                        res["communicationmod"] = True
            except Exception:
                pass

        return res

    # =========================================================================
    # 4. Full Diagnosis
    # =========================================================================
    def diagnose(self) -> DiagnosticResult:
        """Performs full environment diagnostic and auto-binds config.properties."""
        diag = DiagnosticResult()

        # Step 1: Auto-bind config.properties
        bound, cfg_path = self.auto_bind_communication_mod()
        diag.config_bound = bound
        diag.config_path = cfg_path

        # Step 2: Detect game
        game_path, source = self.detect_game()
        diag.game_installed = bool(game_path)
        diag.game_path = game_path
        diag.game_source = source

        # Step 3: Check mods
        if diag.game_installed:
            mods_status = self.check_mods(game_path)
            diag.modthespire_installed = mods_status["modthespire"]
            diag.basemod_installed = mods_status["basemod"]
            diag.communicationmod_installed = mods_status["communicationmod"]

            missing = []
            if not diag.modthespire_installed:
                missing.append("ModTheSpire (加载器)")
            if not diag.basemod_installed:
                missing.append("BaseMod (API基础库)")
            if not diag.communicationmod_installed:
                missing.append("CommunicationMod (通信桥梁)")
            diag.missing_mods = missing

            if diag.all_mods_installed:
                diag.status_code = "READY"
                diag.status_title = "[就绪] 尖塔联动环境就绪"
                diag.status_desc = f"检测到游戏路径: {game_path}。请在 Steam 启动游戏时选择 [Play with Mods]！"
                diag.suggestions = [
                    "启动 Steam 打开《杀戮尖塔》，选择 Play with Mods",
                    "勾选 CommunicationMod 启动游戏，AI 悬浮窗将实时协同！"
                ]
            else:
                diag.status_code = "MODS_MISSING"
                diag.status_title = "[注意] 缺少必备通信 Mod"
                diag.status_desc = f"已检测到游戏，但缺少: {'、'.join(missing)}。"
                diag.suggestions = [
                    "点击 [一键订阅 Mod] 在 Steam 创意工坊订阅",
                    "或点击 [一键安装离线补丁] 免联网自动拷入游戏"
                ]
        else:
            diag.status_code = "GAME_NOT_FOUND"
            diag.status_title = "[提示] 未检测到《杀戮尖塔》"
            diag.status_desc = "未能在常见路径找到游戏。若已安装，请手动指定目录；若未安装可体验内置演示模式。"
            diag.suggestions = [
                "点击 [手动选择游戏目录] 指定杀戮尖塔所在文件夹",
                "若尚未安装，请先在 Steam 中安装杀戮尖塔",
                "点击 [体验演示推演] 即可无缝体验 AI 实战推演"
            ]

        return diag

    # =========================================================================
    # 5. Recovery Actions
    # =========================================================================
    def open_workshop_pages(self):
        """Opens Steam Workshop subscription pages in browser/Steam client."""
        workshop_urls = [
            f"https://steamcommunity.com/sharedfiles/filedetails/?id={WORKSHOP_MODTHESPIRE_ID}",
            f"https://steamcommunity.com/sharedfiles/filedetails/?id={WORKSHOP_BASEMOD_ID}",
            f"https://steamcommunity.com/sharedfiles/filedetails/?id={WORKSHOP_COMMUNICATIONMOD_ID}",
        ]
        for url in workshop_urls:
            try:
                webbrowser.open(url)
            except Exception:
                pass

    def has_offline_mod_kit(self) -> bool:
        """Checks if bundled offline mod files exist in spire_mods/."""
        mod_kit_dir = os.path.join(self.app_root, "spire_mods")
        if not os.path.isdir(mod_kit_dir):
            return False
        # Check if at least one jar is present
        jars = [f for f in os.listdir(mod_kit_dir) if f.endswith(".jar")]
        return len(jars) > 0

    def install_offline_mods(self, target_game_dir: str) -> Tuple[bool, str]:
        """Copies bundled mod jars from spire_mods/ into target game directory."""
        if not self._is_valid_game_dir(target_game_dir):
            return False, "目标目录不是有效的杀戮尖塔游戏文件夹！"

        mod_kit_dir = os.path.join(self.app_root, "spire_mods")
        if not os.path.isdir(mod_kit_dir):
            return False, "未找到内置的 spire_mods/ 离线补丁文件夹！"

        try:
            mods_dir = os.path.join(target_game_dir, "mods")
            os.makedirs(mods_dir, exist_ok=True)

            copied = []
            for item in os.listdir(mod_kit_dir):
                if item.endswith(".jar"):
                    src = os.path.join(mod_kit_dir, item)
                    # ModTheSpire.jar goes to root, others to mods/
                    if item.lower() == "modthespire.jar":
                        dst = os.path.join(target_game_dir, item)
                    else:
                        dst = os.path.join(mods_dir, item)
                    shutil.copy2(src, dst)
                    copied.append(item)

            return True, f"成功安装 {len(copied)} 个 Mod 文件到游戏目录！"
        except Exception as e:
            return False, f"安装失败: {str(e)}"

    def save_custom_game_dir(self, path: str) -> bool:
        """Saves a verified custom game directory to user_config.json."""
        if not self._is_valid_game_dir(path):
            return False
        try:
            cfg = {}
            if os.path.exists(self.user_config_path):
                try:
                    with open(self.user_config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                except Exception:
                    pass
            cfg["custom_game_dir"] = os.path.abspath(path)
            with open(self.user_config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def load_custom_game_dir(self) -> Optional[str]:
        """Loads custom game directory from user_config.json."""
        if not os.path.exists(self.user_config_path):
            return None
        try:
            with open(self.user_config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            p = cfg.get("custom_game_dir")
            if p and os.path.isdir(p):
                return p
        except Exception:
            pass
        return None
