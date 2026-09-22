"""
World-Class Desktop Topmost Transparent Floating Overlay HUD for Slay the Spire.
Features:
- Multi-Tab Navigation:
  - Tab 1: ⚔️ 实时战斗 (In-Combat mathematical optimizer, sequence, damage forecast, visual health/block bar)
  - Tab 2: 🧠 宏观决策 (Laya decision engine, confidence meters, Pro Skip philosophy, Boss warnings)
  - Tab 3: 🏺 遗物看板 (Active relic counter alerts, Incense Burner 5/6, Pen Nib 9/10, full relic list)
  - Tab 4: 🃏 牌库透视 (Draw/Discard/Exhaust piles, hypergeometric draw probabilities for next turn)
- Premium Visual Aesthetics:
  - Dark glassmorphism (#10131c) styling with high contrast cyber-fantasy accents.
  - Draggable header, topmost toggle, multi-level opacity adjustment.
  - Windows API click-through toggle (WS_EX_TRANSPARENT).
  - Hotkey support: F1 toggle hide/show, F2 toggle click-through.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ctypes
import logging
from typing import Dict, Any, Optional, Callable, List
from config import CONFIG
from combat_solver import CombatPlan
from macro_advisor import MacroDecision
from relic_tracker import RelicAlert
from deck_tracker import DeckStats

logger = logging.getLogger("OverlayHUD")

# Windows constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

class OverlayHUD:
    def __init__(self, on_scenario_select: Optional[Callable[[str], None]] = None):
        self.config = CONFIG.overlay
        self.on_scenario_select = on_scenario_select

        self.root = tk.Tk()
        self.root.title("NeowEye - 杀戮尖塔 AI 战术辅助器")

        self.root.geometry(f"{self.config.width + 20}x{self.config.height + 40}+{self.config.initial_x}+{self.config.initial_y}")
        self.root.configure(bg=self.config.bg_color)

        self.root.attributes("-topmost", self.config.always_on_top)
        self.root.attributes("-alpha", self.config.alpha)
        self.root.minsize(360, 520)

        # State tracking
        self.is_click_through = False
        self.is_minimized = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.current_tab = "combat"  # "combat", "macro", "relics", "deck"

        # Cached states
        self.last_combat_plan: Optional[CombatPlan] = None
        self.last_macro_decision: Optional[MacroDecision] = None
        self.last_relic_alerts: List[RelicAlert] = []
        self.last_deck_stats: Optional[DeckStats] = None

        self._build_ui()
        self._setup_window_drag()
        self._setup_hotkeys()

    def _setup_hotkeys(self):
        """Binds F1 and F2 hotkeys."""
        self.root.bind("<F1>", lambda e: self._toggle_minimize())
        self.root.bind("<F2>", lambda e: self._toggle_clickthrough())

    def _setup_window_drag(self):
        def on_drag_start(event):
            self.drag_start_x = event.x
            self.drag_start_y = event.y

        def on_drag_motion(event):
            x = self.root.winfo_x() + (event.x - self.drag_start_x)
            y = self.root.winfo_y() + (event.y - self.drag_start_y)
            self.root.geometry(f"+{x}+{y}")

        self.header_frame.bind("<Button-1>", on_drag_start)
        self.header_frame.bind("<B1-Motion>", on_drag_motion)
        self.title_lbl.bind("<Button-1>", on_drag_start)
        self.title_lbl.bind("<B1-Motion>", on_drag_motion)

    def _build_ui(self):
        # 1. Header Bar
        self.header_frame = tk.Frame(self.root, bg="#181b26", height=42, padx=10, pady=6)
        self.header_frame.pack(fill="x", side="top")

        self.status_dot = tk.Label(self.header_frame, text="●", fg="#2ed573", bg="#181b26", font=("Segoe UI", 12, "bold"))
        self.status_dot.pack(side="left", padx=(0, 6))

        self.title_lbl = tk.Label(
            self.header_frame,
            text="NeowEye · 涅奥之眼 (Laya)",
            fg=self.config.text_primary,
            bg="#181b26",
            font=("Microsoft YaHei UI", 11, "bold")
        )
        self.title_lbl.pack(side="left")

        # Header Control Buttons
        self.btn_alpha = tk.Button(
            self.header_frame, text="🌗", fg=self.config.text_secondary, bg="#262a38",
            activebackground="#3e4458", activeforeground="#ffffff", bd=0, padx=6, pady=2,
            font=("Segoe UI", 9), cursor="hand2", command=self._toggle_opacity
        )
        self.btn_alpha.pack(side="right", padx=2)

        self.btn_clickthrough = tk.Button(
            self.header_frame, text="🖱️穿透", fg=self.config.text_secondary, bg="#262a38",
            activebackground="#3e4458", activeforeground="#ffffff", bd=0, padx=6, pady=2,
            font=("Microsoft YaHei UI", 8), cursor="hand2", command=self._toggle_clickthrough
        )
        self.btn_clickthrough.pack(side="right", padx=2)

        # 2. Player Status Bar
        self.info_bar = tk.Frame(self.root, bg="#141722", padx=12, pady=5)
        self.info_bar.pack(fill="x", side="top")

        self.lbl_game_status = tk.Label(
            self.info_bar,
            text="[A1 F1] 铁甲战士 · HP 80/80 · ⚡ 3 · 💰 99",
            fg=self.config.text_secondary,
            bg="#141722",
            font=("Microsoft YaHei UI", 8)
        )
        self.lbl_game_status.pack(side="left")

        # 3. Global Tactical Alert Bar (Incense Burner, Pen Nib, etc.)
        self.relic_alert_bar = tk.Frame(self.root, bg="#2b1e1a", padx=10, pady=4)
        self.lbl_relic_alert = tk.Label(
            self.relic_alert_bar,
            text="",
            fg="#ffa502",
            bg="#2b1e1a",
            font=("Microsoft YaHei UI", 8, "bold"),
            justify="left",
            wraplength=350
        )
        self.lbl_relic_alert.pack(fill="x")
        self.relic_alert_bar.pack_forget()

        # 3.5 Environment Diagnostic Banner
        self.env_banner = tk.Frame(self.root, bg="#1a1e2b", padx=10, pady=8, highlightthickness=1, highlightbackground="#3d445c")
        self.env_banner_title = tk.Label(
            self.env_banner, text="🔍 环境检测中...", fg="#ffa502", bg="#1a1e2b",
            font=("Microsoft YaHei UI", 9, "bold"), anchor="w"
        )
        self.env_banner_title.pack(fill="x")

        self.env_banner_desc = tk.Label(
            self.env_banner, text="", fg=self.config.text_secondary, bg="#1a1e2b",
            font=("Microsoft YaHei UI", 8), anchor="w", justify="left", wraplength=340
        )
        self.env_banner_desc.pack(fill="x", pady=(2, 6))

        self.env_btn_frame = tk.Frame(self.env_banner, bg="#1a1e2b")
        self.env_btn_frame.pack(fill="x")
        self.env_banner.pack_forget()

        # 4. Multi-Tab Navigation Buttons Bar
        self.tab_bar = tk.Frame(self.root, bg="#1a1d2b", padx=6, pady=4)
        self.tab_bar.pack(fill="x", side="top")

        self.btn_tab_combat = tk.Button(
            self.tab_bar, text="⚔️ 战斗精算", fg="#ffffff", bg="#e55039",
            bd=0, padx=8, pady=3, font=("Microsoft YaHei UI", 8, "bold"),
            command=lambda: self.switch_tab("combat")
        )
        self.btn_tab_combat.pack(side="left", padx=2)

        self.btn_tab_macro = tk.Button(
            self.tab_bar, text="🧠 宏观决策", fg=self.config.text_secondary, bg="#262a38",
            bd=0, padx=8, pady=3, font=("Microsoft YaHei UI", 8),
            command=lambda: self.switch_tab("macro")
        )
        self.btn_tab_macro.pack(side="left", padx=2)

        self.btn_tab_relics = tk.Button(
            self.tab_bar, text="🏺 遗物看板", fg=self.config.text_secondary, bg="#262a38",
            bd=0, padx=8, pady=3, font=("Microsoft YaHei UI", 8),
            command=lambda: self.switch_tab("relics")
        )
        self.btn_tab_relics.pack(side="left", padx=2)

        self.btn_tab_deck = tk.Button(
            self.tab_bar, text="🃏 牌库透视", fg=self.config.text_secondary, bg="#262a38",
            bd=0, padx=8, pady=3, font=("Microsoft YaHei UI", 8),
            command=lambda: self.switch_tab("deck")
        )
        self.btn_tab_deck.pack(side="left", padx=2)

        # 5. Main Content Container
        self.content_frame = tk.Frame(self.root, bg=self.config.bg_color, padx=10, pady=8)
        self.content_frame.pack(fill="both", expand=True)

        self.card_box = tk.Frame(self.content_frame, bg=self.config.card_bg, padx=12, pady=10, relief="flat")
        self.card_box.pack(fill="both", expand=True)

        self.sec_header = tk.Label(
            self.card_box,
            text="⚔️ 数学最优打法 (掉血最少)",
            fg=self.config.accent_color,
            bg=self.config.card_bg,
            font=("Microsoft YaHei UI", 11, "bold"),
            anchor="w"
        )
        self.sec_header.pack(fill="x", pady=(0, 6))

        self.inner_frame = tk.Frame(self.card_box, bg=self.config.card_bg)
        self.inner_frame.pack(fill="both", expand=True)

        # 6. Bottom Scenario Switcher & Hotkey Guide
        self.footer_frame = tk.Frame(self.root, bg="#181b26", padx=10, pady=6)
        self.footer_frame.pack(fill="x", side="bottom")

        lbl_scen = tk.Label(self.footer_frame, text="场景:", fg=self.config.text_secondary, bg="#181b26", font=("Microsoft YaHei UI", 8))
        lbl_scen.pack(side="left", padx=(0, 4))

        self.scenario_var = tk.StringVar(value="切换测试对局场景...")
        self.scenario_combo = ttk.Combobox(
            self.footer_frame, textvariable=self.scenario_var, state="readonly", font=("Microsoft YaHei UI", 8), width=24
        )
        self.scenario_combo.pack(side="left", fill="x", expand=True)
        self.scenario_combo.bind("<<ComboboxSelected>>", self._on_scenario_changed)

        lbl_hint = tk.Label(self.footer_frame, text=" [F1隐藏 F2穿透]", fg="#747d8c", bg="#181b26", font=("Segoe UI", 7))
        lbl_hint.pack(side="right", padx=(4, 0))

    def switch_tab(self, tab_name: str):
        """Switches between Combat, Macro, Relics, and Deck tabs."""
        self.current_tab = tab_name
        buttons = {
            "combat": (self.btn_tab_combat, "#e55039"),
            "macro": (self.btn_tab_macro, "#1e90ff"),
            "relics": (self.btn_tab_relics, "#ffa502"),
            "deck": (self.btn_tab_deck, "#9b59b6")
        }

        for name, (btn, active_color) in buttons.items():
            if name == tab_name:
                btn.config(bg=active_color, fg="#ffffff", font=("Microsoft YaHei UI", 8, "bold"))
            else:
                btn.config(bg="#262a38", fg=self.config.text_secondary, font=("Microsoft YaHei UI", 8))

        if tab_name == "combat":
            if self.last_combat_plan:
                self.show_combat_plan(self.last_combat_plan)
        elif tab_name == "macro":
            if self.last_macro_decision:
                self.show_macro_decision(self.last_macro_decision)
        elif tab_name == "relics":
            self.show_relic_tab(self.last_relic_alerts)
        elif tab_name == "deck":
            if self.last_deck_stats:
                self.show_deck_tab(self.last_deck_stats)

    def set_scenarios(self, scenario_names: List[str]):
        self.scenario_combo["values"] = scenario_names
        if scenario_names:
            self.scenario_combo.current(0)

    def _on_scenario_changed(self, event=None):
        name = self.scenario_var.get()
        if self.on_scenario_select:
            self.on_scenario_select(name)

    def _toggle_opacity(self):
        current = self.root.attributes("-alpha")
        new_alpha = 0.70 if current > 0.85 else (0.45 if current > 0.60 else 0.92)
        self.root.attributes("-alpha", new_alpha)

    def _toggle_clickthrough(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if not self.is_click_through:
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
                self.btn_clickthrough.config(text="🔒穿透开启", fg="#2ed573")
                self.is_click_through = True
            else:
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style & ~WS_EX_TRANSPARENT)
                self.btn_clickthrough.config(text="🖱️穿透", fg=self.config.text_secondary)
                self.is_click_through = False
        except Exception as e:
            logger.warning(f"Failed to toggle click-through: {e}")

    def _toggle_minimize(self):
        if self.is_minimized:
            self.content_frame.pack(fill="both", expand=True)
            self.tab_bar.pack(fill="x", side="top", after=self.relic_alert_bar)
            self.is_minimized = False
        else:
            self.content_frame.pack_forget()
            self.tab_bar.pack_forget()
            self.is_minimized = True

    def update_game_info(self, character: str, act: int, floor: int, hp: int, max_hp: int, energy: int, gold: int):
        char_zh = {"IRONCLAD": "铁甲战士", "THE_SILENT": "静默猎手", "DEFECT": "故障机器人", "WATCHER": "观者"}.get(character.upper(), character)
        info_str = f"[第{act}幕 第{floor}层] {char_zh} · HP {hp}/{max_hp} · ⚡ {energy} · 💰 {gold}"
        self.lbl_game_status.config(text=info_str)

    def update_relic_alerts(self, alerts: List[RelicAlert]):
        self.last_relic_alerts = alerts
        if not alerts:
            self.relic_alert_bar.pack_forget()
            return
        lines = [f"💡 {a.message}" for a in alerts]
        self.lbl_relic_alert.config(text="\n".join(lines))
        self.relic_alert_bar.pack(fill="x", side="top", after=self.info_bar)

    def show_combat_plan(self, plan: CombatPlan):
        """Renders in-combat mathematical plan."""
        self.last_combat_plan = plan
        if self.current_tab != "combat":
            return

        for widget in self.inner_frame.winfo_children():
            widget.destroy()

        self.sec_header.config(text="⚔️ 数学最优打法 (掉血最少)", fg=self.config.accent_color)

        steps_box = tk.Frame(self.inner_frame, bg=self.config.card_bg)
        steps_box.pack(fill="both", expand=True, pady=(0, 6))

        if not plan.steps:
            lbl = tk.Label(steps_box, text="⚠️ 无推荐动作 (能量不足或无需出牌)", fg=self.config.text_secondary, bg=self.config.card_bg, font=("Microsoft YaHei UI", 9))
            lbl.pack(pady=10)
        else:
            for idx, step in enumerate(plan.steps, 1):
                step_row = tk.Frame(steps_box, bg="#222738", padx=6, pady=4)
                step_row.pack(fill="x", pady=2)

                lbl_num = tk.Label(step_row, text=f"[{idx}]", fg=self.config.accent_gold, bg="#222738", font=("Segoe UI", 9, "bold"), width=3)
                lbl_num.pack(side="left")

                type_icon = "⚔️" if step.card_info.card_type == "ATTACK" else ("🛡️" if step.card_info.card_type == "SKILL" else "✨")
                lbl_card = tk.Label(step_row, text=f"{type_icon} {step.card_info.name_zh}", fg=self.config.text_primary, bg="#222738", font=("Microsoft YaHei UI", 8, "bold"))
                lbl_card.pack(side="left", padx=3)

                lbl_cost = tk.Label(step_row, text=f"{step.card_info.cost}⚡", fg="#1e90ff", bg="#181b26", font=("Segoe UI", 8, "bold"), padx=3, pady=1)
                lbl_cost.pack(side="left", padx=3)

                details = []
                if step.target_name: details.append(f"➔ {step.target_name}")
                if step.damage_dealt > 0: details.append(f"{step.damage_dealt}伤")
                if step.block_gained > 0: details.append(f"+{step.block_gained}防")
                if step.notes: details.append(step.notes.strip())

                lbl_detail = tk.Label(step_row, text=" ".join(details), fg="#eccc68" if step.damage_dealt > 0 else "#2ed573", bg="#222738", font=("Microsoft YaHei UI", 8))
                lbl_detail.pack(side="right")

        # Tactical Forecast Box
        pred_frame = tk.Frame(self.inner_frame, bg="#131620", padx=8, pady=6)
        pred_frame.pack(fill="x", side="bottom")

        hp_loss = plan.projected_hp_loss
        if hp_loss == 0:
            dmg_text = f"🛡️ 预计掉血: 0 HP (完美格挡! 抵挡全部 {plan.initial_incoming_damage} 伤)"
            dmg_fg = "#2ed573"
        else:
            dmg_text = f"⚠️ 预计掉血: -{hp_loss} HP (承受 {plan.projected_incoming_damage} 伤, 抵挡 {plan.projected_block} 点)"
            dmg_fg = "#ff4757"

        lbl_dmg = tk.Label(pred_frame, text=dmg_text, fg=dmg_fg, bg="#131620", font=("Microsoft YaHei UI", 9, "bold"), anchor="w")
        lbl_dmg.pack(fill="x")

        if getattr(plan, "end_of_turn_forecast", None):
            lbl_forecast = tk.Label(
                pred_frame,
                text=f"🔮 回合末结算: {' · '.join(plan.end_of_turn_forecast)}",
                fg="#a29bfe",
                bg="#131620",
                font=("Microsoft YaHei UI", 8),
                anchor="w"
            )
            lbl_forecast.pack(fill="x", pady=(1, 0))

        stat_parts = []
        if plan.monsters_killed > 0: stat_parts.append(f"💀 斩杀 {plan.monsters_killed} 敌")
        stat_parts.append(f"⚡ 剩余能量: {plan.remaining_energy}")
        if plan.final_stance != "None": stat_parts.append(f"🧘 姿态: {plan.final_stance}")
        stat_parts.append(f"⏱️ {plan.computation_time_ms}ms")

        lbl_stats = tk.Label(pred_frame, text=" · ".join(stat_parts), fg=self.config.text_secondary, bg="#131620", font=("Microsoft YaHei UI", 7), anchor="w")
        lbl_stats.pack(fill="x", pady=(2, 0))

    def show_macro_decision(self, decision: MacroDecision):
        """Renders Laya macro decisions."""
        self.last_macro_decision = decision
        if self.current_tab != "macro":
            return

        for widget in self.inner_frame.winfo_children():
            widget.destroy()

        self.sec_header.config(text=decision.title, fg=self.config.accent_blue)

        # Archetype Badge
        if decision.deck_archetype:
            lbl_arch = tk.Label(self.inner_frame, text=f"🎯 当前流派: {decision.deck_archetype}", fg="#70a1ff", bg=self.config.card_bg, font=("Microsoft YaHei UI", 8, "bold"), anchor="w")
            lbl_arch.pack(fill="x", pady=(0, 4))

        # Recommendation Box
        rec_frame = tk.Frame(self.inner_frame, bg="#1e2438", padx=8, pady=6)
        rec_frame.pack(fill="x", pady=(0, 6))

        lbl_rec_title = tk.Label(rec_frame, text="🌟 模型首选建议:", fg=self.config.text_secondary, bg="#1e2438", font=("Microsoft YaHei UI", 8), anchor="w")
        lbl_rec_title.pack(fill="x")

        lbl_rec = tk.Label(rec_frame, text=f"{decision.recommended_choice}  ({round(decision.confidence * 100, 1)}%)", fg="#ffa502", bg="#1e2438", font=("Microsoft YaHei UI", 11, "bold"), anchor="w")
        lbl_rec.pack(fill="x", pady=2)

        # Tactical / Boss / Deck Thickness Warning
        if decision.tactical_note:
            note_frame = tk.Frame(self.inner_frame, bg="#2b1a1a", padx=8, pady=5)
            note_frame.pack(fill="x", pady=(0, 6))
            lbl_note = tk.Label(note_frame, text=decision.tactical_note, fg="#ff7675", bg="#2b1a1a", font=("Microsoft YaHei UI", 8, "bold"), wraplength=310, justify="left")
            lbl_note.pack(fill="x")

        # Probability Meters
        if decision.choice_probabilities:
            dist_box = tk.Frame(self.inner_frame, bg=self.config.card_bg)
            dist_box.pack(fill="both", expand=True, pady=(0, 6))

            for opt_name, prob in sorted(decision.choice_probabilities.items(), key=lambda x: x[1], reverse=True):
                opt_row = tk.Frame(dist_box, bg="#222738", padx=6, pady=3)
                opt_row.pack(fill="x", pady=1)

                is_top = (opt_name == decision.recommended_choice)
                lbl_name = tk.Label(opt_row, text=opt_name, fg="#ffa502" if is_top else self.config.text_primary, bg="#222738", font=("Microsoft YaHei UI", 8, "bold" if is_top else "normal"), width=15, anchor="w")
                lbl_name.pack(side="left")

                bar_canvas = tk.Canvas(opt_row, width=110, height=8, bg="#151822", bd=0, highlightthickness=0)
                bar_canvas.pack(side="left", padx=4)
                bar_len = int(110 * prob)
                if bar_len > 0:
                    bar_canvas.create_rectangle(0, 0, bar_len, 8, fill="#ffa502" if is_top else "#3742fa", width=0)

                lbl_pct = tk.Label(opt_row, text=f"{round(prob * 100, 1)}%", fg=self.config.text_secondary, bg="#222738", font=("Segoe UI", 7))
                lbl_pct.pack(side="right")

        # Metrics Box
        metrics_frame = tk.Frame(self.inner_frame, bg="#131620", padx=8, pady=5)
        metrics_frame.pack(fill="x", side="bottom")

        items = []
        if decision.noul_probability is not None: items.append(f"🛑 {decision.noul_label}: {round(decision.noul_probability * 100, 1)}%")
        if decision.score_value is not None: items.append(f"🎯 {decision.score_label}: {round(decision.score_value, 2)}")
        items.append(f"⚡ 延迟: {decision.latency_ms}ms")

        lbl_metrics = tk.Label(metrics_frame, text=" · ".join(items), fg="#70a1ff", bg="#131620", font=("Microsoft YaHei UI", 7), anchor="w")
        lbl_metrics.pack(fill="x")

    def show_relic_tab(self, alerts: List[RelicAlert]):
        """Renders the dedicated Relic & Counter Tracker tab."""
        for widget in self.inner_frame.winfo_children():
            widget.destroy()

        self.sec_header.config(text="🏺 遗物看板与计数监控", fg=self.config.accent_gold)

        if not alerts:
            lbl = tk.Label(self.inner_frame, text="暂无交互式遗物计数\n(香炉/钢笔尖/手里剑/日晷等拾取后将在此显示)", fg=self.config.text_secondary, bg=self.config.card_bg, font=("Microsoft YaHei UI", 8), justify="center")
            lbl.pack(pady=40)
            return

        box = tk.Frame(self.inner_frame, bg=self.config.card_bg)
        box.pack(fill="both", expand=True)

        for alert in alerts:
            row = tk.Frame(box, bg="#222738" if alert.alert_level == "INFO" else "#332218", padx=8, pady=6)
            row.pack(fill="x", pady=2)

            lbl_title = tk.Label(row, text=alert.relic_name, fg="#ffa502" if alert.alert_level != "INFO" else self.config.text_primary, bg=row.cget("bg"), font=("Microsoft YaHei UI", 8, "bold"), anchor="w")
            lbl_title.pack(fill="x")

            lbl_msg = tk.Label(row, text=alert.message, fg="#f1f2f6", bg=row.cget("bg"), font=("Microsoft YaHei UI", 8), wraplength=310, justify="left")
            lbl_msg.pack(fill="x", pady=(2, 0))

    def show_deck_tab(self, stats: DeckStats):
        """Renders the Deck & Draw Probability Tracker tab."""
        self.last_deck_stats = stats
        if self.current_tab != "deck":
            return

        for widget in self.inner_frame.winfo_children():
            widget.destroy()

        self.sec_header.config(text="🃏 牌库透视与抽牌概率", fg="#9b59b6")

        # Draw Counts Header
        count_frame = tk.Frame(self.inner_frame, bg="#1a1c28", padx=8, pady=5)
        count_frame.pack(fill="x", pady=(0, 6))

        count_text = f"抽牌堆: {stats.total_draw_count} 张  ·  弃牌堆: {stats.total_discard_count} 张  ·  消耗堆: {stats.total_exhaust_count} 张"
        lbl_counts = tk.Label(count_frame, text=count_text, fg="#f1f2f6", bg="#1a1c28", font=("Microsoft YaHei UI", 8, "bold"))
        lbl_counts.pack()

        # Next Turn Probability Gauges
        prob_box = tk.Frame(self.inner_frame, bg="#222738", padx=8, pady=6)
        prob_box.pack(fill="x", pady=(0, 6))

        lbl_prob_title = tk.Label(prob_box, text="🎲 下回合抓牌概率预测 (抽5张):", fg=self.config.text_secondary, bg="#222738", font=("Microsoft YaHei UI", 8, "bold"), anchor="w")
        lbl_prob_title.pack(fill="x", pady=(0, 4))

        # Block prob
        row_b = tk.Frame(prob_box, bg="#222738")
        row_b.pack(fill="x", pady=1)
        tk.Label(row_b, text="🛡️ 抽到至少1张格挡牌:", fg="#2ed573", bg="#222738", font=("Microsoft YaHei UI", 8), width=18, anchor="w").pack(side="left")
        tk.Label(row_b, text=f"{round(stats.prob_draw_block * 100, 1)}%", fg="#2ed573", bg="#222738", font=("Segoe UI", 8, "bold")).pack(side="right")

        # Attack prob
        row_a = tk.Frame(prob_box, bg="#222738")
        row_a.pack(fill="x", pady=1)
        tk.Label(row_a, text="⚔️ 抽到至少1张攻击牌:", fg="#ff4757", bg="#222738", font=("Microsoft YaHei UI", 8), width=18, anchor="w").pack(side="left")
        tk.Label(row_a, text=f"{round(stats.prob_draw_attack * 100, 1)}%", fg="#ff4757", bg="#222738", font=("Segoe UI", 8, "bold")).pack(side="right")

        # Curse prob
        row_c = tk.Frame(prob_box, bg="#222738")
        row_c.pack(fill="x", pady=1)
        tk.Label(row_c, text="🛑 抽到诅咒/状态废牌:", fg="#ffa502", bg="#222738", font=("Microsoft YaHei UI", 8), width=18, anchor="w").pack(side="left")
        tk.Label(row_c, text=f"{round(stats.prob_draw_curse_status * 100, 1)}%", fg="#ffa502", bg="#222738", font=("Segoe UI", 8, "bold")).pack(side="right")

        # Tactical Advice
        if stats.tactical_advice:
            adv_frame = tk.Frame(self.inner_frame, bg="#241b2b", padx=8, pady=5)
            adv_frame.pack(fill="x", pady=(0, 6))
            lbl_adv = tk.Label(adv_frame, text=stats.tactical_advice, fg="#d29bfe", bg="#241b2b", font=("Microsoft YaHei UI", 8, "bold"), wraplength=310, justify="left")
            lbl_adv.pack(fill="x")

        # Draw pile cards sample
        if stats.draw_pile_cards:
            lbl_list_title = tk.Label(self.inner_frame, text=f"📋 抽牌堆明细 (剩余 {len(stats.draw_pile_cards)} 张):", fg=self.config.text_secondary, bg=self.config.card_bg, font=("Microsoft YaHei UI", 8), anchor="w")
            lbl_list_title.pack(fill="x", pady=(2, 2))
            sample_text = ", ".join(stats.draw_pile_cards[:16])
            if len(stats.draw_pile_cards) > 16:
                sample_text += f" 等共 {len(stats.draw_pile_cards)} 张"
            lbl_sample = tk.Label(self.inner_frame, text=sample_text, fg="#a4b0be", bg=self.config.card_bg, font=("Microsoft YaHei UI", 7), wraplength=310, justify="left")
            lbl_sample.pack(fill="x")

    def update_env_status(
        self,
        diag,
        on_refresh: Optional[Callable[[], None]] = None,
        on_select_folder: Optional[Callable[[str], None]] = None,
        on_subscribe: Optional[Callable[[], None]] = None,
        on_install_offline: Optional[Callable[[str], None]] = None
    ):
        """Updates the environment diagnostic banner and status indicators."""
        for w in self.env_btn_frame.winfo_children():
            w.destroy()

        if diag.status_code == "READY":
            self.status_dot.config(text="●", fg="#2ed573")
            source_tag = f" ({diag.game_source})" if diag.game_source else ""
            self.lbl_game_status.config(
                text=f"[就绪] 尖塔联动已就绪{source_tag} · 等待对局开始..."
            )
            self.env_banner.pack_forget()
            return

        # Pack banner between info_bar and tab_bar
        self.env_banner.pack(fill="x", side="top", padx=10, pady=(0, 6), before=self.tab_bar)

        if diag.status_code == "MODS_MISSING":
            self.status_dot.config(text="●", fg="#ffa502")
            self.lbl_game_status.config(text="[注意] 检测到游戏已安装，但缺少通信 Mod")
            self.env_banner_title.config(text="⚠️ 缺少必备通信 Mod", fg="#ffa502")
            self.env_banner_desc.config(
                text=f"游戏目录: {diag.game_path}\n缺少: {'、'.join(diag.missing_mods)}"
            )

            if on_subscribe:
                btn_sub = tk.Button(
                    self.env_btn_frame, text="🌐 创意工坊一键订阅", fg="#ffffff", bg="#1e90ff",
                    activebackground="#2f3542", bd=0, padx=8, pady=3,
                    font=("Microsoft YaHei UI", 8, "bold"), cursor="hand2",
                    command=on_subscribe
                )
                btn_sub.pack(side="left", padx=(0, 4))

            if on_install_offline and diag.game_path:
                btn_offline = tk.Button(
                    self.env_btn_frame, text="📦 安装离线补丁", fg="#ffffff", bg="#2ed573",
                    activebackground="#2f3542", bd=0, padx=8, pady=3,
                    font=("Microsoft YaHei UI", 8, "bold"), cursor="hand2",
                    command=lambda: on_install_offline(diag.game_path)
                )
                btn_offline.pack(side="left", padx=(0, 4))

            if on_refresh:
                btn_ref = tk.Button(
                    self.env_btn_frame, text="🔄 刷新", fg=self.config.text_secondary, bg="#262a38",
                    activebackground="#3e4458", bd=0, padx=6, pady=3,
                    font=("Microsoft YaHei UI", 8), cursor="hand2",
                    command=on_refresh
                )
                btn_ref.pack(side="right")

        elif diag.status_code == "GAME_NOT_FOUND":
            self.status_dot.config(text="●", fg="#ff7f50")
            self.lbl_game_status.config(text="[提示] 未检测到《杀戮尖塔》安装目录")
            self.env_banner_title.config(text="🔍 未检测到《杀戮尖塔》目录", fg="#ff7f50")
            self.env_banner_desc.config(
                text="未能在常见路径找到游戏。若已安装请手动指定；若未安装可体验演示模式。"
            )

            def _choose_folder():
                chosen = filedialog.askdirectory(
                    title="选择《杀戮尖塔》游戏安装目录 (包含 SlayTheSpire.exe 或 desktop-1.0.jar)"
                )
                if chosen and on_select_folder:
                    on_select_folder(chosen)

            btn_browse = tk.Button(
                self.env_btn_frame, text="📁 手动选择游戏目录", fg="#ffffff", bg="#1e90ff",
                activebackground="#2f3542", bd=0, padx=8, pady=3,
                font=("Microsoft YaHei UI", 8, "bold"), cursor="hand2",
                command=_choose_folder
            )
            btn_browse.pack(side="left", padx=(0, 4))

            btn_demo = tk.Button(
                self.env_btn_frame, text="🎮 体验演示推演", fg="#ffffff", bg="#e55039",
                activebackground="#2f3542", bd=0, padx=8, pady=3,
                font=("Microsoft YaHei UI", 8, "bold"), cursor="hand2",
                command=lambda: self.switch_tab("combat")
            )
            btn_demo.pack(side="left", padx=(0, 4))

            if on_refresh:
                btn_ref = tk.Button(
                    self.env_btn_frame, text="🔄 刷新", fg=self.config.text_secondary, bg="#262a38",
                    activebackground="#3e4458", bd=0, padx=6, pady=3,
                    font=("Microsoft YaHei UI", 8), cursor="hand2",
                    command=on_refresh
                )
                btn_ref.pack(side="right")

    def run(self):
        self.root.mainloop()

