# 效用 AI 規格 (Utility AI Spec) — action_decision

> `action_decision` 是整個去 LLM 計畫中最複雜、影響最大的任務。
> 這份文件定義 Utility AI 的完整設計。

---

## 一、核心概念

**效用 AI**（Utility AI）：對每個可用動作計算一個「效用分數」，選出分數最高的動作執行。

```
decision(avatar, world) → argmax over actions of:  utility(action, avatar, world)
```

與 LLM 版本的差異：LLM 能理解自然語言上下文，Utility AI 只能用數值化的狀態因子。但修仙世界的狀態可以很好地數值化（境界壓力、HP、靈石、關係值），效果應該可接受。

---

## 二、效用分數組成

```
utility(action, avatar, world) =
    base_weight(action)
    × persona_multiplier(avatar.persona, action)
    × goal_alignment(avatar.goal, action)
    × resource_feasibility(avatar, action, world)
    × realm_pressure(avatar, action)
    × social_context(avatar, action, world)
    × urgency_override(avatar, action)  ← 可覆蓋所有其他因子
    × random_noise(ε)                   ← 避免行為完全固化
```

所有因子為乘法組合。任一因子為 0 則整體為 0（動作被排除）。  
`urgency_override` 在緊急情況（HP 極低、被追殺）可強制某動作效用最高。

---

## 三、各因子設計

### 3.1 base_weight — 動作基礎效用

基本假設：每個動作在「沒有特殊情境」時的合理發生頻率。

```python
BASE_WEIGHT = {
    # 日常行動
    "meditate":           1.5,   # 修煉是常態
    "retreat":            1.2,   # 閉關也常見
    "move_to_region":     1.0,   # 移動正常
    "rest":               0.6,   # 休息不那麼常用
    
    # 經濟行動
    "buy":                0.6,
    "sell":               0.5,
    "harvest":            0.8,
    "mine":               0.7,
    "hunt":               0.8,
    "plant":              0.5,
    "refine":             0.7,   # 煉丹
    
    # 社交行動
    "play":               0.5,
    "help_people":        0.4,
    "sect_mission":       1.3,   # 有宗門任務時優先
    
    # 高風險行動
    "attack":             0.4,   # 主動攻擊基礎低
    "assassinate":        0.2,
    "devour_people":      0.15,
    "plunder_people":     0.2,
    
    # 逃跑
    "escape":             0.0,   # 僅在 urgency_override 觸發
    "move_away_from_avatar": 0.1,
}
```

---

### 3.2 persona_multiplier — 性格修正

```python
PERSONA_EFFECT = {
    # (性格特質, 動作類型) → 乘數
    ("好鬥", "attack"):           2.0,
    ("好鬥", "spar"):             1.8,
    ("好鬥", "retreat"):          0.3,
    
    ("謹慎", "attack"):           0.2,
    ("謹慎", "retreat"):          1.5,
    ("謹慎", "meditate"):         1.3,
    
    ("好學", "meditate"):         1.6,
    ("好學", "retreat"):          1.4,
    
    ("貪財", "buy"):              1.5,
    ("貪財", "mine"):             1.4,
    ("貪財", "harvest"):          1.3,
    ("貪財", "plunder_people"):   1.6,
    
    ("俠義", "help_people"):      2.0,
    ("俠義", "attack"):           0.6,   # 俠義者不隨意出手
    ("俠義", "devour_people"):    0.0,   # 絕對不做
    
    ("殘忍", "devour_people"):    1.8,
    ("殘忍", "attack"):           1.5,
    ("殘忍", "help_people"):      0.1,
    
    ("隱逸", "meditate"):         1.5,
    ("隱逸", "move_to_region"):   0.5,  # 不愛四處走
    ("隱逸", "retreat"):          1.8,
    
    ("雄心", "meditate"):         1.3,
    ("雄心", "sect_mission"):     1.5,
    ("雄心", "rest"):             0.4,
}

def persona_multiplier(persona_list: list[str], action_name: str) -> float:
    mult = 1.0
    for trait in persona_list:
        if (trait, action_name) in PERSONA_EFFECT:
            mult *= PERSONA_EFFECT[(trait, action_name)]
        # 模糊匹配：動作分類
        action_category = get_action_category(action_name)  # combat/economy/social/cultivation
        if (trait, action_category) in PERSONA_EFFECT:
            mult *= PERSONA_EFFECT[(trait, action_category)] ** 0.5  # 分類效果打折
    return mult
```

