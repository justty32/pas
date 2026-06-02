"""
Phase 1: long_term_objective 目標生成器

根據 avatar_info 中的線索（宗門、境界、近期大事件）
選擇最合適的目標模板，附加角色名稱讓文字更自然。
"""
import random

# ── 目標模板池（依情境分類）────────────────────────────────────────────────

_CULTIVATION_GOALS = [
    "突破境界，精進修為，登臨修仙之巔",
    "磨礪功法，蓄積靈力，等待突破時機",
    "苦心修煉，厚積薄發，一朝飛升成仙",
    "克服瓶頸，突破現有境界，再登新高",
]

_SECT_GOALS = [
    "忠心效力宗門，晉升宗門地位",
    "修煉精進，成為宗門倚重的強者",
    "為宗門立下功勳，提升自身影響力",
    "與門中同道切磋共進，共謀宗門壯大",
]

_WANDERER_GOALS = [
    "遊歷四方，增長見識，尋訪奇人異事",
    "廣結善緣，積累人脈，以備不時之需",
    "尋訪機緣，或入名門，或立一派",
    "拜訪各方高人，求得修煉機緣",
]

_WEALTH_GOALS = [
    "積累靈石，廣置資財，充實修煉資本",
    "開源節流，積少成多，為突破打好基礎",
]

_REVENGE_GOALS = [
    "臥薪嚐膽，積蓄實力，終有一日報仇雪恨",
    "提升境界，剷除宿敵，方得安心修煉",
]

_WAR_GOALS = [
    "協助宗門打贏戰事，護衛門中同道",
    "在戰火中磨礪自身，以戰促修",
]

_GENERIC_GOALS = [
    "修煉精進，掌控自身命運",
    "廣積善緣，成就一番事業",
    "尋訪機緣，突破現有桎梏",
    "歷盡滄桑，以道心照見萬物",
]


def _extract_hints(avatar_info: dict) -> dict:
    """
    從 avatar_info（可能是 dict 或含中文 key 的 dict）
    提取 has_sect, has_enemy, at_war, magic_stone_low 等布林線索。
    """
    # avatar_info 的 key 可能是翻譯後的中文或英文，用 lower 做模糊匹配
    flat = {}
    for k, v in avatar_info.items():
        flat[str(k).lower()] = v

    # 是否有宗門
    sect_val = str(flat.get("sect", flat.get("宗門", "")))
    has_sect = bool(sect_val) and all(
        kw not in sect_val for kw in ("散修", "None", "Rogue", "none", "rogue")
    )

    # 近期大事件（是否有仇恨/戰爭跡象）
    major_events = flat.get("major events", flat.get("大事件", []))
    if isinstance(major_events, list):
        event_str = " ".join(str(e).lower() for e in major_events)
    else:
        event_str = str(major_events).lower()
    has_enemy = any(kw in event_str for kw in ("war", "enemy", "kill", "死", "殺", "仇", "敵", "戰"))
    at_war = "war" in event_str or "宣戰" in event_str

    # 靈石是否不足（難以判斷絕對數字，只用比較低的標準）
    magic_stone = int(flat.get("magic stone", flat.get("靈石", 0)) or 0)
    magic_stone_low = magic_stone < 100

    return {
        "has_sect": has_sect,
        "has_enemy": has_enemy,
        "at_war": at_war,
        "magic_stone_low": magic_stone_low,
    }


def gen_long_term_objective(infos: dict) -> dict:
    """
    Phase 1 long_term_objective 模板生成器。
    消費端只需要 {"long_term_objective": str}。
    """
    avatar_info = infos.get("avatar_info", {})
    hints = _extract_hints(avatar_info) if isinstance(avatar_info, dict) else {}

    has_sect       = hints.get("has_sect", False)
    has_enemy      = hints.get("has_enemy", False)
    at_war         = hints.get("at_war", False)
    magic_stone_low = hints.get("magic_stone_low", False)

    # 依優先級選擇目標池（可疊加）
    pool: list[str] = []

    if at_war:
        pool += _WAR_GOALS
    if has_enemy:
        pool += _REVENGE_GOALS
    if has_sect:
        pool += _SECT_GOALS
        pool += _CULTIVATION_GOALS
    if magic_stone_low:
        pool += _WEALTH_GOALS
    if not has_sect:
        pool += _WANDERER_GOALS

    # 最後補上修煉目標（永遠適用）
    pool += _CULTIVATION_GOALS

    if not pool:
        pool = _GENERIC_GOALS

    return {"long_term_objective": random.choice(pool)}
