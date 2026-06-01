# 設計總覽 — cws-no-llm

**版本**: v0.1（規劃階段）  
**參照**: `analysis/cultivation-world-simulator/architecture/02_level2_modules.md`

---

## 一、核心策略：Shim Layer

修改 `src/utils/llm/client.py::call_llm_with_task_name()` 使其在呼叫 urllib 前先查詢本地 AI 引擎：

```python
# src/utils/llm/client.py（改動點）
async def call_llm_with_task_name(task_name, template_path, infos, max_retries=None):
    # 新增：若本地 AI 有處理器，直接返回，不走網路
    from src.local_ai.dispatcher import dispatch
    local_result = dispatch(task_name, infos)
    if local_result is not None:
        return local_result

    # 原版邏輯（降級到 LLM，僅在顯式啟用時）
    mode = get_task_mode(task_name)
    return await call_llm_with_template(template_path, infos, mode, max_retries)
```

`src/local_ai/dispatcher.py` 是唯一的路由入口，按 `task_name` 分派到對應引擎。

---

## 二、新增模組結構

```
src/local_ai/
├── __init__.py
├── dispatcher.py           # 路由入口：task_name → handler
├── decision.py             # action_decision：效用 AI
├── goals.py                # long_term_objective：目標優先級
├── relations.py            # relation_resolver + relation_delta
├── narrative.py            # story_teller + interaction_feedback + backstory
├── events.py               # random_minor_event + sect_random_event
├── sect_strategy.py        # sect_decider + sect_thinker
├── epithets.py             # nickname
├── choices.py              # single_choice
└── data/
    ├── vocab/
    │   ├── adjectives.py   # 形容詞詞庫（按分類）
    │   ├── verbs.py        # 動詞詞庫（按動作類型）
    │   ├── nouns.py        # 名詞詞庫
    │   └── epithets.py     # 外號片段詞庫
    ├── templates/
    │   ├── narrative.py    # 敘事模板字串
    │   ├── backstory.py    # 傳記模板
    │   └── events.py       # 事件描述模板
    └── decision/
        ├── utility.py      # 動作效用權重表
        └── goals.py        # 目標類型定義
```

---

## 三、各子系統設計

### 3.1 `action_decision` → 效用 AI（Utility AI）

**目標**：給定 NPC 當前狀態與可執行動作列表，選出最合理的動作。

**原理**：
```
utility(action, avatar, world) = base_weight(action)
                                × persona_modifier(avatar.persona, action)
                                × goal_modifier(avatar.long_term_goal, action)
                                × resource_modifier(avatar, action)
                                × realm_modifier(avatar.realm, action)
                                × social_modifier(avatar, action, world)
```

**實作方式**：

每個動作類型預定義基礎效用（base_weight），再套乘情境係數。

```python
# data/decision/utility.py
BASE_WEIGHTS = {
    "meditate":  1.5,  # 修煉基礎效用高
    "move":      1.0,
    "attack":    0.8,  # 攻擊有風險，基礎低
    "buy":       0.6,
    "rest":      0.4,
    "retreat":   1.2,  # 閉關高
    # ...
}

PERSONA_MODIFIERS = {
    # (persona_trait, action_type) -> multiplier
    ("好鬥", "attack"):    1.8,
    ("謹慎", "attack"):    0.3,
    ("好學", "meditate"):  1.5,
    ("貪財", "buy"):       1.6,
    ("俠義", "help_people"): 1.8,
    # ...
}
```

**特殊規則**（硬性覆蓋效用評分）：
- 若 HP < 30%，`self_heal / rest` 效用強制最高
- 若同區域有仇敵（relations < -60），`flee / attack` 機率上升
- 若已加入宗門且有任務，`sect_mission` 效用乘以 2.0
- 若境界卡關（突破失敗次數多），`retreat` 效用大幅提升

**返回格式**（必須與 LLM 版本一致）：
```python
{"action_name": "meditate", "params": {...}, "reason": "境界壓力高，選擇修煉"}
```

---

### 3.2 `long_term_objective` → 目標優先級引擎

**目標類型預定義**：

```python
GOAL_TYPES = [
    "BREAKTHROUGH_REALM",      # 突破境界
    "JOIN_SECT",               # 加入宗門
    "LEAVE_SECT",              # 離開宗門
    "SEEK_REVENGE",            # 復仇（仇人 relation < -70）
    "FIND_MASTER",             # 拜師
    "TRAIN_DISCIPLE",          # 收徒
    "ACCUMULATE_WEALTH",       # 積累靈石
    "ACQUIRE_TECHNIQUE",       # 習得功法
    "FORGE_WEAPON",            # 鑄造武器
    "GAIN_REPUTATION",         # 提升名望
    "FORM_ALLIANCE",           # 結交盟友
    "DOMINATE_REGION",         # 稱霸一方（高境界時）
]
```