**動作分類**（用於模糊匹配）：
```python
ACTION_CATEGORIES = {
    "combat":      ["attack", "assassinate", "spar", "devour_people"],
    "cultivation": ["meditate", "retreat", "temper", "breakthrough"],
    "economy":     ["buy", "sell", "mine", "harvest", "hunt", "plant", "refine"],
    "social":      ["play", "help_people", "sect_mission", "govern"],
    "movement":    ["move_to_region", "move_to_avatar", "escape"],
}
```

---

### 3.3 goal_alignment — 目標對齊

```python
GOAL_ACTION_ALIGNMENT = {
    # (目標類型, 動作) → 乘數
    ("BREAKTHROUGH_REALM", "meditate"):        2.0,
    ("BREAKTHROUGH_REALM", "retreat"):         2.2,
    ("BREAKTHROUGH_REALM", "buy"):             0.8,   # 買材料可以，但不是重點
    
    ("ACCUMULATE_WEALTH", "mine"):             1.8,
    ("ACCUMULATE_WEALTH", "harvest"):          1.7,
    ("ACCUMULATE_WEALTH", "sell"):             1.5,
    ("ACCUMULATE_WEALTH", "buy"):              0.7,   # 省著花
    
    ("SEEK_REVENGE", "attack"):                2.0,   # 只針對仇人
    ("SEEK_REVENGE", "move_to_avatar"):        1.5,   # 追蹤仇人
    
    ("ACQUIRE_TECHNIQUE", "buy"):              1.5,   # 購買功法書
    ("ACQUIRE_TECHNIQUE", "sect_mission"):     1.3,   # 完成任務換功法
    
    ("JOIN_SECT", "move_to_region"):           1.3,   # 前往宗門所在地
    
    ("FIND_MASTER", "move_to_avatar"):         1.5,   # 尋找潛在師父
    ("FIND_MASTER", "sect_mission"):           1.2,
    
    ("GAIN_REPUTATION", "help_people"):        1.5,
    ("GAIN_REPUTATION", "spar"):              1.3,
    ("GAIN_REPUTATION", "sect_mission"):       1.4,
}

def goal_alignment(goal_type: str, action_name: str, action_params: dict, avatar) -> float:
    base = GOAL_ACTION_ALIGNMENT.get((goal_type, action_name), 1.0)
    
    # 特殊情況：SEEK_REVENGE 只對仇人的 attack/move_to_avatar 有效
    if goal_type == "SEEK_REVENGE" and action_name in ("attack", "move_to_avatar"):
        target = action_params.get("target_avatar_id")
        if target and not avatar.is_enemy(target):
            return 1.0  # 不是仇人，不加成
    
    return base
```

---

### 3.4 resource_feasibility — 資源可行性

確保 NPC 不做「做了也沒意義」的動作：

```python
def resource_feasibility(avatar, action_name, world) -> float:
    if action_name == "buy":
        if avatar.gold < MIN_BUY_GOLD:
            return 0.1     # 沒錢還去買，大幅降低
        return 1.0
    
    if action_name == "refine":
        if not avatar.has_refine_materials():
            return 0.0     # 沒材料不能煉丹
        return 1.0
    
    if action_name in ("mine", "harvest"):
        region = world.get_region(avatar.location)
        if region.resource_depleted:
            return 0.2
        return 1.0
    
    return 1.0
```

---

### 3.5 realm_pressure — 境界壓力

修仙世界的核心驅動力：境界壓力讓角色不斷修煉。

```python
def realm_pressure(avatar, action_name) -> float:
    # 修煉進度（0=剛突破，1=即將突破）
    progress = avatar.cultivation_progress
    
    if action_name in ("meditate", "retreat", "temper"):
        # 進度越高，修煉效用越強（接近突破時加速）
        return 1.0 + progress * 1.5
    
    if action_name == "breakthrough":
        if progress >= 0.95:
            return 3.0    # 強力觸發突破嘗試
        return 0.0        # 進度未到不突破
    
    # 高進度時，非修煉動作略微降低
    if progress > 0.8 and action_name not in ("meditate", "retreat", "temper"):
        return 0.9
    
    return 1.0
```

---

### 3.6 social_context — 社交情境

