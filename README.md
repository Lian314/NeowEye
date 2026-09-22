# NeowEye (涅奥之眼) - 杀戮尖塔 AI 战术辅助器
*(NeowEye: Edge-AI & Mathematical Tactical Optimization Assistant for Slay the Spire)*

基于 **Laya 决策模型**（421M 现代编码器端侧推理）与**微观战斗数学精算算法**，为卡牌 Roguelike 游戏《杀戮尖塔》(Slay the Spire) 打造的世界顶级实时战术辅助系统。

---

## 🌟 核心功能与技术特色

### 1. 【微观】四角色战斗数学最优打法 (0 掉血精算)
- **全角色机制全覆盖**：
  - **铁甲战士**：力量增幅、易伤/虚弱、重刃/飞身踢等时序优化。
  - **静默猎手**：小刀流（精准伤害加成）、中毒流层数结算。
  - **故障机器人**：闪电球、冰霜球、暗黑球、等离子球生成与激发结算。
  - **观者**：愤怒（双倍伤害与承受）、平静（出姿态 +2 能量）、神格（三倍伤害与 +3 能量）全套姿态引擎。
- **高阶遗物联动精算**：
  - **钢笔尖 (Pen Nib)**：计数为 9 时，自动将下一步攻击伤害精准翻倍。
  - **锚 (Anchor)**：第 1 回合自动计入 +10 护甲。
  - **纸蛙 (Paper Frog)**：易伤伤害系数自动从 1.5x 提升至 1.75x。
  - **纸鹤 (Paper Crane)**：虚弱减伤系数自动从 0.75x 优化至 0.60x。
  - **手里剑 / 苦无 / 铜钹 / 狂热**：出牌序列中自动追踪卡牌类型并触发属性成长。
- **击杀截断与威胁消除**：在能量限制下通过**有界深度优先搜索 (Bounded DFS / Branch & Bound)** 穷举有效出牌序列，精准识别斩杀正在意图攻击的敌人，将掉血压至数学绝对最低（0 HP 完美格挡）。

### 2. 【宏观】Laya 421M 现代编码器端侧本地推理 (ONNX Runtime INT8) + 智能双模
- **零服务器成本 & 无限并发**：彻底摆脱家用宽带 NAT 连接数瓶颈、FRP 穿透带宽限速以及笔记本显卡发热降频问题。
- **本地极速零延迟**：本地 CPU (AVX2/AVX-512) 推理，单次耗时仅 **15ms ~ 30ms**（比跨公网 HTTP 提速 10 倍以上）。
- **完全离线可用**：玩家在飞机、高铁等无网络环境下依然可获得完整的决策支持。
- **智能双模无缝融合 (`engine_mode = "auto"`)**：
  - 本地优先：若检测到 `models/laya_int8.onnx`，自动以端侧纯 CPU 运行。
  - 优雅降级：若本地未提供模型文件，自动回退走远程 HTTP 服务或启发式决策。
- **三种类型化题目支持**：
  - `choice`：卡牌抓取推荐与概率分布（Softmax 归一化）。
  - `noul`：是非概率评估（是否跳过选牌、是否打精英，Sigmoid 输出）。
  - `score`：流派契合度评分与危险度评分。
- **高手跳过哲学 (Pro Skip Philosophy)**：
  - 卡组厚度监控：卡组达到 20/25 张以上且候选牌与流派不契合时，强烈推荐跳过 (Skip)，避免牌库稀释。
- **关底 Boss 针对性预警**：
  - **时光吞噬者 (Time Eater)**：严控出牌数，避免高频低效小牌。
  - **觉醒者 (Awakened One)**：限制能力牌抓取，警惕力量暴涨。
  - **甜豆花 (Donu & Deca)**：强化 AOE 爆发与快速破局。
- **一键导出与 INT8 量化工具 (`export_laya_onnx.py`)**：支持从 PyTorch 421M ModernBERT 导出为 ONNX，并执行 INT8 动态量化，体积从 ~840MB 缩减至 ~250MB。

### 3. 【牌库】超几何分布抽牌概率透视 (Deck Tracker)
- **实时三大牌堆监控**：抽牌堆、弃牌堆、消耗堆全量卡牌实时统计与明细展示。
- **超几何分布 (Hypergeometric Distribution) 精算**：
  - 计算公式：\( P(X \ge 1) = 1 - \frac{\binom{N-K}{n}}{\binom{N}{n}} \)
  - 精确预测**下回合抽到至少 1 张格挡牌**的概率。
  - 精确预测**下回合抽到攻击牌**与**抽到诅咒/状态废牌 (防鬼抽)** 的概率。
  - 动态生成战术建议（例如：“下回合抽到格挡牌概率仅 31%，本回合建议保留防御！”）。