**優先級評分**：

```python
def score_goal(goal_type, avatar, world) -> float:
    if goal_type == "BREAKTHROUGH_REALM":
        # 修為進度越接近突破點，分數越高
        return avatar.cultivation_progress * realm_pressure_factor(avatar.realm)
    if goal_type == "SEEK_REVENGE":
        # 有深仇（< -70）且實力優勢時
        enemies = [r for r in avatar.relations if r.friendliness < -70]
        return len(enemies) * 2.0 if can_win_against_enemies(avatar) else 0.0
    # ...
```

選出最高分目標，附上簡短文字描述（模板生成，非 LLM）。

---

### 3.3 `relation_resolver` / `relation_delta` → 公式引擎

**原版 LLM 邏輯**：給定互動描述，決定 friendliness 變化量（-6 ~ +6）。

**替換方案**：

```python
# 基礎 delta（config.yml 已有 fixed_deltas，這裡補充 LLM 模式的部分）
BASE_INTERACTION_DELTA = {
    "conversation":   {"min": -2, "max": 4},   # 對話通常正向
    "talk":           {"min": -1, "max": 3},
    "gift":           {"min": 2,  "max": 5},
    "spar":           {"min": -3, "max": 2},   # 切磋有輸贏
    "gathering":      {"min": -2, "max": 4},
    "random_minor_event": {"min": -1, "max": 2},
}

# 性格相容矩陣（影響 delta 方向偏移）
PERSONA_COMPATIBILITY = {
    ("正義", "邪惡"):    -2,   # 正邪不兩立
    ("謙遜", "傲慢"):    -1,
    ("俠義", "怯懦"):     1,   # 俠義對怯懦有包容
    ("好學", "好學"):     2,   # 同好加成
    ("貪財", "俠義"):    -1,
}
```

計算流程：
1. 取互動類型的 base 範圍，隨機一個值
2. 加上雙方性格相容度 modifier
3. 加上境界差 modifier（強者對弱者的輕視/尊重）
4. 加上近期事件 modifier（剛打架過扣分）
5. 裁剪到 `config.yml` 的 `social.relation.llm_delta.min/max`

---

### 3.4 `story_teller` / `interaction_feedback` / `backstory` → 詞庫組合模板

**設計理念**：類 Caves of Qud——不是隨機排列詞語，而是有語意結構的模板，詞庫填充其中的「可變槽位」。

#### 3.4.1 敘事模板

```python
# data/templates/narrative.py

COMBAT_WIN = [
    "{winner}祭出{technique}，一招制敵，{loser}敗下陣來。",
    "{winner}與{loser}酣鬥{n}招，終以{realm_adj}境界勝出。",
    "{loser}不敵{winner}，{retreat_desc}。",
]

COMBAT_LOSE = [
    "{loser}落敗，{injury_desc}，{loser}狼狽{retreat_desc}。",
    "{winner}一出手，{loser}便知不是對手，{retreat_desc}。",
]

CULTIVATION_BREAKTHROUGH = [
    "{avatar}閉關{n}月，終於{breakthrough_desc}，境界晉升至{new_realm}。",
    "{avatar}在{place}感悟天地靈氣，一鳴驚人，突破{new_realm}。",
]
```

**詞庫**（按修為/性格/種族分類）：

```python
# data/vocab/adjectives.py

REALM_ADJ = {
    "QI_REFINEMENT":       ["練氣初成", "蓄力待發"],
    "FOUNDATION_ESTABLISHMENT": ["築基圓滿", "根基穩固"],
    "CORE_FORMATION":      ["結丹有成", "道心堅毅"],
    "NASCENT_SOUL":        ["元嬰出竅", "神通廣大"],
}

PERSONA_ADJ = {
    "正義":  ["堂堂正正", "俠肝義膽"],
    "邪惡":  ["陰狡狠毒", "心狠手辣"],
    "謙遜":  ["溫文儒雅", "不露鋒芒"],
    "傲慢":  ["桀驁不馴", "目中無人"],
}

RETREAT_DESC = ["倉皇逃離", "負傷退走", "含恨而去", "忍辱認輸"]
```

#### 3.4.2 傳記模板

