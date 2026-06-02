# Phase 0 實作指南 — 全任務 Stub

> **目標**：讓遊戲在零 LLM 環境下可以啟動並跑完若干月份，不崩潰。
> 先不管行為是否合理（NPC 全部傻傻修煉也沒關係），重要的是建立可迭代的基礎。

---

## 步驟 1：確認改動位置

原版 `src/utils/llm/client.py` 的 `call_llm_with_task_name()`（約 431 行）：

```python
async def call_llm_with_task_name(
    task_name: str,
    template_path: Path | str,
    infos: dict,
    max_retries: int | None = None
) -> dict:
    mode = get_task_mode(task_name)
    return await call_llm_with_template(template_path, infos, mode, max_retries)
```

**要加的 4 行**：

```python
async def call_llm_with_task_name(
    task_name: str,
    template_path: Path | str,
    infos: dict,
    max_retries: int | None = None
) -> dict:
    # === Phase 0: 本地 AI 優先 ===
    from src.local_ai.dispatcher import dispatch
    local_result = dispatch(task_name, infos)
    if local_result is not None:
        return local_result
    # === END ===

    mode = get_task_mode(task_name)
    return await call_llm_with_template(template_path, infos, mode, max_retries)
```

---

## 步驟 2：建立 dispatcher（stub 版）

建立 `src/local_ai/__init__.py`（空文件）和 `src/local_ai/dispatcher.py`：

```python
# src/local_ai/dispatcher.py
"""
Phase 0: 全任務 stub。返回最小合法值讓遊戲可以跑。
Phase 1+: 逐步替換為真正的本地 AI 實作。
"""
import logging

logger = logging.getLogger("local_ai")

def dispatch(task_name: str, infos: dict):
    """
    路由 task_name 到本地處理器。
    返回 dict = 已由本地 AI 處理（不走 LLM）。
    返回 None = 無本地處理器，fallback 到 LLM。
    """
    # debug log（Phase 0 必開，Phase 1 後可降到 DEBUG 級別）
    logger.debug(f"[local_ai] task={task_name} infos_keys={list(infos.keys())}")
    
    handler = _HANDLERS.get(task_name)
    if handler is None:
        return None  # fallback to LLM
    
    try:
        result = handler(infos)
        logger.debug(f"[local_ai] task={task_name} result_keys={list(result.keys()) if result else None}")
        return result
    except Exception as e:
        logger.error(f"[local_ai] task={task_name} error: {e}", exc_info=True)
        return None  # 出錯時也 fallback，避免崩潰


# ── Stub 處理器 ──────────────────────────────────────────────────────────────
# 這些是 Phase 0 的最小實作，目的是讓遊戲能跑起來。
# 在後續 Phase 中逐步替換為真正實作。

def _stub_action_decision(infos: dict) -> dict:
    """Phase 0 stub: 永遠選 meditate"""
    available = infos.get("available_actions", [])
    # 嘗試找 meditate，找不到就用第一個可用動作
    for action in available:
        name = action.get("action_name", action) if isinstance(action, dict) else action
        if name == "meditate":
            return {"action_name": "meditate", "params": {}, "reason": "[stub] 默認修煉"}
    if available:
        first = available[0]
        name = first.get("action_name", first) if isinstance(first, dict) else first
        return {"action_name": name, "params": {}, "reason": "[stub] 第一個可用動作"}
    return {"action_name": "rest", "params": {}, "reason": "[stub] 無可用動作，休息"}


def _stub_long_term_objective(infos: dict) -> dict:
    return {
        "goal_type": "BREAKTHROUGH_REALM",
        "goal_desc": "突破境界，精進修為",
        "priority": 0.8,
        "sub_goals": [],
    }


def _stub_relation_resolver(infos: dict) -> dict:
    return {"delta_a_to_b": 0, "delta_b_to_a": 0, "reason": "[stub] 平淡交流"}


def _stub_relation_delta(infos: dict) -> dict:
    return {"delta": 0}


def _stub_story_teller(infos: dict) -> dict:
    avatar = infos.get("avatar_name", infos.get("avatars", [{}])[0].get("name", "修士"))
    return {"story_text": f"[stub] {avatar}繼續修煉，世界平靜如常。", "tone": "平淡"}


def _stub_interaction_feedback(infos: dict) -> dict:
    return {"feedback": "[stub] 雙方寒暄幾句，無甚要事。"}


def _stub_history_influence(infos: dict) -> dict:
    return {"influence_score": 0.0, "desc": "[stub] 歷史影響中性"}


def _stub_backstory(infos: dict) -> dict:
    name = infos.get("avatar_name", "此人")
    return {"backstory": f"[stub] {name}來歷不明，默默無聞，正踏上修仙之路。"}


def _stub_sect_decider(infos: dict) -> dict:
    return {
        "strategy": "TRAIN",
        "actions": [],
        "yearly_thinking": "[stub] 宗門平靜，以訓練弟子為本。",
    }


def _stub_sect_thinker(infos: dict) -> dict:
    return {"thinking": "[stub] 宗門無甚大事，靜待時機。"}


def _stub_nickname(infos: dict) -> dict:
    # Phase 0 不生成外號（返回 None 讓呼叫端跳過）
    # 注意：若消費端不接受 None 這裡需要改
    return None


def _stub_single_choice(infos: dict) -> dict:
    return {"choices": []}


def _stub_custom_content(infos: dict) -> dict:
    return None  # fallback to LLM（custom content 暫不替換）


# ── Handler 映射表 ────────────────────────────────────────────────────────────
_HANDLERS = {
    "action_decision":            _stub_action_decision,
    "long_term_objective":        _stub_long_term_objective,
    "relation_resolver":          _stub_relation_resolver,
    "relation_delta":             _stub_relation_delta,
    "story_teller":               _stub_story_teller,
    "interaction_feedback":       _stub_interaction_feedback,
    "history_influence":          _stub_history_influence,
    "backstory":                  _stub_backstory,
    "random_minor_event":         lambda _: None,  # 不觸發隨機事件
    "sect_random_event":          lambda _: None,
    "sect_random_event_reason":   lambda _: {"reason": "[stub] 形勢所需"},
    "sect_decider":               _stub_sect_decider,
    "sect_thinker":               _stub_sect_thinker,
    "nickname":                   _stub_nickname,
    "single_choice":              _stub_single_choice,
    "custom_content_generation":  _stub_custom_content,
}
```