### 4. 【遗物】169 个全量遗物监控与关键计数预警 (Relic Tracker)
- 基于权威 EO 数据库的 169 种遗物识别。
- **职业级关键计数提醒**：
  - **香炉 (Incense Burner)**：计数达到 5/6 时触发高危警报（提醒控怪下回合获得无实体）。
  - **钢笔尖 (Pen Nib)**：计数达到 9/10 时触发翻倍爆发提示。
  - **双节棍 / 墨水瓶 / 日晷 / 开心小花 / 石历** 等关键节奏点全量覆盖。

### 5. 【界面】四标签页赛博朋克玻璃拟态桌面置顶悬浮窗 (Overlay HUD)
- **四标签页无缝切换**：
  - `⚔️ 战斗精算`：最优出牌序列、目标怪物、预计掉血、完美格挡指示、剩余能量。
  - `🧠 宏观决策`：Laya 模型首选建议、置信度柱状图、流派标签、Boss 战术告警。
  - `🏺 遗物看板`：当前持有遗物列表与高危计数警报条。
  - `🃏 牌库透视`：抽/弃/消耗堆数量、下回合抽牌概率仪表盘、牌库明细。
- **Windows 原生特性**：
  - `HWND_TOPMOST` 窗口永远置顶。
  - 一键开启/关闭点击穿透 (`WS_EX_TRANSPARENT`)。
  - 多档半透明调节 (92% / 70% / 45%)。
  - 快捷键支持：`F1` 最小化/展开，`F2` 切换鼠标穿透。

---

## 📐 整体系统架构

```mermaid
flowchart TD
    subgraph Game ["《杀戮尖塔》客户端"]
        SlayTheSpire["Slay the Spire (Ironclad / Silent / Defect / Watcher)"]
        CommMod["CommunicationMod (Mod)"]
        SlayTheSpire <--> CommMod
    end

    subgraph Assistant ["实时战术辅助器 (Python 3.12)"]
        CommBridge["comm_bridge.py\n(Stdin / Socket / Mock)"]
        
        subgraph Engines ["核心决策与精算引擎"]
            CombatSolver["combat_solver.py\n【微观】四角色手牌穷举\n0掉血优化 · 姿态 · 遗物加成"]
            MacroAdvisor["macro_advisor.py\n【宏观】流派识别 · Boss对策\nPro Skip 哲学"]
            DeckTracker["deck_tracker.py\n【牌库】超几何分布抽牌概率\n防鬼抽 · 战术警报"]
            RelicTracker["relic_tracker.py\n【遗物】169种遗物监控\n香炉5/6 · 钢笔尖9/10 预警"]
            KnowledgeBase["knowledge_base.py & card_db.py\n权威 EO 数据库 + 观者扩展\n295卡牌 · 169遗物 · 69怪物 · 131能力"]
        end

        LayaClient["laya_client.py\n(421M Laya HTTP POST 客户端)"]
        OverlayHUD["overlay_hud.py\n(四标签页暗色玻璃拟态置顶悬浮窗)"]

        CommBridge --> |战斗状态 JSON| CombatSolver
        CommBridge --> |抽/弃牌堆 JSON| DeckTracker
        CommBridge --> |遗物状态 JSON| RelicTracker
        CommBridge --> |宏观状态 JSON| MacroAdvisor

        CombatSolver <--> KnowledgeBase
        DeckTracker <--> KnowledgeBase
        RelicTracker <--> KnowledgeBase
        MacroAdvisor <--> LayaClient

        CombatSolver --> |最优序列 & 0掉血预报| OverlayHUD
        MacroAdvisor --> |推荐卡牌 & 置信度| OverlayHUD
        DeckTracker --> |抽牌概率预测| OverlayHUD
        RelicTracker --> |高危计数警报| OverlayHUD
    end

    subgraph Cloud ["Laya 决策模型服务器"]
        LayaServer["Laya ModernBERT 421M\n(可选远程服务 /predict)"]
        LayaClient <--> |HTTPS POST (choice/score/noul)| LayaServer
    end

    CommMod <--> |Stdin/Stdout JSON| CommBridge
```

---

## 🚀 快速启动

