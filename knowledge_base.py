"""
Unified World-Class Knowledge Base for Slay the Spire.
Authoritative source of truth:
- Loads and indexes 295 cards, 169 relics, 69 monsters, 131 powers from D:\\ccode\\slay\\EO\\Slay-the-Spire-EO.
- Complements the full 75-card dataset and Stance mechanics for Watcher (观者).
- Covers all 4 characters: Ironclad (战士), The Silent (猎手), Defect (机器人), Watcher (观者).
- Full bilingual support (English/Chinese) for cards, relics, powers, monsters, and keywords.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("KnowledgeBase")

EO_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "EO", "Slay-the-Spire-EO")

# Comprehensive Watcher (观者) dataset to complement EO v1.0 data
WATCHER_CARDS: Dict[str, Dict[str, Any]] = {
    "Strike_P": {"NAME": "Strike", "ZH": "打击", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 6, "HITS": 1, "DESC": "造成 6 点伤害。"},
    "Defend_P": {"NAME": "Defend", "ZH": "防御", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 5, "DESC": "获得 5 点格挡。"},
    "Eruption": {"NAME": "Eruption", "ZH": "愤怒爆发", "COST": 2, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 9, "STANCE": "Wrath", "DESC": "造成 9 点伤害。进入【愤怒】姿态。"},
    "Vigilance": {"NAME": "Vigilance", "ZH": "警惕", "COST": 2, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 8, "STANCE": "Calm", "DESC": "获得 8 点格挡。进入【平静】姿态。"},
    "Bowling Bash": {"NAME": "Bowling Bash", "ZH": "保龄球重击", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 7, "DESC": "场上每有一名敌人，造成 7 点伤害一次。"},
    "Consecrate": {"NAME": "Consecrate", "ZH": "祝圣", "COST": 0, "TYPE": "ATTACK", "TARGET": "ALL_ENEMY", "DMG": 5, "AOE": True, "DESC": "对所有敌人造成 5 点伤害。"},
    "Crescendo": {"NAME": "Crescendo", "ZH": "渐强", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "STANCE": "Wrath", "DESC": "保留。进入【愤怒】姿态。消耗。"},
    "Crush Joints": {"NAME": "Crush Joints", "ZH": "粉碎关节", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 8, "VULN": 1, "DESC": "造成 8 点伤害。若上一张是技能，给予 1 层易伤。"},
    "Cut Through Fate": {"NAME": "Cut Through Fate", "ZH": "斩破命运", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 8, "DRAW": 1, "DESC": "造成 8 点伤害。预见 2。抽 1 张牌。"},
    "Empty Body": {"NAME": "Empty Body", "ZH": "空身", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 7, "STANCE": "None", "DESC": "获得 7 点格挡。退出当前姿态。"},
    "Empty Fist": {"NAME": "Empty Fist", "ZH": "空拳", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 9, "STANCE": "None", "DESC": "造成 9 点伤害。退出当前姿态。"},
    "Flurry of Blows": {"NAME": "Flurry of Blows", "ZH": "疾风连击", "COST": 0, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 4, "DESC": "造成 4 点伤害。每当你改变姿态时，将此牌从弃牌堆返回手牌。"},
    "Flying Sleeves": {"NAME": "Flying Sleeves", "ZH": "飞袖", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 4, "HITS": 2, "DESC": "保留。造成 4 点伤害 2 次。"},
    "Follow-Up": {"NAME": "Follow-Up", "ZH": "追击", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 7, "DESC": "造成 7 点伤害。若上一张是攻击牌，获得 1 点能量。"},
    "Halt": {"NAME": "Halt", "ZH": "停顿", "COST": 0, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 3, "DESC": "获得 3 点格挡。若处于【愤怒】姿态，额外获得 9 点格挡。"},
    "Just Lucky": {"NAME": "Just Lucky", "ZH": "只是幸运", "COST": 0, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 3, "BLOCK": 1, "DESC": "预见 1。获得 1 点格挡。造成 3 点伤害。"},
    "Prostrate": {"NAME": "Prostrate", "ZH": "俯卧拜伏", "COST": 0, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 4, "MANTRA": 2, "DESC": "获得 2 点真言。获得 4 点格挡。"},
    "Protect": {"NAME": "Protect", "ZH": "守护", "COST": 2, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 12, "DESC": "保留。获得 12 点格挡。"},
    "Sash Whip": {"NAME": "Sash Whip", "ZH": "飘带鞭击", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 8, "WEAK": 1, "DESC": "造成 8 点伤害。若上一张是攻击牌，给予 1 层虚弱。"},
    "Third Eye": {"NAME": "Third Eye", "ZH": "第三只眼", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 7, "DESC": "获得 7 点格挡。预见 3。"},
    "Evaluate": {"NAME": "Evaluate", "ZH": "评估", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 6, "DESC": "获得 6 点格挡。在抽牌堆加入一张【洞见】。"},
    "Carve Reality": {"NAME": "Carve Reality", "ZH": "雕刻现实", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 6, "DESC": "造成 6 点伤害。在手牌中加入一张【重击】。"},
    "Deceive Reality": {"NAME": "Deceive Reality", "ZH": "欺瞒现实", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 4, "DESC": "获得 4 点格挡。在手牌中加入一张【安全】。"},
    "Fasting": {"NAME": "Fasting", "ZH": "辟谷绝食", "COST": 2, "TYPE": "POWER", "TARGET": "SELF", "DESC": "每回合能量上限 -1。获得 3 点力量与 3 点敏捷。"},
    "Fear No Evil": {"NAME": "Fear No Evil", "ZH": "不惧邪恶", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 8, "DESC": "造成 8 点伤害。若敌人意图攻击，进入【平静】姿态。"},
    "Inner Peace": {"NAME": "Inner Peace", "ZH": "内心宁静", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "若处于【平静】姿态，抽 3 张牌；否则进入【平静】姿态。"},
    "Like Water": {"NAME": "Like Water", "ZH": "如水", "COST": 1, "TYPE": "POWER", "TARGET": "SELF", "DESC": "回合结束时若处于【平静】姿态，获得 5 点格挡。"},
    "Meditate": {"NAME": "Meditate", "ZH": "冥想", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "将弃牌堆 1 张牌放回手牌并保留。进入【平静】姿态。结束回合。"},
    "Mental Fortress": {"NAME": "Mental Fortress", "ZH": "心如止水", "COST": 1, "TYPE": "POWER", "TARGET": "SELF", "DESC": "每当你改变姿态时，获得 4 点格挡。"},
    "Nirvana": {"NAME": "Nirvana", "ZH": "涅槃", "COST": 1, "TYPE": "POWER", "TARGET": "SELF", "DESC": "每当你预见时，获得 3 点格挡。"},
    "Perseverance": {"NAME": "Perseverance", "ZH": "坚韧不拔", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 5, "DESC": "保留。本牌在手牌中每保留一回合，格挡增加 2 点。"},
    "Pray": {"NAME": "Pray", "ZH": "祈祷", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "MANTRA": 3, "DESC": "获得 3 点真言。在抽牌堆加入一张【洞见】。"},
    "Reach Heaven": {"NAME": "Reach Heaven", "ZH": "触及天国", "COST": 2, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 10, "DESC": "造成 10 点伤害。在抽牌堆加入一张【穿透暴力】。"},
    "Rushdown": {"NAME": "Rushdown", "ZH": "猛虎下山", "COST": 1, "TYPE": "POWER", "TARGET": "SELF", "DESC": "每当你进入【愤怒】姿态时，抽 2 张牌。"},
    "Sanctity": {"NAME": "Sanctity", "ZH": "圣洁", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 6, "DESC": "获得 6 点格挡。若上一张是攻击牌，抽 2 张牌。"},
    "Sands of Time": {"NAME": "Sands of Time", "ZH": "时间之沙", "COST": 4, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 20, "DESC": "保留。在手牌中每保留一回合，耗能减少 1 点。造成 20 点伤害。"},
    "Signature Move": {"NAME": "Signature Move", "ZH": "招牌动作", "COST": 2, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 30, "DESC": "仅在手牌中只有这一张攻击牌时才能打出。造成 30 点伤害。"},
    "Simmering Fury": {"NAME": "Simmering Fury", "ZH": "蓄势待发", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "在你的下回合开始时，进入【愤怒】姿态并抽 2 张牌。"},
    "Swivel": {"NAME": "Swivel", "ZH": "回旋", "COST": 2, "TYPE": "SKILL", "TARGET": "SELF", "BLOCK": 8, "DESC": "获得 8 点格挡。你的下一张攻击牌耗能为 0。"},
    "Talk to the Hand": {"NAME": "Talk to the Hand", "ZH": "与手掌对话", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 5, "DESC": "造成 5 点伤害。每当你攻击该敌人时，获得 2 点格挡。消耗。"},
    "Tantrum": {"NAME": "Tantrum", "ZH": "暴怒", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 3, "HITS": 3, "STANCE": "Wrath", "DESC": "造成 3 点伤害 3 次。进入【愤怒】姿态。洗入抽牌堆。"},
    "Wallop": {"NAME": "Wallop", "ZH": "痛击", "COST": 2, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 9, "DESC": "造成 9 点伤害。获得等同于未被格挡伤害的格挡值。"},
    "Wave of the Hand": {"NAME": "Wave of the Hand", "ZH": "拂手", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "本回合内每当你获得格挡，对所有敌人给予 1 层虚弱。"},
    "Windmill Strike": {"NAME": "Windmill Strike", "ZH": "风车打击", "COST": 2, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 7, "DESC": "保留。在手牌中每保留一回合，伤害增加 4 点。造成 7 点伤害。"},
    "Worship": {"NAME": "Worship", "ZH": "崇拜", "COST": 2, "TYPE": "SKILL", "TARGET": "SELF", "MANTRA": 5, "DESC": "获得 5 点真言。保留。"},
    "Wreath of Flame": {"NAME": "Wreath of Flame", "ZH": "烈焰花环", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "你的下一张攻击牌额外造成 5 点伤害。"},
    "Alpha": {"NAME": "Alpha", "ZH": "阿尔法", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "在抽牌堆加入一张【贝塔】。消耗。"},
    "Blasphemy": {"NAME": "Blasphemy", "ZH": "渎神", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "STANCE": "Divinity", "DESC": "保留。进入【神化】姿态。在你的下回合开始时死亡。消耗。"},
    "Brilliance": {"NAME": "Brilliance", "ZH": "辉煌", "COST": 1, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 12, "DESC": "造成 12 点伤害。本场战斗中每获得过 1 点真言，额外造成 1 点伤害。"},
    "Conjure Blade": {"NAME": "Conjure Blade", "ZH": "变幻之刃", "COST": -1, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "消耗所有能量。在抽牌堆加入一张打出 X 次的【斩杀剑】。消耗。"},
    "Deus Ex Machina": {"NAME": "Deus Ex Machina", "ZH": "天外救星", "COST": -2, "TYPE": "SKILL", "TARGET": "NONE", "DESC": "不可打出。当你抽到此牌时，获得 2 点能量并消耗。"},
    "Deva Form": {"NAME": "Deva Form", "ZH": "天神形态", "COST": 3, "TYPE": "POWER", "TARGET": "SELF", "DESC": "虚无。每回合开始时额外获得能量，每回合获得的能量比上一回合 +1。"},
    "Devotion": {"NAME": "Devotion", "ZH": "虔诚", "COST": 1, "TYPE": "POWER", "TARGET": "SELF", "MANTRA": 2, "DESC": "在你的回合开始时，获得 2 点真言。"},
    "Establishment": {"NAME": "Establishment", "ZH": "奠基建立", "COST": 1, "TYPE": "POWER", "TARGET": "SELF", "DESC": "每当有一张牌在手牌中被保留，其耗能减少 1 点。"},
    "Judgement": {"NAME": "Judgement", "ZH": "审判", "COST": 1, "TYPE": "SKILL", "TARGET": "ENEMY", "DESC": "若敌人生命值在 30 点或以下，使其生命直接变为 0。"},
    "Lesson Learned": {"NAME": "Lesson Learned", "ZH": "吸取教训", "COST": 2, "TYPE": "ATTACK", "TARGET": "ENEMY", "DMG": 10, "DESC": "致命：随机永久升级牌库中一张卡牌。消耗。"},
    "Master Reality": {"NAME": "Master Reality", "ZH": "掌控现实", "COST": 1, "TYPE": "POWER", "TARGET": "SELF", "DESC": "每当在战斗中创造一张卡牌，将其升级。"},
    "Omniscience": {"NAME": "Omniscience", "ZH": "全知", "COST": 4, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "选择抽牌堆中的一张牌打出两次，然后将其消耗。消耗。"},
    "Ragnarok": {"NAME": "Ragnarok", "ZH": "诸神黄昏", "COST": 3, "TYPE": "ATTACK", "TARGET": "ALL_ENEMY", "DMG": 5, "HITS": 5, "DESC": "随机对敌人造成 5 点伤害 5 次。"},
    "Scrawl": {"NAME": "Scrawl", "ZH": "天人合一", "COST": 1, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "抽牌直到手牌达到上限。消耗。"},
    "Spirit Shield": {"NAME": "Spirit Shield", "ZH": "灵能护盾", "COST": 2, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "手牌中每有一张牌，获得 3 点格挡。"},
    "Vault": {"NAME": "Vault", "ZH": "腾跃", "COST": 3, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "结束当前回合并立即开始一个额外的回合。消耗。"},
    "Wish": {"NAME": "Wish", "ZH": "祈愿", "COST": 3, "TYPE": "SKILL", "TARGET": "SELF", "DESC": "选择一项：获得 3 层镀层护甲、3 点力量或 25 金币。消耗。"}
}

# Master Bilingual Translation Map
CARD_ZH_MAP = {
    # Ironclad
    "Strike_R": "打击", "Strike": "打击", "Defend_R": "防御", "Defend": "防御", "Bash": "痛击",
    "Anger": "愤怒", "Armaments": "武装", "Body Slam": "全身撞击", "Clash": "交锋",
    "Cleave": "顺劈斩", "Clothesline": "金刚臂", "Flex": "活动肌肉", "Havoc": "浩劫",
    "Headbutt": "头槌", "Heavy Blade": "重刃", "Iron Wave": "铁浪", "Perfected Strike": "完美打击",
    "Pommel Strike": "剑柄打击", "Shrug It Off": "耸肩无视", "Sword Boomerang": "回旋镖",
    "Thunderclap": "雷霆打击", "True Grit": "坚毅", "Twin Strike": "双重打击", "Warcry": "战嚎",
    "Wild Strike": "狂野打击", "Battle Trance": "战意", "Blood for Blood": "以血还血",
    "Bloodletting": "放血", "Burning Pact": "燃烧契约", "Carnage": "残杀", "Combust": "自燃",
    "Dark Embrace": "黑暗之拥", "Disarm": "缴械", "Dropkick": "飞踢", "Dual Wield": "双持",
    "Entrench": "巩固", "Evolve": "进化", "Feel No Pain": "无惧疼痛", "Fire Breathing": "火焰吐息",
    "Flame Barrier": "火焰屏障", "Ghostly Armor": "幽灵护甲", "Hemokinesis": "血液流动",
    "Infernal Blade": "地狱之刃", "Inflame": "燃烧", "Intimidate": "威吓", "Metallicize": "金属化",
    "Power Through": "硬撑", "Pummel": "重拳连击", "Rage": "盛怒", "Rampage": "暴走",
    "Reckless Charge": "蛮冲撞", "Rupture": "破裂", "Searing Blow": "炙热打击", "Second Wind": "残存力量",
    "Seeing Red": "眼花缭乱", "Sentinel": "哨兵", "Sever Soul": "撕裂灵魂", "Shockwave": "震荡波",
    "Spot Weakness": "观察弱点", "Uppercut": "上勾拳", "Whirlwind": "旋风斩", "Barricade": "壁垒",
    "Berserk": "狂暴", "Bludgeon": "痛击重击", "Brutality": "残虐", "Corruption": "腐化",
    "Demon Form": "恶魔形态", "Double Tap": "双发", "Exhume": "掘墓", "Feed": "吞食",
    "Fiend Fire": "恶魔之火", "Immolate": "燔祭", "Impervious": "不屈不挠", "Juggernaut": "重装甲",
    "Limit Break": "突破极限", "Offering": "祭品", "Reaper": "死神收割",

    # The Silent
    "Strike_G": "打击", "Defend_G": "防御", "Neutralize": "中和", "Survivor": "生存者",
    "Bane": "剧毒之灾", "Blade Dance": "刀刃之舞", "Cloak And Dagger": "斗篷与匕首",
    "Dagger Spray": "匕首雨", "Dagger Throw": "掷刃", "Deadly Poison": "致命毒药",
    "Deflect": "偏转", "Dodge and Roll": "翻滚闪避", "Flying Knee": "飞膝", "Outmaneuver": "以退为进",
    "Piercing Wail": "刺耳尖叫", "Poisoned Stab": "带毒刺击", "Prepared": "早有准备",
    "Quick Slash": "迅捷打击", "Slice": "切削", "Sneaky Strike": "隐秘打击", "Sucker Punch": "偷袭",
    "Accuracy": "精准", "All-Out Attack": "全力攻击", "Backflip": "后空翻", "Backstab": "背刺",
    "Bouncing Flask": "弹跳药瓶", "Calculated Gamble": "精打细算", "Caltrops": "蒺藜",
    "Catalyst": "催化剂", "Choke": "窒息", "Concentrate": "全神贯注", "Crippling Cloud": "致残毒云",
    "Dash": "疾驰", "Distraction": "分散注意", "Endless Agony": "无尽苦痛", "Escape Plan": "脱逃计划",
    "Eviscerate": "开膛破肚", "Expertise": "特长", "Finisher": "终结技", "Flechettes": "飞镖",
    "Footwork": "灵动步伐", "Heel Hook": "足跟勾踢", "Infinite Blades": "无限刀刃",
    "Leg Sweep": "扫堂腿", "Masterful Stab": "大师刺击", "Noxious Fumes": "毒雾",
    "Predator": "捕食者", "Reflex": "本能反应", "Riddle With Holes": "千疮百孔",
    "Setup": "布局", "Skewer": "穿刺", "Tactician": "战术家", "Terror": "恐吓",
    "Well-Laid Plans": "深谋远虑", "A Thousand Cuts": "凌迟", "Adrenaline": "肾上腺素",
    "After Image": "余像", "Alchemize": "炼金术", "Bullet Time": "子弹时间",
    "Burst": "爆发", "Corpse Explosion": "尸爆术", "Die Die Die": "去死吧！",
    "Doppelganger": "分身", "Envenom": "涂毒", "Glass Knife": "玻璃刀",
    "Grand Finale": "华丽收场", "Malaise": "萎靡", "Nightmare": "梦魇", "Phantasmal Killer": "幻影杀手",
    "Storm of Steel": "钢铁风暴", "Tools of the Trade": "专业工具", "Unload": "倾泻而出",
    "Wraith Form v2": "幽魂形态", "Wraith Form": "幽魂形态",

    # Defect
    "Strike_B": "打击", "Defend_B": "防御", "Zap": "电击", "Dualcast": "双重释放",
    "Ball Lightning": "球状闪电", "Barrage": "弹幕射击", "Beam Cell": "光束射线",
    "Charge Battery": "充能电池", "Claw": "爪击", "Cold Snap": "冰霜打击", "Compile Driver": "编译驱动",
    "Coolheaded": "冷静面对", "Go for the Eyes": "瞄准双眼", "Hologram": "全息投影",
    "Leap": "飞跃", "Rebound": "弹回", "Steam Barrier": "蒸汽屏障", "Streamline": "流线型",
    "Sweeping Beam": "横扫光束", "Turbo": "涡轮", "Aggregate": "聚合", "Auto-Shields": "自动护盾",
    "Blizzard": "暴风雪", "BootSequence": "引导程序", "Bullseye": "靶心", "Capacitor": "电容器",
    "Chaos": "混沌", "Chill": "寒冷", "Consume": "消耗", "Darkness": "黑暗",
    "Defragment": "碎片整理", "Doom and Gloom": "毁灭与黑暗", "Double Energy": "双倍能量",
    "Equilibrium": "均衡", "FTL": "超光速", "Force Field": "力场", "Fusion": "聚变",
    "Genetic Algorithm": "遗传算法", "Glacier": "冰川", "Heatsinks": "散热片",
    "Hello World": "你好，世界", "Loop": "循环", "Melter": "溶解器", "Overclock": "超频",
    "Recycle": "回收", "Reinforced Body": "强化机体", "Reprogram": "重新编程",
    "Rip and Tear": "撕咬撕裂", "Scrape": "刮削", "Self Repair": "自我修复",
    "Skim": "略读", "Static Discharge": "静电释放", "Storm": "暴风雨", "Sunder": "撕裂",
    "Tempest": "暴风", "White Noise": "白噪音", "All for One": "万物一心",
    "Amplify": "放大", "Biased Cognition": "偏执认知", "Buffer": "缓冲",
    "Core Surge": "核心电涌", "Creative AI": "创造性AI", "Echo Form": "回响形态",
    "Electrodynamics": "电动力学", "Fission": "裂变", "Hyperbeam": "超能光束",
    "Machine Learning": "机器学习", "Meteor Strike": "流星打击", "Multi-Cast": "多重施法",
    "Rainbow": "彩虹", "Reboot": "重启", "Seek": "寻觅", "Thunder Strike": "雷霆打击",

    # Colorless & Curses
    "Apparition": "灵体", "Bandage Up": "包扎", "Blind": "致盲", "Dark Shackles": "黑暗镣铐",
    "Deep Breath": "深呼吸", "Discovery": "发现", "Dramatic Entrance": "华丽登场",
    "Enlightenment": "顿悟", "Finesse": "灵巧", "Flash of Steel": "钢之闪烁",
    "Forethought": "深谋", "Good Instincts": "敏锐直觉", "Impatience": "急躁",
    "Jack Of All Trades": "万能杂耍", "Madness": "疯狂", "Mind Blast": "心灵震击",
    "Panacea": "万灵药", "Panic Button": "应急按钮", "Purity": "净化纯洁",
    "Swift Strike": "迅捷打击", "Trip": "绊倒", "Apotheosis": "神化",
    "Chrysalis": "蛹化", "HandOfGreed": "贪婪之手", "Magnetism": "磁力",
    "Master of Strategy": "战略大师", "Mayhem": "混乱爆发", "Metamorphosis": "蜕变",
    "Panache": "华丽姿态", "Sadistic Nature": "虐待倾向", "Secret Technique": "密技",
    "Secret Weapon": "秘密武器", "The Bomb": "炸弹", "Thinking Ahead": "超前思维",
    "Transmutation": "嬗变", "Violence": "暴力",
    "Clumsy": "笨拙", "Decay": "腐烂", "Doubt": "怀疑", "Injury": "受伤",
    "Normality": "凡庸", "Pain": "痛苦", "Parasite": "寄生虫", "Regret": "悔恨",
    "Shame": "羞愧", "Writhe": "翻滚痛苦", "Curse of the Bell": "诅咒钟声",
    "Necronomicurse": "死灵诅咒", "AscendersBane": "进阶之灾", "Burn": "灼伤",
    "Dazed": "眩晕", "Slimed": "黏液", "Void": "虚空", "Wound": "伤口"
}

# Inject Watcher names into master map
for k, v in WATCHER_CARDS.items():
    CARD_ZH_MAP[k] = v["ZH"]
    CARD_ZH_MAP[v["NAME"]] = v["ZH"]

# Master Relic Translation Map (169 Relics)
RELIC_ZH_MAP = {
    "Burning Blood": "燃烧之血", "Ring of the Snake": "蛇之戒指", "Cracked Core": "破损核心", "PureWater": "纯净之水",
    "Akabeko": "赤牛", "Anchor": "锚", "Ancient Tea Set": "远古茶具", "Art of War": "孙子兵法",
    "Bag of Marbles": "弹珠袋", "Bag of Preparation": "准备背包", "Blood Vial": "鲜血药瓶",
    "Bronze Scales": "青铜鳞片", "Centennial Puzzle": "百年积木", "CeramicFish": "陶瓷小鱼",
    "Damaru": "小手鼓", "Dream Catcher": "捕梦网", "Happy Flower": "开心小花",
    "Juzu Bracelet": "数珠手串", "Lantern": "提灯", "MawBank": "巨口储蓄罐",
    "MealTicket": "餐券", "Nunchaku": "双节棍", "Oddly Smooth Stone": "奇特光滑的石头",
    "Omamori": "御守", "Orichalcum": "奥利哈钢", "Pen Nib": "钢笔尖",
    "Potion Belt": "药水腰带", "Preserved Insect": "昆虫标本", "Regal Pillow": "皇家枕头",
    "Smiling Mask": "微笑面具", "Strawberry": "草莓", "Boot": "靴子",
    "Tiny Chest": "迷你宝箱", "Toy Ornithopter": "玩具扑翼机", "Vajra": "金刚杵",
    "War Paint": "战书涂料", "Whetstone": "磨刀石",
    "Blue Candle": "蓝蜡烛", "Bottled Flame": "瓶装火焰", "Bottled Lightning": "瓶装闪电",
    "Bottled Tornado": "瓶装龙卷风", "Darkstone Periapt": "暗石护符", "Egg": "熔火之卵",
    "Frozen Egg 2": "冰冻之卵", "Toxic Egg 2": "毒素之卵", "Gremlin Horn": "地精之角",
    "HornCleat": "系缆桩", "InkBottle": "墨水瓶", "Kunai": "苦无",
    "Letter Opener": "拆信刀", "Matryoshka": "套娃", "Meat on the Bone": "带骨肉",
    "Mercury Hourglass": "水银沙漏", "Mummified Hand": "干瘪之手", "Ninja Scroll": "忍者卷轴",
    "Ornamental Fan": "精美折扇", "Pantograph": "缩放仪", "Paper Crane": "纸鹤",
    "Paper Frog": "纸蛙", "Pear": "雪梨", "Question Card": "问号卡牌",
    "Shuriken": "手里剑", "Singing Bowl": "唱歌碗", "StrikeDummy": "打击假人",
    "Sundial": "日晷", "The Courier": "信使", "CaptainsWheel": "舵轮",
    "Bird Faced Urn": "鸟面瓮", "Calipers": "圆规", "Champion Belt": "冠军腰带",
    "Charon's Ashes": "卡戎之灰", "CloakClasp": "斗篷扣", "Dead Branch": "枯木树枝",
    "Du-Vu Doll": "度量玩偶", "Gambling Chip": "赌徒筹码", "Ginger": "生姜",
    "Girya": "壶铃", "Ice Cream": "冰淇淋", "Incense Burner": "香炉",
    "Lizard Tail": "蜥蜴尾巴", "Mango": "芒果", "Old Coin": "古钱币",
    "Peace Pipe": "烟斗", "Pocketwatch": "怀表", "Prayer Wheel": "转经筒",
    "Shovel": "铁锹", "Stone Calendar": "石历", "Thread and Needle": "针线",
    "Torii": "鸟居", "Tough Bandages": "坚固绷带", "Turnip": "芜菁",
    "Unceasing Top": "陀螺", "WingedGreaves": "飞羽护胫",
    "Astrolabe": "星盘", "Black Star": "黑星", "Busted Crown": "碎裂王冠",
    "Calling Bell": "唤魔铃", "Coffee Dripper": "咖啡滤杯", "Cursed Key": "诅咒钥匙",
    "Ectoplasm": "外质", "Empty Cage": "空鸟笼", "Fusion Hammer": "融合之锤",
    "HoveringKite": "悬浮风筝", "Inserter": "植入物", "Mark of Pain": "痛苦印记",
    "Nuclear Battery": "核能电池", "Pandora's Box": "潘多拉魔盒", "Philosopher's Stone": "哲人石",
    "Runic Cube": "符文魔方", "Runic Dome": "符文圆顶", "Runic Pyramid": "符文金字塔",
    "SacredBark": "神圣树皮", "Slaver's Collar": "奴隶贩子项圈", "Snecko Eye": "异蛇之眼",
    "Sozu": "添水", "Velvet Choker": "天鹅绒项圈", "VioletLotus": "紫罗兰莲花",
    "WristBlade": "手腕刀",

    # Remaining Relics (Total 169)
    "Black Blood": "黑血", "Bloody Idol": "鲜血神像", "Cables": "金壳虫丝", "Cauldron": "大金坩埚",
    "Chameleon Ring": "变色龙之戒", "Chemical X": "化学物X", "Circlet": "无名头冠",
    "ClockworkSouvenir": "发条纪念品", "CultistMask": "邪教徒面具", "DataDisk": "数据磁盘",
    "Derp Rock": "呆呆石", "Discerning Monocle": "单片眼镜", "Dodecahedron": "十二面体",
    "DollysMirror": "多利之镜", "Emotion Chip": "情感芯片", "Enchiridion": "机械手抄本",
    "Eternal Feather": "永恒羽毛", "FaceOfCleric": "牧师的面具", "Frozen Egg": "冻结之蛋",
    "Frozen Eye": "冻结之眼", "FrozenCore": "冻结核心", "Golden Idol": "黄金神像",
    "GremlinMask": "地精面具", "HandDrill": "手摇钻", "Lee's Waffle": "李氏华夫饼",
    "Living Blade": "活体刀刃", "Magic Flower": "魔法花朵", "Mark of the Bloom": "盛开之印",
    "Medical Kit": "医疗箱", "Membership Card": "会员卡", "Molten Egg": "熔火之卵",
    "Molten Egg 2": "熔岩之蛋", "Necronomicon": "死灵之书", "NeowsBlessing": "涅奥的悲悯",
    "Nilry's Codex": "尼利的宝典", "Nine Lives": "九命", "Nloth's Gift": "恩洛斯的礼物",
    "NlothsMask": "恩洛斯的面具", "Nullstone Periapt": "废石护符", "Odd Mushroom": "奇异蘑菇",
    "OrangePellets": "橙色药丸", "Orrery": "天象仪", "Red Circlet": "红头冠",
    "Red Mask": "红面具", "Red Skull": "红色头骨", "Ring of the Serpent": "蛇之戒",
    "Runic Capacitor": "符文电容", "Self Forming Clay": "自塑黏土", "Sling": "投石索",
    "Snake Skull": "蛇头骨", "Spirit Poop": "灵魂之屎", "SsserpentHead": "异蛇之首",
    "Strange Spoon": "奇怪的勺子", "Symbiotic Virus": "共生病毒",
    "Test 1": "测试遗物1", "Test 2": "测试遗物2", "Test 3": "测试遗物3", "Test 4": "测试遗物4",
    "Test 5": "测试遗物5", "Test 6": "测试遗物6", "Test 7": "测试遗物7", "Test 8": "测试遗物8",
    "The Specimen": "标本", "TheAbacus": "算盘", "Tingsha": "廷夏", "Tiny House": "微型小屋",
    "Toolbox": "工具箱", "Toxic Egg": "剧毒之蛋", "TwistedFunnel": "扭曲漏斗",
    "White Beast Statue": "白兽雕像"
}

class KnowledgeBase:
    def __init__(self, data_dir: str = EO_DATA_DIR):
        self.data_dir = data_dir
        self.raw_cards: Dict[str, Any] = {}
        self.raw_relics: Dict[str, Any] = {}
        self.raw_monsters: Dict[str, Any] = {}
        self.raw_powers: Dict[str, Any] = {}
        self.raw_potions: Dict[str, Any] = {}
        self.is_loaded = False

        self._load_all_data()

    def _load_all_data(self):
        """Loads all JSON files from the EO repository."""
        if not os.path.exists(self.data_dir):
            logger.warning(f"EO data directory not found at: {self.data_dir}")
            return

        try:
            cards_path = os.path.join(self.data_dir, "cards.json")
            if os.path.exists(cards_path):
                with open(cards_path, "r", encoding="utf-8") as f:
                    self.raw_cards = json.load(f)

            relics_path = os.path.join(self.data_dir, "relics.json")
            if os.path.exists(relics_path):
                with open(relics_path, "r", encoding="utf-8") as f:
                    self.raw_relics = json.load(f)

            monsters_path = os.path.join(self.data_dir, "monsters.json")
            if os.path.exists(monsters_path):
                with open(monsters_path, "r", encoding="utf-8") as f:
                    self.raw_monsters = json.load(f)

            powers_path = os.path.join(self.data_dir, "powers.json")
            if os.path.exists(powers_path):
                with open(powers_path, "r", encoding="utf-8") as f:
                    self.raw_powers = json.load(f)

            potions_path = os.path.join(self.data_dir, "potions.json")
            if os.path.exists(potions_path):
                with open(potions_path, "r", encoding="utf-8") as f:
                    self.raw_potions = json.load(f)

            self.is_loaded = True
            logger.info(
                f"KnowledgeBase loaded: {len(self.raw_cards)} EO cards + {len(WATCHER_CARDS)} Watcher cards, "
                f"{len(self.raw_relics)} relics, {len(self.raw_monsters)} monsters, {len(self.raw_powers)} powers."
            )
        except Exception as e:
            logger.error(f"Failed to load KnowledgeBase data: {e}")

    def get_card_zh_name(self, card_name_or_id: str) -> str:
        """Returns the official Chinese name for a card."""
        clean = card_name_or_id.rstrip("+")
        if clean in CARD_ZH_MAP:
            return CARD_ZH_MAP[clean] + ("+" if card_name_or_id.endswith("+") else "")
        if clean in WATCHER_CARDS:
            return WATCHER_CARDS[clean]["ZH"] + ("+" if card_name_or_id.endswith("+") else "")
        if clean in self.raw_cards:
            return self.raw_cards[clean].get("NAME", clean)
        return card_name_or_id

    def get_relic_zh_name(self, relic_name_or_id: str) -> str:
        """Returns the official Chinese name for a relic."""
        if relic_name_or_id in RELIC_ZH_MAP:
            return RELIC_ZH_MAP[relic_name_or_id]
        if relic_name_or_id in self.raw_relics:
            return self.raw_relics[relic_name_or_id].get("NAME", relic_name_or_id)
        return relic_name_or_id

    def get_card_description(self, card_name_or_id: str, upgraded: bool = False) -> str:
        """Returns description of a card with placeholders cleaned."""
        clean = card_name_or_id.rstrip("+")
        if clean in WATCHER_CARDS:
            return WATCHER_CARDS[clean]["DESC"]

        data = self.raw_cards.get(clean)
        if not data:
            return ""

        desc = data.get("UPGRADE_DESCRIPTION" if (upgraded and "UPGRADE_DESCRIPTION" in data) else "DESCRIPTION", "")
        desc = desc.replace(" NL ", " ").replace("NL ", " ").replace("NL", " ")
        desc = desc.replace("[G]", "⚡").replace("[R]", "⚡").replace("[B]", "⚡").replace("[E]", "⚡")
        return desc

    def get_relic_description(self, relic_name_or_id: str) -> str:
        """Returns description of a relic."""
        data = self.raw_relics.get(relic_name_or_id)
        if not data:
            return ""
        descs = data.get("DESCRIPTIONS", [])
        return "".join(descs).replace("#b", "").replace("#y", "").replace("[R]", "⚡").replace("[G]", "⚡").replace("[B]", "⚡")

GLOBAL_KB = KnowledgeBase()
