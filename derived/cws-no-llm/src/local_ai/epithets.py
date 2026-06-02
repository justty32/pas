"""
Phase 2: 外號生成系統
處理 nickname 任務。

nickname infos:
  world_info (dict), world_lore (str), avatar_info (dict — get_expanded_info)
返回: {"nickname": str, "reason": str, "thinking": str}
"""
import random


# 前綴詞庫（修煉體系、靈性形象）
_PREFIX_POOL = [
    "青玄", "玄陰", "金剛", "紫霄", "天罡", "地煞",
    "赤焰", "冰魄", "雷動", "風行", "逍遙", "無名",
    "孤鶴", "白骨", "鐵血", "奇峰", "玉虛", "太虛",
    "無極", "混沌", "烈陽", "幽冥", "九霄", "八荒",
]

# 主題元素詞庫（插在前綴與後綴之間）
_THEME_POOL = [
    "劍", "刀", "掌", "指", "拳",
    "霧", "雷", "火", "冰", "風",
    "雲", "山", "嶽", "淵", "月",
    "星", "佛", "魔", "道", "仙",
]

# 後綴身份詞庫
_SUFFIX_POOL = [
    "道人", "散人", "真人", "居士", "客", "子",
    "尊者", "老祖", "翁", "仙", "魔", "俠", "君",
]

# 稀有特殊外號（整體一詞，5% 機率出現）
_SPECIAL_POOL = [
    ("獨行俠",   "遊走四方，不附宗門，人稱獨行俠"),
    ("煉丹宗師", "精通丹道，名聞遐邇"),
    ("佈陣奇才", "布陣造詣精深，令人側目"),
    ("天劍無雙", "劍法超絕，江湖難尋敵手"),
    ("鐵面無私", "執法嚴明，恩怨分明"),
    ("鬼醫",     "醫術通玄，據傳可起死回生"),
    ("藏鋒客",   "深藏不露，實力難測"),
    ("無常使",   "行蹤飄忽，令人捉摸不定"),
]

# 境界關鍵字 → 前綴池縮窄（越高境界用越稀少的前綴）
_REALM_PREFIX = {
    "煉氣": _PREFIX_POOL[:8],
    "築基": _PREFIX_POOL[:14],
    "金丹": _PREFIX_POOL[:18],
    "元嬰": _PREFIX_POOL[:20],
    "化神": _PREFIX_POOL,
    "合體": _PREFIX_POOL,
    "渡劫": _PREFIX_POOL,
    "大乘": _PREFIX_POOL,
}


def _get_realm_prefix_pool(avatar_info: dict) -> list:
    if not isinstance(avatar_info, dict):
        return _PREFIX_POOL
    realm = str(avatar_info.get("realm", "") or avatar_info.get("stage", "") or "")
    for key, pool in _REALM_PREFIX.items():
        if key in realm:
            return pool
    return _PREFIX_POOL


def _gen_epithet(avatar_info: dict) -> tuple:
    # 5% 機率得到特殊外號
    if random.random() < 0.05:
        nick, reason = random.choice(_SPECIAL_POOL)
        return nick, reason

    prefix_pool = _get_realm_prefix_pool(avatar_info)
    prefix = random.choice(prefix_pool)
    suffix = random.choice(_SUFFIX_POOL)

    # 50% 帶主題字（如「青玄劍道人」），50% 僅前後（如「青玄道人」）
    if random.random() < 0.5:
        theme = random.choice(_THEME_POOL)
        nick   = f"{prefix}{theme}{suffix}"
        reason = f"因{prefix}之氣與{theme}道相合，江湖人稱{nick}。"
    else:
        nick   = f"{prefix}{suffix}"
        reason = f"以{prefix}之名行走江湖，人稱{nick}。"

    return nick, reason


def gen_nickname(infos: dict) -> dict:
    avatar_info = infos.get("avatar_info", {})
    nick, reason = _gen_epithet(avatar_info)
    return {"nickname": nick, "reason": reason, "thinking": ""}