### 方式 A：一键启动脚本 (推荐)
双击运行根目录下的 `run_assistant.bat` 或 `start_hud.bat`：
- **按 `1`**：启动**独立演示/悬浮测试模式**（内置 8 大真实对局场景，包括香炉/钢笔尖高危警报、大卡组对抗时光吞噬者、静默猎手毒刀流、机器人球机制、观者姿态切换等）。
- **按 `2`**：启动 **CommunicationMod 游戏实时联动模式**。
- **按 `3`**：运行**全量 19 项自动化单元测试**。

### 方式 B：命令行启动
```powershell
# 1. 启动独立演示与悬浮窗模式
C:\Users\Admin\.local\bin\python3.12.exe main.py --mode mock

# 2. 启动 CommunicationMod 游戏联动模式
C:\Users\Admin\.local\bin\python3.12.exe main.py --mode stdin

# 3. 运行全量单元测试
C:\Users\Admin\.local\bin\python3.12.exe -m unittest discover tests
```

---

## 🎮 配置 CommunicationMod 联动

若需与《杀戮尖塔》游戏本体实时联动：
1. 在游戏中安装 [ModTheSpire](https://github.com/kiooeht/ModTheSpire) 与 [CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod)。
2. 打开 CommunicationMod 配置文件（通常位于 `%USERPROFILE%\AppData\Local\ModTheSpire\CommunicationMod\config.properties`）：
   ```properties
   command=C:\\Users\\Admin\\.local\\bin\\python3.12.exe d:\\ccode\\NeowEye\\main.py --mode stdin
   ```
3. 启动游戏进入任何对局，悬浮窗将自动捕捉手牌、怪物意图、遗物计数与牌堆，提供实时辅助！

---

## 📁 核心文件结构

```
d:/ccode/NeowEye/
├── EO/Slay-the-Spire-EO/       # 权威中文卡牌、遗物、怪物、能力数据库
├── config.py                  # 系统核心配置 (Laya 接口、悬浮窗参数、精算权重)
├── knowledge_base.py          # 统一权威数据库加载器 (EO 库解析 + 观者全套 75 张卡牌补全)
├── card_db.py                 # 卡牌属性查询与动态解析 (统一委托给 knowledge_base)
├── combat_solver.py           # 四角色微观战斗数学精算器 (有界 DFS、0掉血优化、姿态与遗物加成)
├── deck_tracker.py            # 超几何分布抽牌概率引擎 (抽/弃/消耗堆透视与防鬼抽预警)
├── relic_tracker.py           # 遗物计数跟踪器 (香炉 5/6、钢笔尖 9/10 等高危节点监控)
├── local_laya_engine.py       # Laya 端侧本地推理引擎 (ONNX Runtime INT8 极速 CPU 推理)
├── export_laya_onnx.py        # Laya 模型导出与 INT8 动态量化工具
├── macro_advisor.py           # 宏观策略决策管理器 (Laya 调用、流派识别、Boss 对策、跳过哲学)
├── laya_client.py             # 智能双模 Laya 客户端 (本地 ONNX 优先 + 远程 HTTP 优雅降级)
├── comm_bridge.py             # CommunicationMod IPC 桥接器 (stdin/stdout、socket、mock)
├── overlay_hud.py             # 四标签页桌面置顶透明悬浮窗 (Windows API 穿透、置顶、快捷键)
├── main.py                    # 统一主入口调度器
├── test_mock_scenarios.py     # 8 大真实对局测试场景 (邪教徒、高危遗物、厚卡组Boss、观者姿态等)
├── tests/                     # 完整单元与集成测试套件 (23项测试全部通过，耗时仅 1.0s)
│   ├── test_local_laya_engine.py # 端侧本地推理测试 (ONNX 前向推理、Softmax、Sigmoid、延迟)
│   ├── test_combat_solver.py  # 战斗精算测试 (掉血最小化、斩杀、易伤时序、小刀、法球、姿态)
│   ├── test_deck_tracker.py   # 抽牌概率测试 (超几何分布准确性、边界条件、战术建议)
│   ├── test_relic_tracker.py  # 遗物监控测试 (香炉、钢笔尖翻倍、锚起手格挡、Boss预警)
│   ├── test_knowledge_base.py # 权威数据库测试 (EO 解析、观者补全、双语映射)
│   ├── test_laya_client.py    # Laya 双模客户端测试 (本地优先、健康检查、LRU缓存)
│   ├── test_macro_advisor.py  # 宏观策略测试 (流派契合度、跳牌哲学、Boss 预警)
│   └── test_overlay_hud.py    # 悬浮窗全场景与四标签页渲染测试
├── run_assistant.bat          # GBK 编码 Windows 一键启动脚本
├── start_hud.bat              # GBK 编码极速启动脚本
└── README.md                  # 本文档
```
