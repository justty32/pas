"""
Phase 0: 全任務 stub。返回最小合法值讓遊戲可以跑。
Phase 1+: 逐步替換為真正的本地 AI 實作。

返回格式全部以 projects/cultivation-world-simulator/src 原始碼核對（2026-06-02）：
  - action_decision   : ai.py:84 — {avatar_name: {"action_name_params_pairs": [...]}}
  - long_term_objective: long_term_objective.py:100 — {"long_term_objective": str}
  - relation_resolver  : relation_resolver.py:70 — {"changed": bool, "change_type", "relation", "reason"}
  - relation_delta     : relation_delta_service.py:79 — {"delta_a_to_b": int, "delta_b_to_a": int}
  - story_teller       : story_teller.py:122 — {"story": str}
  - interaction_feedback: mutual_action.py:266 — {"response": str, "thinking": str}
  - backstory          : backstory.py:49 — {"backstory": str}
  - random_minor_event : random_minor_event_service.py:132 — {"event_text": str}
  - sect_decider       : sect_decider.py:210-245 — {id lists + "thinking"}
  - sect_thinker       : sect_thinker.py:62 — {"sect_thinking": str}
  - nickname           : nickname.py:86 — {"nickname": str, "reason": str}
  - single_choice      : parser.py:11 — {"choice": str, "thinking": str}
  NOTE: sect_random_event / sect_random_event_reason 使用 call_llm_with_template 直呼，不經此 dispatcher。
  NOTE: history_influence / custom_content_generation 原始碼未找到呼叫，保留為 None fallback。
"""
import logging

logger = logging.getLogger("local_ai")


def dispatch(task_name: str, infos: dict):
    """
    路由 task_name 到本地處理器。
    返回 dict = 本地 AI 已處理（不走 LLM）。
    返回 None  = 無本地處理器，fallback 到 LLM。
    """
    logger.debug("[local_ai] task=%s infos_keys=%s", task_name, list(infos.keys()))

    handler = _HANDLERS.get(task_name)
    if handler is None:
        return None

    try:
        result = handler(infos)
        if result is not None:
            logger.debug("[local_ai] task=%s result_keys=%s", task_name, list(result.keys()))
        return result
    except Exception as exc:
        logger.error("[local_ai] task=%s error: %s", task_name, exc, exc_info=True)
        return None  # 出錯時 fallback，避免崩潰


# ── Stub 處理器 ────────────────────────────────────────────────────────────────

def _stub_action_decision(infos: dict) -> dict:
    """
    Phase 0: 永遠選 meditate。
    返回格式: {avatar_name: {"action_name_params_pairs": [[name, params], ...]}}
    """
    avatar_name = infos.get("avatar_name", "unknown")
    return {
        avatar_name: {
            "action_name_params_pairs": [["meditate", {}]],
            "avatar_thinking": "[stub] 靜心修煉",
            "short_term_objective": "突破境界",
            "current_emotion": "平靜",
        }
    }


def _stub_long_term_objective(infos: dict) -> dict:
    """返回格式: {"long_term_objective": str}"""
    return {"long_term_objective": "[stub] 突破境界，精進修為"}


def _stub_relation_resolver(infos: dict) -> dict:
    """
    返回格式: {"changed": bool, "change_type": str|None, "relation": str|None, "reason": str}
    changed=False 表示本次互動不產生關係連結變化。
    """
    return {
        "changed": False,
        "change_type": None,
        "relation": None,
        "reason": "[stub] 平淡交流，無甚變化",
    }


def _stub_relation_delta(infos: dict) -> dict:
    """返回格式: {"delta_a_to_b": int, "delta_b_to_a": int}"""
    return {"delta_a_to_b": 0, "delta_b_to_a": 0}


def _stub_story_teller(infos: dict) -> dict:
    """返回格式: {"story": str}"""
    avatars = infos.get("avatars", [{}])
    name = avatars[0].get("name", "修士") if avatars else "修士"
    return {"story": f"[stub] {name}繼續修煉，世界平靜如常。"}


def _stub_interaction_feedback(infos: dict) -> dict:
    """返回格式: {"response": str, "thinking": str}"""
    return {
        "response": "[stub] 雙方寒暄幾句，無甚要事。",
        "thinking": "",
    }


def _stub_backstory(infos: dict) -> dict:
    """返回格式: {"backstory": str}"""
    name = infos.get("avatar_name", "此人")
    return {"backstory": f"[stub] {name}來歷不明，默默無聞，正踏上修仙之路。"}


def _stub_random_minor_event(infos: dict) -> dict:
    """
    返回 event_text="" 讓 _generate_event_text() 返回空字串，
    上層 try_create_events() 的 if not event_text 保護會跳過建立事件。
    （不可返回 None，否則 fallback 到 LLM）
    """
    return {"event_text": ""}


def _stub_sect_decider(infos: dict) -> dict:
    """
    返回格式: 六個 ID list + "thinking"
    _parse_plan() 解析時每個 list 為空 = 不執行任何宗門行動。
    """
    return {
        "declare_war_target_ids": [],
        "seek_peace_target_ids": [],
        "recruit_avatar_ids": [],
        "expel_avatar_ids": [],
        "reward_avatar_ids": [],
        "support_avatar_ids": [],
        "thinking": "[stub] 宗門平靜，以訓練弟子為本。",
    }


def _stub_sect_thinker(infos: dict) -> dict:
    """返回格式: {"sect_thinking": str}（注意不是 "thinking"）"""
    return {"sect_thinking": "[stub] 宗門無甚大事，靜待時機。"}


def _stub_nickname(infos: dict) -> dict:
    """
    返回空字串讓 generate_nickname() 的 if not nickname: return None 保護生效，
    安全跳過外號生成。（不可返回 Python None，否則 .get() 會 AttributeError）
    """
    return {"nickname": "", "reason": "", "thinking": ""}


def _stub_single_choice(infos: dict) -> dict:
    """
    返回空 choice 讓 normalize_choice_key("") 返回 None，
    觸發 fallback_policy（預設選第一個選項）。
    """
    return {"choice": "", "thinking": ""}


# ── Handler 映射表 ─────────────────────────────────────────────────────────────

_HANDLERS = {
    "action_decision":          _stub_action_decision,
    "long_term_objective":      _stub_long_term_objective,
    "relation_resolver":        _stub_relation_resolver,
    "relation_delta":           _stub_relation_delta,
    "story_teller":             _stub_story_teller,
    "interaction_feedback":     _stub_interaction_feedback,
    "backstory":                _stub_backstory,
    "random_minor_event":       _stub_random_minor_event,
    "sect_decider":             _stub_sect_decider,
    "sect_thinker":             _stub_sect_thinker,
    "nickname":                 _stub_nickname,
    "single_choice":            _stub_single_choice,
    # 以下在原始碼未見 call_llm_with_task_name 呼叫，保留為 None fallback
    "history_influence":        lambda _: None,
    "custom_content_generation": lambda _: None,
    # sect_random_event / sect_random_event_reason 使用 call_llm_with_template 直呼，不在此。
}
