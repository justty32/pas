# 任務介面規格 — 各 LLM Task 的輸入輸出

> 這是去 LLM 工程中最關鍵的文件。
> Shim Layer 必須對每個 task 返回與 LLM 版本**格式完全一致**的 JSON dict，
> 否則上層 Phase 代碼解析失敗。
>
> **TODO 標記**：尚未通過讀源碼確認的格式，需進入 Phase 0 開發時對照
> `projects/cultivation-world-simulator/src/sim/simulator_engine/phases/` 確認。

---

## 如何確認格式

最可靠方法：在 Phase 0 stub 裡先記錄 `infos`，再看消費端如何使用返回值：

```python
# stub 調試版（Phase 0 前期使用）
def dispatch(task_name: str, infos: dict):
    import json, logging
    logging.debug(f"[local_ai] task={task_name} infos_keys={list(infos.keys())}")
    # ... 返回 stub
```

然後啟動遊戲運行 1-2 月，從 log 裡確認每個 task 收到什麼 infos。

---

## action_decision

**呼叫位置**: `src/sim/simulator_engine/phases/actions.py::phase_decide_actions()`  
**呼叫頻率**: 每月，每個無計畫的存活角色各呼叫一次

**輸入 `infos` (推測，待確認)**:
```python
{
    "avatar_name": str,          # 角色名
    "realm": str,                # 境界英文 key（如 "QI_REFINEMENT"）
    "persona": list[str],        # 性格特質列表
    "location": str,             # 當前所在區域名
    "hp": float,                 # 生命值（0~1 比率）
    "long_term_goal": str,       # 當前長期目標描述
    "available_actions": list,   # 可執行動作列表（已過 can_possibly_start 篩選）
    "world_info": dict,          # 世界背景資訊
    "nearby_avatars": list,      # 附近角色資訊
    "relations": dict,           # 主要關係（與誰的 friendliness 值）
    # ... 其他上下文
}
```

**返回格式 (推測，待確認)**:
```python
{
    "action_name": str,       # 動作 ID（如 "meditate"、"attack"）
    "params": dict,           # 動作參數（如 {"target_avatar_id": 123}）
    "reason": str,            # 決策原因（可能用於 log 或 story）
}
```

**或可能是返回整個行動鏈**:
```python
{
    "actions": [
        {"action_name": "move_to_region", "params": {"region_id": 5}},
        {"action_name": "meditate", "params": {}},
    ]
}
```

**⚠️ 需重點確認**：`available_actions` 的結構（是 id 列表還是含 params 的 dict？），以及是返回單動作還是動作鏈。

---

## long_term_objective

**呼叫位置**: `src/sim/simulator_engine/phases/lifecycle.py::phase_long_term_objective_thinking()`  
**呼叫頻率**: 每月，需要重新規劃目標的角色

**輸入 `infos` (推測)**:
```python
{
    "avatar_name": str,
    "realm": str,
    "age": int,
    "persona": list[str],
    "current_goal": str,        # 現有目標描述
    "recent_events": list[str], # 近期重大事件
    "relations": dict,          # 重要關係
    "sect": str | None,         # 所屬宗門
}
```

**返回格式 (推測)**:
```python
{
    "goal_type": str,           # 目標類型（如 "BREAKTHROUGH_REALM"）
    "goal_desc": str,           # 自然語言描述（用於顯示）
    "priority": float,          # 優先級（0~1）
    "sub_goals": list[str],     # 中期子目標（可為空）
}
```

---

## relation_resolver

**呼叫位置**: `src/classes/relation/relation_resolver.py`  
**呼叫頻率**: 每次互動後（conversation、spar、gift 等）

**輸入 `infos` (推測)**:
```python
{
    "avatar_a": {"name": str, "persona": list, "realm": str},
    "avatar_b": {"name": str, "persona": list, "realm": str},
    "interaction_type": str,     # 互動類型（如 "conversation"）
    "interaction_desc": str,     # 互動描述（事件文字）
    "current_friendliness": float,
    "history_summary": str,      # 過往關係摘要
}
```

**返回格式 (推測)**:
```python
{
    "delta_a_to_b": float,      # A 對 B 的 friendliness 變化（-6 ~ +6）
    "delta_b_to_a": float,      # B 對 A 的 friendliness 變化
    "reason": str,              # 原因描述
}
```