---

## 步驟 3：驗證

1. 啟動遊戲（`python src/server/main.py --dev`），配置一個 LLM（備用）
2. 開始新遊戲
3. 觀察 log，確認 `[local_ai]` 前綴的 debug 訊息出現
4. 讓模擬跑 10 個月
5. **確認沒有崩潰**，事件正常入庫

---

## 步驟 4：Phase 0 期間需收集的資訊

從 debug log 確認每個 task 的 infos 鍵名（對照 `docs/task_interface_spec.md` 的「待確認」項目）：

```
[local_ai] task=action_decision infos_keys=['avatar_name', 'realm', 'persona', ...]
[local_ai] task=long_term_objective infos_keys=[...]
...
```

收集後填回 `docs/task_interface_spec.md`，讓後續 Phase 的真正實作有準確的輸入格式。

---

## Phase 0 完成標準

- [ ] 遊戲可在 `--no-llm` 模式或無網路環境啟動
- [ ] 10 月模擬無崩潰
- [ ] 全部 16 個 task 的 infos 鍵名已記錄到 `task_interface_spec.md`
- [ ] 確認 `nickname` 和 `random_minor_event` 返回 `None` 時消費端是否安全處理

---

## 可能的坑

### 坑 1：`nickname` 返回 `None` 但消費端做 `result["nickname"]`

如果 `phase_nickname_generation()` 直接做：
```python
result = await call_llm_with_task_name("nickname", ...)
avatar.nickname = result["nickname"]  # 若 result 是 None 會 KeyError
```

需要在消費端加 guard，或讓 stub 返回 `{"nickname": None}` 而非 Python `None`。

### 坑 2：`action_decision` 消費端期望的是動作鏈而非單動作

若消費端這樣讀：
```python
result = await call_llm_with_task_name("action_decision", ...)
for action in result["actions"]:  # 預期 list
    ...
```

但 stub 返回的是 `{"action_name": ..., "params": ...}`（單動作），就會 KeyError。  
Phase 0 開發時必須先確認這個格式。

### 坑 3：`random_minor_event` / `sect_random_event` 返回 `None`

若消費端：
```python
result = await call_llm_with_task_name("random_minor_event", ...)
event = Event(desc=result["event_desc"])  # None 會 TypeError
```

同坑 1，需先確認消費端是否有 `if result is None: return` 的 guard。