```python
def social_context(avatar, action_name, action_params, world) -> float:
    target_id = action_params.get("target_avatar_id")
    if target_id is None:
        return 1.0
    
    friendliness = avatar.get_friendliness(target_id)
    
    if action_name == "attack":
        if friendliness > 0:
            return 0.1    # 不攻擊朋友（除非被強制）
        if friendliness < -60:
            return 1.5    # 攻擊仇敵加成
        return 0.8
    
    if action_name in ("play", "talk"):
        if friendliness < -25:
            return 0.3    # 不跟討厭的人玩
        if friendliness > 50:
            return 1.4    # 跟好友玩
        return 1.0
    
    if action_name == "help_people":
        if friendliness > 25:
            return 1.3
        return 0.8
    
    return 1.0
```

---

### 3.7 urgency_override — 緊急覆蓋

緊急情況直接覆蓋所有其他計算：

```python
def urgency_override(avatar, action_name, world) -> float:
    # 生命值危急
    if avatar.hp_ratio < 0.2:
        if action_name in ("escape", "move_away_from_avatar", "self_heal", "rest"):
            return 10.0   # 強制逃跑/治療
        if action_name in ("meditate", "retreat"):
            return 0.1    # 瀕死不修煉
        if action_name == "attack":
            return 0.05   # 瀕死不主動攻擊
    
    # 被追殺（仇人在同區域且比自己強）
    if has_overwhelming_threat(avatar, world):
        if action_name in ("escape", "move_away_from_avatar"):
            return 8.0
    
    # 宗門緊急任務
    if avatar.has_urgent_sect_mission():
        if action_name == "sect_mission":
            return 3.0
    
    return 1.0   # 無緊急情況，不影響
```

---

### 3.8 random_noise — 隨機擾動

防止所有 NPC 做完全相同的決策：

```python
def random_noise(ε: float = 0.15) -> float:
    return 1.0 + random.uniform(-ε, ε)
```

---

## 四、完整決策流程

```python
class UtilityAIDecision:
    def decide(self, avatar, world, available_actions: list[ActionOption]) -> ActionOption:
        scored = []
        for action in available_actions:
            score = (
                self._base_weight(action.name)
                * self._persona_mult(avatar.persona, action.name)
                * self._goal_align(avatar.long_term_goal_type, action.name, action.params, avatar)
                * self._resource(avatar, action.name, world)
                * self._realm_pressure(avatar, action.name)
                * self._social(avatar, action.name, action.params, world)
                * self._urgency(avatar, action.name, world)
                * self._noise()
            )
            scored.append((score, action))
        
        # Softmax 選擇（而非直接 argmax，保留一點隨機性）
        return self._softmax_sample(scored, temperature=0.8)
    
    def _softmax_sample(self, scored, temperature=0.8) -> ActionOption:
        scores = [s for s, _ in scored]
        # 溫度調節：temperature 越高越隨機，越低越貪心
        exp_scores = [math.exp(s / temperature) for s in scores]
        total = sum(exp_scores)
        probs = [e / total for e in exp_scores]
        return random.choices([a for _, a in scored], weights=probs)[0]
```

---

## 五、Softmax vs Argmax

使用 **Softmax 採樣**而非直接取最高分有以下原因：

1. **行為多樣性**：同條件下不同角色有不同選擇，更真實
2. **涌現性**：偶爾做「次優」決策產生意外劇情
3. **溫度可調**：`temperature=0.0` 退化成確定性 argmax（用於測試）

---

## 六、返回格式

符合原版 LLM 消費端期望的格式：

```python
{
    "action_name": "meditate",
    "params": {},
    "reason": "境界壓力（進度 0.87）× 好學性格，選擇修煉",  # 調試用
    "_debug": {
        "scores": {"meditate": 3.24, "retreat": 2.87, "buy": 0.43}
    }
}
```

`_debug` 欄位在 Phase 1 開發時用於驗證決策是否合理，之後可關閉。

---

## 七、待確認項目

1. `available_actions` 的確切結構（`ActionOption` 是什麼？）  
   → 讀 `src/sim/simulator_engine/phases/actions.py` 的呼叫代碼

2. 返回的 `params` 格式（每個動作類型的 params 是什麼鍵？）  
   → 讀 `src/classes/action/param_options.py` 和 `action.py`

3. 是返回單一動作還是動作鏈？  
   → 讀 Phase 4 之後如何消費 `action_decision` 的返回值

4. `long_term_goal` 在 infos 裡是字串描述還是 goal_type enum？  
   → 決定 `goal_alignment` 的 key 設計