---

## relation_delta

與 `relation_resolver` 類似，可能是更簡單的版本：

**返回格式**:
```python
{"delta": float}
```

---

## story_teller

**呼叫位置**: `src/classes/story_event_service.py::StoryEventService`  
**呼叫頻率**: 視 `config.yml` 中 `story.probabilities` 的概率觸發

**輸入 `infos` (推測)**:
```python
{
    "event_type": str,           # 事件類型（如 "combat"、"cultivation_major"）
    "avatars": list[dict],       # 涉及角色資訊
    "base_event": dict,          # 基礎事件（已有的結構化事件）
    "world_info": dict,
}
```

**返回格式 (推測)**:
```python
{
    "story_text": str,           # 敘事文字（多句）
    "tone": str,                 # 敘事語氣（如 "悲壯"、"詼諧"）
}
```

---

## interaction_feedback

**呼叫位置**: 互動結算後  
**返回格式**:
```python
{
    "feedback": str,             # 一句話描述互動結果
}
```

---

## history_influence

**呼叫位置**: `src/classes/action/`（歷史影響計算）  
**返回格式 (推測)**:
```python
{
    "influence_score": float,    # 影響係數
    "desc": str,                 # 描述
}
```

---

## backstory

**呼叫位置**: `src/sim/simulator_engine/phases/lifecycle.py::phase_backstory_generation()`  
**返回格式 (推測)**:
```python
{
    "backstory": str,            # 2-5 句的身世描述
}
```

---

## random_minor_event

**呼叫位置**: `src/systems/random_minor_event_service.py`  
**返回格式 (推測)**:
```python
{
    "event_desc": str,           # 事件描述
    "effects": list[dict],       # 對角色的影響（可為空）
}
```
或返回 `None` 表示不觸發。

---

## sect_random_event / sect_random_event_reason

**呼叫位置**: `src/systems/sect_random_event.py`  
**返回格式**:
```python
# sect_random_event
{
    "event_desc": str,
    "effects": list[dict],
}

# sect_random_event_reason
{
    "reason": str,               # 一句話原因
}
```

---

## sect_decider

**呼叫位置**: `src/classes/sect_decider.py`（每 3 年執行一次）  
**輸入 `infos` 重點欄位**:
```python
{
    "sect_name": str,
    "sect_realm_avg": float,
    "member_count": int,
    "territory_count": int,
    "resources": int,
    "relations": dict,           # 與其他宗門的關係
    "world_events": list,        # 近期世界事件
}
```

**返回格式 (推測)**:
```python
{
    "strategy": str,             # 策略（EXPAND/CONSOLIDATE/RECRUIT/WAR/TRAIN）
    "actions": list[dict],       # 具體行動計畫
    "yearly_thinking": str,      # 年度反思文字（顯示在前端宗門詳情頁）
}
```

---

## sect_thinker

**返回格式**:
```python
{
    "thinking": str,             # 宗門年度思考/反思文字（1-3 句）
}
```

---

## nickname

**呼叫位置**: `src/sim/simulator_engine/phases/lifecycle.py::phase_nickname_generation()`  
**輸入 `infos` 重點欄位**:
```python
{
    "avatar_name": str,
    "realm": str,
    "persona": list[str],
    "notable_deeds": list[str],  # 重大事蹟列表
    "kill_count": int,
    "age": int,
}
```

**返回格式**:
```python
{
    "nickname": str,             # 外號（2-5 字）
    "reason": str,               # 外號由來
}
```

---

## single_choice

**呼叫位置**: `src/systems/single_choice/`（roleplay 決策邊界）  
**返回格式 (推測)**:
```python
{
    "choices": [
        {"id": "1", "text": str, "effect_desc": str},
        {"id": "2", "text": str, "effect_desc": str},
    ]
}
```

---

## custom_content_generation

**呼叫位置**: `src/server/services/custom_content_service.py`  
**用途**: 玩家要求生成自訂宗門/功法/裝備時使用  
**替換策略**: 返回 `None` 讓其 fallback LLM，或提供有限的預設模板  
**優先級最低**，Phase 4 再處理。