```python
# data/templates/backstory.py

TEMPLATES = [
    "{avatar}出身{origin}，{parents_desc}。自幼{childhood_desc}，"
    "{teen_event}，自此踏上修仙之路。",

    "{avatar}本是{origin}的{social_status}，"
    "{chance_event}，偶得{opportunity}，遂立志{ambition}。",
]

ORIGIN_POOL = {
    "mountain": ["深山僻村", "靈山腳下", "懸崖古寨"],
    "city":     ["繁華城市", "修仙坊市", "世家大宅"],
    "sect":     ["宗門後裔", "修仙世家", "名門望族"],
}
```

---

### 3.5 `nickname` → 成就詞庫拼接

**觸發條件**（與原版 `config.yml` 一致）：
- `major_event_threshold: 3`（大事件超過 3 次）
- `minor_event_threshold: 25`（小事件超過 25 次）

**外號生成規則**：

```python
# data/vocab/epithets.py

# 按「成就類型」分類的外號片段
KILL_EPITHETS = {
    "prefix": ["殺人", "血手", "閻羅", "斷魂"],
    "suffix": ["魔頭", "修羅", "刀客", "劍客"],
}

HEALING_EPITHETS = {
    "prefix": ["活死人", "妙手", "仁心"],
    "suffix": ["神醫", "聖手", "藥王"],
}

REALM_EPITHETS = {
    "NASCENT_SOUL_YOUNG": ["天驕", "少年元嬰", "驚世天才"],
    "CORE_FORMATION_OLD": ["百年老丹", "遲暮金丹"],
}

# 組合規則
def generate_nickname(avatar) -> str:
    category = determine_achievement_category(avatar)
    pool = KILL_EPITHETS if category == "combat" else HEALING_EPITHETS  # etc.
    pattern = random.choice(["prefix+suffix", "realm_title", "place+noun"])
    # ...
```

---

### 3.6 `sect_decider` → 宗門策略決策樹

**宗門狀態評估**：

```python
class SectState:
    strength: float      # 成員平均境界
    territory: int       # 地盤格數
    resources: int       # 靈石收入
    member_count: int    # 成員數
    morale: float        # 士氣（由近期事件決定）

STRATEGY_TREE = [
    # 條件 → 策略
    (lambda s: s.member_count < 3,                       "RECRUIT"),
    (lambda s: s.resources < 500,                        "CONSOLIDATE"),
    (lambda s: s.territory > 20 and s.resources > 2000,  "WAR"),
    (lambda s: s.morale < 0.3,                           "CONSOLIDATE"),
    (lambda s: s.strength > threshold_war,               "EXPAND"),
    (lambda _: True,                                      "TRAIN"),  # 預設
]
```

策略 → 具體行動映射：
- `RECRUIT`：降低入門要求，主動邀請遊蕩角色
- `CONSOLIDATE`：停止擴張，加強現有成員訓練
- `EXPAND`：派遣強力成員奪取附近地盤
- `WAR`：向關係最差的宗門宣戰
- `TRAIN`：增加修煉資源分配

---

### 3.7 `random_minor_event` / `sect_random_event` → 預定義事件表

```python
# data/templates/events.py

MINOR_EVENTS = [
    {
        "id": "treasure_found",
        "condition": lambda a, w: a.is_in_wilderness(),
        "effect": lambda a: a.gain_item("spirit_stone", 10),
        "template": "{avatar}在{place}意外發現一處靈石礦脈，得靈石{n}枚。",
    },
    {
        "id": "ambush",
        "condition": lambda a, w: a.realm < threshold and w.has_bandits_nearby(a),
        "effect": lambda a: a.take_damage(0.2),
        "template": "{avatar}遭人埋伏，雖僥倖脫身，卻受了些許傷勢。",
    },
    # ... 50+ 事件
]
```

---

## 四、Phase 0：全任務 Stub（最優先）

**目標**：讓遊戲先跑起來，每個 task 都返回一個最小合法值。

```python
# src/local_ai/dispatcher.py
STUBS = {
    "action_decision":         lambda i: {"action_name": "meditate", "params": {}},
    "long_term_objective":     lambda i: {"goal": "BREAKTHROUGH_REALM", "desc": "修煉突破"},
    "relation_resolver":       lambda i: {"delta_a_to_b": 0, "delta_b_to_a": 0, "reason": "平淡交流"},
    "relation_delta":          lambda i: {"delta": 0},
    "story_teller":            lambda i: {"story": f"{i.get('avatar_name', '修士')}繼續修煉。"},
    "interaction_feedback":    lambda i: {"feedback": "雙方寒暄幾句，無甚要事。"},
    "history_influence":       lambda i: {"influence": 0, "desc": "歷史平靜"},
    "backstory":               lambda i: {"backstory": "此人來歷不明，默默無聞。"},
    "random_minor_event":      lambda i: None,  # None = 不觸發事件
    "sect_random_event":       lambda i: None,
    "sect_random_event_reason": lambda i: {"reason": "形勢所迫"},
    "sect_decider":            lambda i: {"strategy": "TRAIN", "actions": []},
    "sect_thinker":            lambda i: {"thinking": "宗門平靜，無甚動盪。"},
    "nickname":                lambda i: None,  # None = 不生成外號
    "single_choice":           lambda i: {"choices": []},
    "custom_content_generation": lambda i: None,
}

def dispatch(task_name: str, infos: dict):
    handler = STUBS.get(task_name)
    if handler is None:
        return None  # fallback to LLM
    return handler(infos)
```

