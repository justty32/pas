"""
Phase 1: relation_delta 公式引擎

根據互動事件文字推斷互動類型，
搭配雙方現有好感度計算 delta（-6 ~ +6 範圍）。
"""
import random

# ── 各互動類型的 delta 基礎範圍 ───────────────────────────────────────────────
# 每個 tuple 是 (min, max)，以整數表示
_INTERACTION_BASE: dict[str, tuple[int, int]] = {
    "gift":               (2,  5),
    "dual_cultivation":   (3,  5),
    "swear_brotherhood":  (3,  5),
    "impart":             (2,  5),
    "confess":            (0,  4),
    "play":               (1,  3),
    "conversation":       (-1, 3),
    "talk":               (-1, 3),
    "spar":               (-2, 3),
    "occupy":             (-3, -1),
    "drive_away":         (-3, -1),
    "attack":             (-4, -1),
}

_DEFAULT_BASE: tuple[int, int] = (-1, 2)

# 全域上下限（若 infos 沒帶，則使用預設）
_FALLBACK_MIN = -6
_FALLBACK_MAX = 6


def _infer_interaction_type(event_text: str) -> str:
    """
    從 event_text 推斷互動類型（模糊關鍵字匹配）。
    優先匹配更具體的類型，最後 fallback 到 conversation。
    """
    t = event_text.lower()

    if any(k in t for k in ("贈", "gift", "送禮", "送")):
        return "gift"
    if any(k in t for k in ("雙修", "dual cultivation", "dual_cultivation")):
        return "dual_cultivation"
    if any(k in t for k in ("結義", "sworn sibling", "sworn_sibling", "拜把")):
        return "swear_brotherhood"
    if any(k in t for k in ("傳授", "impart", "教導", "授業")):
        return "impart"
    if any(k in t for k in ("告白", "confess", "表白")):
        return "confess"
    if any(k in t for k in ("切磋", "spar", "比武", "比試")):
        return "spar"
    if any(k in t for k in ("攻擊", "attack", "殺", "擊", "傷")):
        return "attack"
    if any(k in t for k in ("驅逐", "drive away", "佔領", "occupy")):
        return "drive_away"
    if any(k in t for k in ("遊玩", "play", "玩耍")):
        return "play"
    if any(k in t for k in ("對話", "conversation", "話", "交談")):
        return "talk"
    return "conversation"


def calc_relation_delta(infos: dict) -> dict:
    """
    Phase 1 relation_delta 公式計算。
    消費端：relation_delta_service.py:79（期望 delta_a_to_b, delta_b_to_a: int）。
    """
    # 取配置的上下限
    try:
        min_delta = int(infos.get("min_delta", _FALLBACK_MIN))
        max_delta = int(infos.get("max_delta", _FALLBACK_MAX))
    except (TypeError, ValueError):
        min_delta, max_delta = _FALLBACK_MIN, _FALLBACK_MAX

    event_text = str(infos.get("event_text", ""))
    interaction_type = _infer_interaction_type(event_text)
    base_min, base_max = _INTERACTION_BASE.get(interaction_type, _DEFAULT_BASE)

    # 讀取現有好感度（用來偏移方向）
    try:
        fr_a_to_b = float(infos.get("avatar_a_to_b_friendliness", 0) or 0)
        fr_b_to_a = float(infos.get("avatar_b_to_a_friendliness", 0) or 0)
    except (TypeError, ValueError):
        fr_a_to_b = fr_b_to_a = 0.0

    def _single_delta(current_fr: float) -> int:
        base = random.randint(base_min, base_max)
        # 好感度高（>60）→ 負值 delta 對正向互動不出現；好感度低（<-40）→ 反之
        if current_fr > 60 and base < 0 and interaction_type in (
            "conversation", "talk", "spar", "play"
        ):
            base = 0
        elif current_fr < -40 and base > 0 and interaction_type in (
            "conversation", "talk"
        ):
            base = max(0, base - 1)
        return max(min_delta, min(max_delta, base))

    return {
        "delta_a_to_b": _single_delta(fr_a_to_b),
        "delta_b_to_a": _single_delta(fr_b_to_a),
    }
