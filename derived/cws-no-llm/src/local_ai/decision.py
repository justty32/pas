"""
Phase 1: action_decision 效用 AI（Utility AI）

評分公式：
  score(action) = BASE_SCORES[action]
                × context_modifier(avatar_ai_context)
                × random.uniform(0.75, 1.25)  # 擾動 ε

選擇方式：softmax 機率取樣（溫度=1.0），讓高分動作更常被選中但不完全固定。
"""
import json
import math
import random

# ── 基礎效用分（PascalCase class name → float）────────────────────────────────
_BASE_SCORES: dict[str, float] = {
    # 修煉系（最高優先）
    "Respire":            10.0,
    "Meditate":            9.0,
    "Temper":              8.0,
    "Refine":              7.5,
    "Retreat":             6.0,
    # 雙修/養器
    "DualCultivation":     6.0,
    "NurtureWeapon":       5.0,
    # 社交（有收益的優先）
    "Impart":              5.5,
    "SectMission":         5.0,
    "SwearBrotherhood":    4.0,
    "Conversation":        4.0,
    "Talk":                4.0,
    "Gift":                3.5,
    "Spar":                3.5,
    "Confess":             2.5,
    # 恢復
    "SelfHeal":            4.0,
    "Rest":                3.0,
    "Escape":              2.5,
    # 生產
    "Mine":                3.5,
    "Harvest":             3.5,
    "Hunt":                3.5,
    "Plant":               3.0,
    "Cast":                3.0,
    "Buy":                 3.0,
    "Sell":                2.5,
    # 治理
    "Govern":              3.0,
    "HelpPeople":          3.0,
    "Educate":             3.0,
    "Play":                2.0,
    # 移動（低基礎，避免 NPC 不斷遊蕩）
    "MoveToRegion":        2.0,
    "MoveToAvatar":        2.0,
    "Move":                1.5,
    "MoveToDirection":     1.5,
    "MoveAwayFromAvatar":  1.0,
    "MoveAwayFromRegion":  1.0,
    # 戰鬥
    "Attack":              3.0,
    "Assassinate":         2.0,
    # 暗面（邪惡陣營）
    "EatMortals":          3.0,
    "DevourPeople":        3.0,
    "PlunderPeople":       2.0,
    "CatchAction":         2.0,
}

_DEFAULT_SCORE = 2.0
_SOFTMAX_TEMP = 1.2   # 溫度越高 → 選擇越均勻；越低 → 越集中於高分


def _apply_context_modifiers(scores: dict[str, float], ai_ctx: dict) -> dict[str, float]:
    """根據 avatar_ai_context 的 decision_hints 與狀態調整效用分。"""
    decision_hints = ai_ctx.get("decision_hints", {})
    should_prioritize_safety   = bool(decision_hints.get("should_prioritize_safety", False))
    should_prioritize_sect_duty = bool(decision_hints.get("should_prioritize_sect_duty", False))

    self_profile = ai_ctx.get("self_profile", {})
    hp = self_profile.get("hp", {})
    hp_cur = float(hp.get("cur", 1) or 1)
    hp_max = float(hp.get("max", 1) or 1)
    hp_ratio = hp_cur / max(1.0, hp_max)

    sect_ctx = ai_ctx.get("sect_context", {})
    has_sect = bool(sect_ctx.get("has_sect", False))

    result: dict[str, float] = {}
    for name, base in scores.items():
        s = base

        # ─ 安全優先：HP < 50% 或 decision_hints 觸發 ─
        if should_prioritize_safety or hp_ratio < 0.5:
            hp_mult = max(0.3, 1.0 - (0.5 - hp_ratio) * 2)  # HP 越低乘越大
            if name in ("Rest", "SelfHeal"):
                s *= (2.0 + (0.5 - min(0.5, hp_ratio)) * 4)
            elif name in ("Escape",):
                s *= 2.0
            elif name in ("Attack", "Spar", "Assassinate"):
                s *= max(0.2, hp_mult * 0.5)

        # ─ 宗門戰爭 ─
        if should_prioritize_sect_duty:
            if name == "SectMission":
                s *= 2.5
            elif name == "Attack":
                s *= 1.5

        # ─ 宗門成員：宗門任務小加成 ─
        if has_sect and name == "SectMission":
            s *= 1.3

        # ─ 隨機擾動 ε（±25%）─
        s *= random.uniform(0.75, 1.25)
        result[name] = s

    return result


def _softmax_select(scores: dict[str, float], temperature: float = _SOFTMAX_TEMP) -> str:
    """
    使用 softmax 機率取樣選出動作名稱。
    高分動作更常被選中，但保留一定隨機性（避免完全同質化）。
    """
    max_s = max(scores.values())
    exps = {k: math.exp((v - max_s) / temperature) for k, v in scores.items()}
    total = sum(exps.values())
    probs = sorted(exps.items(), key=lambda x: -x[1])

    r = random.random()
    cumul = 0.0
    for name, exp_val in probs:
        cumul += exp_val / total
        if r <= cumul:
            return name
    return probs[0][0]  # fallback


def _pick_params(action_info: dict) -> dict:
    """從 param_options 隨機取一個合法 params；若無則返回空 dict。"""
    param_options = action_info.get("param_options")
    if param_options and isinstance(param_options, list) and len(param_options) > 0:
        return dict(random.choice(param_options))
    return {}


def decide_action(infos: dict) -> dict:
    """
    Phase 1 action_decision 入口。
    返回格式與 LLM 版本一致（消費端：ai.py:84）。
    """
    avatar_name = infos.get("avatar_name", "unknown")
    ai_ctx = infos.get("avatar_ai_context", {})

    # 解析可用動作（general_action_infos 可能是 JSON string 或 dict）
    available: dict = {}
    raw = infos.get("general_action_infos", "")
    if isinstance(raw, str) and raw:
        try:
            available = json.loads(raw)
        except json.JSONDecodeError:
            pass
    elif isinstance(raw, dict):
        available = raw

    if not available:
        return {
            avatar_name: {
                "action_name_params_pairs": [["Rest", {}]],
                "avatar_thinking": "[local_ai] 靜待時機",
                "short_term_objective": "休養生息",
                "current_emotion": "emotion_calm",
            }
        }

    # 計算效用分（僅評分在 available 內的動作）
    raw_scores = {name: _BASE_SCORES.get(name, _DEFAULT_SCORE) for name in available}
    scored = _apply_context_modifiers(raw_scores, ai_ctx)

    # softmax 取樣選出動作
    chosen = _softmax_select(scored)
    params = _pick_params(available.get(chosen, {}))

    return {
        avatar_name: {
            "action_name_params_pairs": [[chosen, params]],
            "avatar_thinking": "[local_ai] 效用評估後選擇行動",
            "short_term_objective": "",
            "current_emotion": "emotion_calm",
        }
    }