Phase 0 完成標準：跑 10 月模擬不崩潰。

---

## 五、實作優先級與時程估計

### 優先級排序（影響力 × 實作難度）

| 優先 | 任務 | 影響力 | 估計工時 |
|---|---|---|---|
| 1 | `action_decision` | ★★★★★ 決定 NPC 行為是否合理 | 3-5 天 |
| 2 | `relation_resolver/delta` | ★★★★ 決定人際關係是否有趣 | 1-2 天 |
| 3 | `long_term_objective` | ★★★★ 決定 NPC 行為方向性 | 1-2 天 |
| 4 | `story_teller / interaction_feedback` | ★★★ 決定敘事是否有趣 | 2-3 天（詞庫建立） |
| 5 | `sect_decider` | ★★★ 決定宗門是否有策略感 | 1-2 天 |
| 6 | `nickname` | ★★ 外號生成的成就感 | 0.5 天 |
| 7 | `backstory` | ★★ 角色背景深度 | 0.5 天 |
| 8 | `random_minor_event` | ★★ 世界豐富度 | 1-2 天（事件表） |
| 9 | 其餘 7 個任務 | ★ 邊緣功能 | 各 < 0.5 天 |

### 工時估計（從 Phase 0 到完整等價）

| Phase | 內容 | 估計工時 |
|---|---|---|
| Phase 0 | 全任務 Stub，遊戲可運行 | 0.5 天 |
| Phase 1 | Utility AI + 關係公式 + 目標系統 | 5-8 天 |
| Phase 2 | 詞庫建立 + 敘事模板 + 外號/傳記 | 4-6 天 |
| Phase 3 | 宗門 AI + 隨機事件表 | 2-3 天 |
| Phase 4 | 整合測試 + 行為對比 | 2-3 天 |
| **合計** | | **約 2-3 週** |

---

## 六、關鍵設計決策

### 決策 1：Shim Layer 而非重寫上層

**參照**: `analysis/cultivation-world-simulator/architecture/02_level2_modules.md:2.5`  
**理由**: 原版 20 相位的 Phase 代碼（`simulator_engine/phases/`）邏輯正確且已測試，動它風險高。只換底層的資料來源，不動業務編排。  
**代價**: 必須嚴格符合每個任務的 JSON 返回格式，任何格式不符都會導致上層解析失敗。

### 決策 2：Utility AI 而非行為樹

**理由**: 行為樹適合固定行為序列（如格鬥遊戲招式）；這裡的決策空間是「在 N 個可用動作中選一個」，效用評分更自然。且效用函數可以用資料驅動（YAML 表），比硬編碼行為樹易於擴充修仙世界的新動作。

### 決策 3：詞庫用 Python 常量而非 YAML

**理由**: 詞庫需要有條件的選取邏輯（如「若境界是元嬰才用這個形容詞」），YAML 難以表達條件；Python dict 直接可以加 lambda 條件，且不需要額外的載入機制。

### 決策 4：保留 LLM fallback 能力

**理由**: 若日後想讓某些任務（如 `custom_content_generation`）仍可選用 LLM，只需在 dispatcher 返回 `None` 即可回退原版流程。系統不破壞向後兼容性。

---

## 七、已知難點與風險

| 難點 | 說明 | 緩解方案 |
|---|---|---|
| `action_decision` 返回格式 | 需要研究原版 LLM prompt 返回的確切 JSON 結構 | Phase 0 先跑 debug log，觀察 infos 內容 |
| `infos` 內容不明 | 每個任務的 infos dict 鍵名不確定 | 讀 `simulator_engine/phases/` 相關代碼 |
| NPC 行為退化 | 沒有 LLM 後 NPC 可能全部選同一動作 | Utility AI 加入隨機擾動 ε |
| 詞庫中文語法 | 中文模板比英文複雜（量詞/虛詞） | 準備好初版詞庫後人工校對 |
| `single_choice` 格式 | roleplay 模式的選項生成格式複雜 | 最後階段處理，可先 stub 返回空選項列表 |
