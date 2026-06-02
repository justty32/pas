"""
Phase 3: 宗門 AI 系統
處理 sect_decider 和 sect_thinker 任務。

sect_decider infos:
  sect_name (str), world_info (str JSON), world_lore (str),
  decision_context_info (str JSON), decision_interval_years (int),
  recruit_cost (int), support_amount (int)

sect_thinker infos:
  sect_name (str), world_info (str JSON), world_lore (str),
  current_phenomenon_info (str), decision_context_info (str JSON),
  decision_summary (str)

decision_context_info 內部結構（已由 build_sect_decision_context 序列化）:
  economy.treasury_pressure: "critical" | "tight" | "stable" | "ample"
  self_assessment.war_readiness: "stable" | "stretched"
  self_assessment.war_weariness: int
  self_assessment.can_afford_recruit_count: int
  self_assessment.can_afford_support_count: int
  diplomacy_targets: [{other_sect_id, other_sect_name, status, power_ratio, ...}]
  active_wars: [{other_sect_id, power_ratio, war_months, ...}]
  recruitment_candidates: [{avatar_id, alignment_recruitable, race_recruitable, technique_grade_rank, ...}]
  member_candidates: [{avatar_id, is_rule_breaker, status_score, magic_stone, ...}]
"""
import json
import random


def _parse_context(infos: dict) -> dict:
    """解析 decision_context_info（可能是 JSON 字串或已 dict）。"""
    raw = infos.get("decision_context_info", "")
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# sect_decider
# ═══════════════════════════════════════════════════════════════════════════════

def _decide(infos: dict) -> dict:
    ctx = _parse_context(infos)

    economy        = ctx.get("economy", {})
    self_assess    = ctx.get("self_assessment", {})
    diplomacy      = ctx.get("diplomacy_targets", [])
    active_wars    = ctx.get("active_wars", [])
    recruit_cands  = ctx.get("recruitment_candidates", [])
    member_cands   = ctx.get("member_candidates", [])

    treasury  = str(economy.get("treasury_pressure", "tight"))
    war_weary = int(self_assess.get("war_weariness", 0) or 0)
    readiness = str(self_assess.get("war_readiness", "stable"))
    afford_recruit = int(self_assess.get("can_afford_recruit_count", 0) or 0)
    afford_support = int(self_assess.get("can_afford_support_count", 0) or 0)

    # ── 外交：求和 / 宣戰 ────────────────────────────────────────────────────

    declare_war_ids: list = []
    seek_peace_ids: list = []

    if active_wars:
        # 在戰時若疲戰、資源緊或邊境壓力大 → 求和（優先對 power_ratio 最低的對象）
        should_seek_peace = (
            war_weary >= 3
            or readiness == "stretched"
            or treasury in ("critical", "tight")
        )
        if should_seek_peace:
            weakest_war = min(active_wars, key=lambda w: float(w.get("power_ratio", 1.0)))
            seek_peace_ids.append(int(weakest_war["other_sect_id"]))
    else:
        # 不在戰時：若資源充裕 + 有強壓優勢 + 關係極差 → 低機率宣戰
        if treasury in ("stable", "ample") and readiness == "stable":
            targets = [
                t for t in diplomacy
                if t.get("status") != "war"
                and float(t.get("power_ratio", 0.0)) > 1.3
                and int(t.get("relation_value", 0)) <= -50
            ]
            if targets and random.random() < 0.3:
                best = max(targets, key=lambda t: float(t.get("power_ratio", 1.0)))
                declare_war_ids.append(int(best["other_sect_id"]))

    # ── 招募 ─────────────────────────────────────────────────────────────────

    recruit_ids: list = []
    if treasury in ("stable", "ample") and afford_recruit > 0:
        eligible = [
            c for c in recruit_cands
            if c.get("alignment_recruitable", False)
            and c.get("race_recruitable", True)
        ]
        # 品質優先：technique_grade_rank 高者優先
        eligible.sort(key=lambda c: -int(c.get("technique_grade_rank", 0) or 0))
        n = min(afford_recruit, 2)
        recruit_ids = [str(c["avatar_id"]) for c in eligible[:n]]

    # ── 驅逐（違規者）──────────────────────────────────────────────────────────

    expel_ids = [
        str(m["avatar_id"])
        for m in member_cands
        if m.get("is_rule_breaker", False)
    ]

    # ── 獎勵（績效前 2 名，非違規者）──────────────────────────────────────────

    non_breakers = [m for m in member_cands if not m.get("is_rule_breaker", False)]
    reward_ids = [str(m["avatar_id"]) for m in non_breakers[:2]]

    # ── 扶持（靈石不足者，優先度：magic_stone 低）─────────────────────────────

    support_ids: list = []
    if afford_support > 0:
        needy = sorted(non_breakers, key=lambda m: int(m.get("magic_stone", 0) or 0))
        support_ids = [str(m["avatar_id"]) for m in needy[:min(afford_support, 3)]]

    # ── 思考文字 ──────────────────────────────────────────────────────────────

    sect_name = str(infos.get("sect_name", "本宗"))
    thinking = _build_decider_thinking(
        sect_name, treasury, bool(active_wars),
        len(recruit_ids), len(expel_ids), len(reward_ids), len(support_ids),
    )

    return {
        "declare_war_target_ids": declare_war_ids,
        "seek_peace_target_ids":  seek_peace_ids,
        "recruit_avatar_ids":     recruit_ids,
        "expel_avatar_ids":       expel_ids,
        "reward_avatar_ids":      reward_ids,
        "support_avatar_ids":     support_ids,
        "thinking":               thinking,
    }


