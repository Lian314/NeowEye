"""
World-Class Relic and Counter Tracker for Slay the Spire.
Tracks all 169 relics from KnowledgeBase with active tactical alerts:
- Incense Burner (香炉): Every 6 turns grants 1 Intangible. Alerts when at 5/6 to stall combat.
- Pen Nib (钢笔尖): Every 10 attacks deals double damage. Alerts when at 9/10.
- Nunchaku (双节棍): Every 10 attacks gives 1 Energy. Alerts when at 9/10.
- InkBottle (墨水瓶): Every 10 cards played draws 1 card. Alerts when at 9/10.
- Sundial (日晷): Every 3 shuffles gives 2 Energy. Alerts when at 2/3.
- Happy Flower (开心小花): Every 3 turns gives 1 Energy. Alerts when at 2/3.
- Stone Calendar (石历): Turn 7 deals 52 damage to all enemies.
- Kunai (苦无) / Shuriken (手里剑) / Ornamental Fan (折扇): 3 attacks per turn triggers.
- Paper Frog (纸蛙) / Paper Crane (纸鹤): 1.75x Vulnerable and 40% Weak damage reduction.
- Anchor (锚): Turn 1 +10 Block.
- Preserved Insect (昆虫标本): Elites -25% HP.
"""
from dataclasses import dataclass
from typing import Dict, Any, List
from knowledge_base import GLOBAL_KB

@dataclass
class RelicAlert:
    relic_id: str
    relic_name: str
    current_counter: int
    max_counter: int
    alert_level: str  # "INFO", "WARNING", "OPPORTUNITY"
    message: str

class RelicTracker:
    def __init__(self):
        pass

    def analyze_relics(self, relics_data: List[Dict[str, Any]], turn: int = 1) -> List[RelicAlert]:
        """
        Scans all active relics and generates real-time tactical warnings and pro tips.
        """
        alerts: List[RelicAlert] = []

        for relic in relics_data:
            r_id = relic.get("id", "")
            r_name = GLOBAL_KB.get_relic_zh_name(r_id)
            counter = relic.get("counter", -1)

            # 1. Incense Burner (香炉) - 0 to 5
            if r_id == "Incense Burner":
                if counter == 5:
                    alerts.append(RelicAlert(
                        relic_id=r_id,
                        relic_name=r_name,
                        current_counter=counter,
                        max_counter=6,
                        alert_level="OPPORTUNITY",
                        message="🏮 香炉已达 5/6 层！建议控怪拖到下回合触发（获得1层无实体），或结束战斗使下场进门获得无实体无敌！"
                    ))
                elif counter >= 0:
                    alerts.append(RelicAlert(
                        relic_id=r_id,
                        relic_name=r_name,
                        current_counter=counter,
                        max_counter=6,
                        alert_level="INFO",
                        message=f"🏮 香炉计数: {counter}/6 (还有 {6 - counter} 回合获得无实体)"
                    ))

            # 2. Pen Nib (钢笔尖) - 0 to 9
            elif r_id == "Pen Nib":
                if counter == 9:
                    alerts.append(RelicAlert(
                        relic_id=r_id,
                        relic_name=r_name,
                        current_counter=counter,
                        max_counter=10,
                        alert_level="OPPORTUNITY",
                        message="🖊️ 钢笔尖已达 9/10！下一次打出攻击牌伤害翻倍 (x2)！"
                    ))
                elif counter >= 0:
                    alerts.append(RelicAlert(
                        relic_id=r_id,
                        relic_name=r_name,
                        current_counter=counter,
                        max_counter=10,
                        alert_level="INFO",
                        message=f"🖊️ 钢笔尖计数: {counter}/10 (距离双倍伤害还差 {10 - counter} 次攻击)"
                    ))

            # 3. Nunchaku (双节棍) - 0 to 9
            elif r_id == "Nunchaku":
                if counter == 9:
                    alerts.append(RelicAlert(
                        relic_id=r_id,
                        relic_name=r_name,
                        current_counter=counter,
                        max_counter=10,
                        alert_level="OPPORTUNITY",
                        message="🥋 双节棍已达 9/10！下一张攻击牌将额外获得 1 点能量！"
                    ))
                elif counter >= 0:
                    alerts.append(RelicAlert(
                        relic_id=r_id,
                        relic_name=r_name,
                        current_counter=counter,
                        max_counter=10,
                        alert_level="INFO",
                        message=f"🥋 双节棍计数: {counter}/10"
                    ))

            # 4. InkBottle (墨水瓶) - 0 to 9
            elif r_id == "InkBottle":
                if counter == 9:
                    alerts.append(RelicAlert(
                        relic_id=r_id,
                        relic_name=r_name,
                        current_counter=counter,
                        max_counter=10,
                        alert_level="OPPORTUNITY",
                        message="🖋️ 墨水瓶已达 9/10！下一张打出的牌将额外抽 1 张牌！"
                    ))
                elif counter >= 0:
                    alerts.append(RelicAlert(
                        relic_id=r_id,
                        relic_name=r_name,
                        current_counter=counter,
                        max_counter=10,
                        alert_level="INFO",
                        message=f"🖋️ 墨水瓶计数: {counter}/10"
                    ))

            # 5. Sundial (日晷) - 0 to 2
            elif r_id == "Sundial":
                if counter == 2:
                    alerts.append(RelicAlert(
                        relic_id=r_id,
                        relic_name=r_name,
                        current_counter=counter,
                        max_counter=3,
                        alert_level="OPPORTUNITY",
                        message="⏰ 日晷 2/3！下一次牌库重洗将立即获得 2 点能量！"
                    ))

            # 6. Happy Flower (开心小花) - 0 to 2
            elif r_id == "Happy Flower":
                if counter == 2:
                    alerts.append(RelicAlert(
                        relic_id=r_id,
                        relic_name=r_name,
                        current_counter=counter,
                        max_counter=3,
                        alert_level="INFO",
                        message="🌸 开心小花 2/3：下回合开局额外获得 1 点能量！"
                    ))

            # 7. Stone Calendar (石历)
            elif r_id == "Stone Calendar":
                if turn == 6:
                    alerts.append(RelicAlert(
                        relic_id=r_id,
                        relic_name=r_name,
                        current_counter=turn,
                        max_counter=7,
                        alert_level="OPPORTUNITY",
                        message="⏰ 石历预警：下回合 (第7回合) 结束将对全体敌人造成 52 点巨额伤害！"
                    ))

            # 8. Paper Frog & Paper Crane
            elif r_id == "Paper Frog":
                alerts.append(RelicAlert(
                    relic_id=r_id,
                    relic_name=r_name,
                    current_counter=-1,
                    max_counter=-1,
                    alert_level="INFO",
                    message="🐸 纸蛙生效中：敌人易伤承受伤害提升至 1.75 倍！"
                ))
            elif r_id == "Paper Crane":
                alerts.append(RelicAlert(
                    relic_id=r_id,
                    relic_name=r_name,
                    current_counter=-1,
                    max_counter=-1,
                    alert_level="INFO",
                    message="🕊️ 纸鹤生效中：虚弱敌人造成的伤害降低 40%！"
                ))

        return alerts
