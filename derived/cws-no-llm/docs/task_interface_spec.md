# 任務介面規格 — 各 LLM Task 的輸入輸出

> 核對日期：2026-06-02（直接讀 `projects/cultivation-world-simulator/src` 原始碼確認）
>
> Shim Layer 必須對每個 task 返回與 LLM 版本**格式完全一致**的 JSON dict，
> 否則上層 Phase 代碼解析失敗。

---

## 不走 dispatcher 的 task

`sect_random_event` 和 `sect_random_event_reason` 的呼叫點使用 `call_llm_with_template()` 直呼，
**不經過 `call_llm_with_task_name()`**，因此 dispatcher 無法攔截。
如需替換，需直接 patch `src/systems/sect_random_event.py`。

---

## action_decision

**呼叫位置**: `src/classes/ai.py` 行 76  
**呼叫頻率**: 每月，每個無計畫的存活角色各呼叫一次

**輸入 `infos`**:
```python
{
    "avatar_name": str,          # 角色名（必有）
    "avatar_info": dict,
    "avatar_ai_context": dict,
    "world_info": dict,
    "world_lore": str,
    "general_action_infos": list,
    "player_command": str,
}
```

**返回格式（已確認）**:
```python
{
    infos["avatar_name"]: {
        "action_name_params_pairs": [
            ["action_id", {"param_key": val}],  # list of [name, params]
            # 多個動作組成一個月份行動鏈
        ],
        "avatar_thinking": str,        # 角色思考描述
        "short_term_objective": str,   # 短期目標描述
        "current_emotion": str,        # 當前情緒
    }
}
```

**消費端**（`ai.py:84-120`）：
```python
r = res[avatar.name]
raw_pairs = r.get("action_name_params_pairs", [])
for p in raw_pairs:
    if isinstance(p, list) and len(p) == 2:
        pairs.append((p[0], p[1] or {}))
```

---

## long_term_objective

**呼叫位置**: `src/classes/long_term_objective.py` 行 98  
**呼叫頻率**: 每月，需要重新規劃目標的角色

**返回格式（已確認）**:
```python
{
    "long_term_objective": str,   # 目標文字描述（直接賦給 avatar.long_term_objective）
}
```

注意：原設計假設有 `goal_type`/`goal_desc`/`priority`，但實際只用 `"long_term_objective"` 一個字串 key。

---

## relation_resolver

**呼叫位置**: `src/classes/relation/relation_resolver.py` 行 68  
**呼叫頻率**: 每次互動後（conversation、spar 等）

**返回格式（已確認）**:
```python
{
    "changed": bool,          # True = 有關係連結變化（師徒/仇敵等）
    "change_type": str,       # "ADD" 或 "REMOVE"（changed=False 時為 None）
    "relation": str,          # 關係枚舉名稱，如 "IS_MASTER_OF"（changed=False 時為 None）
    "reason": str,            # 原因說明
}
```

注意：原設計假設返回 friendliness delta，但實際是「是否新增/移除關係連結」。
friendliness delta 由 `relation_delta` 任務負責。

---

## relation_delta

**呼叫位置**: `src/classes/relation/relation_delta_service.py` 行 78  
**呼叫頻率**: 每次互動後

**返回格式（已確認）**:
```python
{
    "delta_a_to_b": int,   # A 對 B 的 friendliness 變化（-6 ~ +6）
    "delta_b_to_a": int,   # B 對 A 的 friendliness 變化
}
```

---

## story_teller

**呼叫位置**: `src/classes/story_teller.py` 行 121, 166  
**呼叫頻率**: 視 config.yml 概率觸發

**返回格式（已確認）**:
```python
{
    "story": str,   # 敘事文字（多句）
}
```

注意：原設計假設有 `"story_text"` 和 `"tone"`，但實際只用 `"story"` key。

---

## interaction_feedback

**呼叫位置**: `src/classes/mutual_action/mutual_action.py` 行 164  
**返回格式（已確認）**:
```python
{
    "response": str,    # 互動回應描述（主 key）
    "thinking": str,    # 思考過程（賦給 target_avatar.thinking）
    # 注：消費端有 result.get("response", result.get("feedback", "")) 的 fallback，
    #     用 "feedback" key 也可被消費，但推薦用 "response"
}
```

---

## history_influence

**注意**：在 `projects/cultivation-world-simulator/src` 全域搜尋未找到任何呼叫。
此 task 可能已棄用。dispatcher 保留映射但返回 `None`（fallback to LLM）。

---

## backstory

**呼叫位置**: `src/classes/backstory.py` 行 47  
**返回格式（已確認）**:
```python
{
    "backstory": str,   # 2-5 句的身世描述
}
```

---

## random_minor_event

**呼叫位置**: `src/systems/random_minor_event_service.py` 行 120  
**返回格式（已確認）**:
```python
{
    "event_text": str,   # 事件描述文字
}
```

注意：原設計假設有 `"event_desc"`，但實際 key 為 `"event_text"`。
返回空字串 `""` 可安全跳過事件生成（消費端有 `if not event_text: return []` 保護）。

---

## sect_random_event / sect_random_event_reason

**不走 `call_llm_with_task_name`**，直接呼叫 `call_llm_with_template()`。
dispatcher 無法攔截，如需替換需 patch `src/systems/sect_random_event.py`。
返回 key 為 `"reason_fragment"`（若未來 patch 時使用）。

---

## sect_decider

**呼叫位置**: `src/classes/sect_decider.py` 行 133  
**呼叫頻率**: 每 3 年執行一次

**返回格式（已確認，`_parse_plan()` 行 210-245）**:
```python
{
    "declare_war_target_ids":  list,  # 宣戰目標宗門 ID 列表
    "seek_peace_target_ids":   list,  # 求和目標宗門 ID 列表
    "recruit_avatar_ids":      list,  # 招募角色 ID 列表
    "expel_avatar_ids":        list,  # 驅逐角色 ID 列表
    "reward_avatar_ids":       list,  # 獎勵角色 ID 列表
    "support_avatar_ids":      list,  # 扶持角色 ID 列表
    "thinking":                str,   # 年度思考文字
}
```

注意：原設計假設有 `"strategy"` 和 `"actions"` key，但實際格式完全不同。

---

## sect_thinker

**呼叫位置**: `src/classes/sect_thinker.py` 行 57  
**返回格式（已確認）**:
```python
{
    "sect_thinking": str,   # 宗門年度思考文字（注意 key 名是 sect_thinking 不是 thinking）
}
```

---

## nickname

**呼叫位置**: `src/classes/nickname.py` 行 84  
**返回格式（已確認）**:
```python
{
    "nickname": str,    # 外號（空字串 = 安全跳過，消費端有 if not nickname: return None 保護）
    "reason":   str,    # 外號由來
    "thinking": str,    # 思考過程（可為空）
}
```

---

## single_choice

**呼叫位置**: `src/systems/single_choice/engine.py` 行 53  
**返回格式（已確認，`extract_choice_payload()` 行 11）**:
```python
{
    "choice":   str,   # 選擇的 key（空字串 = 觸發 fallback_policy，預設選第一個選項）
    "thinking": str,
}
```

---

## custom_content_generation

**注意**：`src/server/services/custom_content_service.py` 導入了 `call_llm_with_task_name`
但未找到以 `"custom_content_generation"` 為 task_name 的直接呼叫。
dispatcher 保留映射但返回 `None`（fallback to LLM）。