def _build_decider_thinking(
    sect_name: str, treasury: str, in_war: bool,
    recruit_n: int, expel_n: int, reward_n: int, support_n: int,
) -> str:
    parts = []
    if in_war:
        parts.append("宗門身陷戰局，以穩定為先")
    elif treasury in ("stable", "ample"):
        parts.append("宗門財力充盈，適時擴張")
    else:
        parts.append("宗門資源吃緊，守成為主")

    if recruit_n:
        parts.append(f"招募{recruit_n}名散修入門")
    if expel_n:
        parts.append(f"清除{expel_n}名違規門人")
    if reward_n:
        parts.append(f"嘉獎{reward_n}名優秀弟子")
    if support_n:
        parts.append(f"扶持{support_n}名弟子修行")

    return "，".join(parts) + "。"


def gen_sect_decider(infos: dict) -> dict:
    return _decide(infos)


# ═══════════════════════════════════════════════════════════════════════════════
# sect_thinker
# ═══════════════════════════════════════════════════════════════════════════════

# 宗門年度思考文字模板（每條長度均 ≥ 30 字，SectThinker._normalize 要求最低 30）
_THINKING_TEMPLATES = [
    "{sect}已確立下一輪方針：{strategy}，立德守規，以待天時。",
    "{sect}國力{econ}，當{strategy}，不可輕舉妄動。",
    "前事不忘，後事之師。{sect}當以過往為鑑，砥礪前行，不失根本。",
    "{sect}弟子{members}，下一輪以{strategy}為要務，穩中求勝。",
    "修仙一道，貴在積累。{sect}守規納才，蓄勢待發，靜候機緣。",
    "{sect}審時度勢，{war_status}，接下來以{strategy}為重心。",
    "山不在高，有仙則名。{sect}廣積善緣，以{strategy}為本，徐圖大業。",
    "{sect}思量得失：{war_status}，財力{econ}，當{strategy}，方為長久之計。",
]

_ECON_TEXT = {
    "critical": "危殆",
    "tight":    "緊拮",
    "stable":   "穩定",
    "ample":    "充裕",
}

_STRATEGY_TEXT = {
    "critical": "休養生息、量入為出",
    "tight":    "節儉為本、穩中求進",
    "stable":   "穩步擴張、廣納人才",
    "ample":    "積極進取、廣招賢才",
}

_WAR_TEXT = {
    True:  "目前宗門深陷戰局",
    False: "當前天下尚稱太平",
}

_MEMBER_TEXT = [
    "人才凋零",        # alive_count == 0
    "人手不足",        # 1-3
    "已有一定規模",    # 4-6
    "人才濟濟",        # 7+
]


def _build_thinking(infos: dict) -> str:
    ctx = _parse_context(infos)
    sect_name = str(infos.get("sect_name", "本宗"))

    economy     = ctx.get("economy", {})
    self_assess = ctx.get("self_assessment", {})
    active_wars = ctx.get("active_wars", [])

    treasury     = str(economy.get("treasury_pressure", "tight"))
    alive_count  = int(self_assess.get("alive_member_count", 0) or 0)
    in_war       = bool(active_wars)

    econ     = _ECON_TEXT.get(treasury, "正常")
    strategy = _STRATEGY_TEXT.get(treasury, "穩健前行")
    war_str  = _WAR_TEXT[in_war]

    if alive_count == 0:
        members = _MEMBER_TEXT[0]
    elif alive_count <= 3:
        members = _MEMBER_TEXT[1]
    elif alive_count <= 6:
        members = _MEMBER_TEXT[2]
    else:
        members = _MEMBER_TEXT[3]

    template = random.choice(_THINKING_TEMPLATES)
    text = template.format(
        sect=sect_name,
        econ=econ,
        strategy=strategy,
        members=members,
        war_status=war_str,
    )

    # 確保 ≥ 30（SectThinker._normalize 門檻）
    if len(text) < 30:
        text = f"{sect_name}已確立本輪治宗方針，當{strategy}，守規立德，靜待天時。"

    return text[:100]  # SectThinker._normalize 上限 100


def gen_sect_thinker(infos: dict) -> dict:
    return {"sect_thinking": _build_thinking(infos)}
