# 敘事系統規格 — 詞庫組合模板

> 處理：story_teller、interaction_feedback、backstory、
>         random_minor_event、sect_random_event、sect_thinker、nickname

---

## 一、設計哲學：Caves of Qud 式敘事

**不是** Madlib（純填充）——那樣文字生硬。  
**而是** 有語意結構的**模板集合**，每個模板本身就是流暢的句子，只有特定槽位是可替換的。

```python
# Bad（純 Madlib）:
"{adj}{noun}的{person}在{place}做了{action}這件事"

# Good（語意模板）:
"{winner}出手如電，三招之內便將{loser}打得{defeat_desc}，{loser}只得{retreat_desc}。"
```

關鍵原則：
1. **每個模板本身就是完整的句子**，不依賴填充內容來決定語法
2. **槽位只替換「名詞片語」**，不替換動詞/助詞（避免中文語法破壞）
3. **詞庫按語境分類**，同一「敗走」可能用「含恨退去」或「倉皇逃離」，根據對戰雙方性格選擇

---

## 二、模板槽位類型

| 槽位記法 | 類型 | 例子 |
|---|---|---|
| `{avatar}` | 角色名（直接插入） | 「李逍遙」 |
| `{realm_adj}` | 境界形容詞 | 「練氣後期」、「元嬰大圓滿」 |
| `{persona_adj}` | 性格形容詞 | 「陰險狡詐」、「堂堂正正」 |
| `{technique}` | 功法/招式名（隨機或角色實際功法） | 「烈火掌法」 |
| `{n}` | 數字（上下文決定範圍） | `random.randint(3, 9)` |
| `{place}` | 地名（取 avatar.location 或鄰近區域） | 「靈峰山脈」 |
| `{defeat_desc}` | 敗陣描述詞庫 | 詞庫 `DEFEAT_DESC` |
| `{retreat_desc}` | 撤退描述詞庫 | 詞庫 `RETREAT_DESC` |

---

## 三、事件類型與模板數量規劃

| 事件類型 | 模板數量目標 | 備注 |
|---|---|---|
| 戰鬥（勝/平/敗） | 各 15 條 | 按性格差異選取不同風格 |
| 切磋（友好） | 10 條 | |
| 修煉突破 | 15 條 | 按境界分組 |
| 突破失敗（天劫/心魔） | 10 條 | |
| 對話/交流 | 12 條 | |
| 贈禮 | 8 條 | |
| 告白（接受/拒絕） | 各 8 條 | |
| 結拜 | 8 條 | |
| 雙修 | 8 條 | |
| 傳授功法 | 8 條 | |
| 死亡 | 15 條 | 按死因分組 |
| 奇遇/天災 | 20 條 | |
| 宗門任務完成/失敗 | 各 8 條 | |
| 煉丹成功/失敗 | 各 6 條 | |
| 鑄造武器 | 8 條 | |
| **合計** | **~200 條** | |

---

## 四、具體模板示例

### 4.1 戰鬥系列

```python
# data/templates/narrative.py

COMBAT_WIN = [
    # 技術勝
    "{winner}施展{technique}，劍走偏鋒，三兩招之間便破了{loser}的防禦，{loser}只得{retreat_desc}。",
    "{winner}與{loser}纏鬥{n}個回合，憑藉{realm_adj}的境界壓制，{loser}終究不敵。",
    "一聲輕嘆，{loser}承認敗局，{winner}收招而立，{loser}{retreat_desc}。",
    
    # 碾壓勝（境界差距大）
    "{winner}只出了三分力，{loser}便已疲態盡顯，不得不{retreat_desc}。",
    "{loser}拼盡全力，卻在{winner}面前不過是螳臂當車，{winner}輕描淡寫便定了勝負。",
    
    # 辛苦勝
    "{winner}與{loser}苦戰{n}個時辰，傷痕累累，卻以微弱優勢取得勝利。",
    "雙方均已精疲力竭，{winner}咬牙撐過最後一刻，{loser}終於{retreat_desc}。",
]

COMBAT_LOSE = [
    "{avatar}被對方一掌震飛丈許，含恨{retreat_desc}。",
    "雖拼盡全力，{avatar}終究不敵，{defeat_desc}，{retreat_desc}。",
    "{avatar}深知今日不敵，強撐著{retreat_desc}，暗暗咬牙，銘記此辱。",  # 性格：復仇心強
]

COMBAT_DRAW = [
    "雙方鬥了{n}個回合，不分勝負，各自罷手。",
    "{avatar_a}與{avatar_b}交手一番，發現實力相當，相視一笑，各自離去。",
]
```

### 4.2 修煉突破系列

```python
CULTIVATION_BREAKTHROUGH = {
    "QI_REFINEMENT_TO_FOUNDATION": [
        "{avatar}在{place}盤膝打坐，靈氣如潮水般湧入，{n}日後驀然突破，正式邁入築基境。",
        "積累多時，{avatar}終於水到渠成，踏入築基，氣息隱隱變化，不可同日而語。",
    ],
    "FOUNDATION_TO_CORE": [
        "{avatar}閉關{n}月，以靈石千枚輔助，終於感悟結丹之機，一聲轟響，金丹成形。",
        "多年積累，{avatar}在天地靈機大開之際抓住時機，金丹破體而出，境界驟升。",
    ],
    "CORE_TO_NASCENT": [
        "天地變色，靈壓四溢，{avatar}歷經{n}道天劫，最終神魂出竅，元嬰成形，震驚四方。",
        "{avatar}在{place}閉關三年，元嬰破殼，靈識大開，已非昔日修士可比。",
    ],
}

CULTIVATION_FAIL = [
    "{avatar}衝擊境界失敗，丹田受創，需靜養{n}月方能恢復。",
    "功虧一簣，{avatar}突破不成，心魔乘虛而入，境界不升反降，面色鐵青。",
    "{avatar}雖全力以赴，卻終究差了一口氣，只得退出閉關，再做籌謀。",
]
```

### 4.3 身世傳記系列

```python
# data/templates/backstory.py

ORIGIN_TEMPLATES = [
    # 寒門出身
    "{avatar}出身{origin_place}的貧寒農家，父母{parents_desc}，自幼便立志{ambition}。"
    "{childhood_event}，機緣巧合下得遇{opportunity}，自此踏入修仙之門。",

    # 世家出身
    "{avatar}乃{origin_place}{family_title}後裔，生來便有{root_adj}靈根，年幼時已展露{talent_desc}。"
    "然而{setback}，{avatar}不得不{response}，磨礪之中，修為日益精進。",

    # 孤兒出身
    "{avatar}幼年孤苦，在{place}流離失所，{rescue_event}。"
    "承蒙{benefactor}收留，習得{skill}，方有今日之成就。",

    # 宗門弟子出身
    "生於{sect_name}道統之中，{avatar}自幼耳濡目染，{training_desc}。"
    "{turning_event}，令其對修仙之道有了更深的領悟，立下{ambition}之志。",
]

ORIGIN_PLACES = {
    "wilderness": ["荒山野嶺", "邊陲小城", "窮鄉僻壤", "深山古寨"],
    "city":       ["繁華坊市", "靈氣豐沛的修仙重鎮", "古老城池"],
    "sect":       ["名門宗派之內", "老牌修仙宗門腳下"],
}

CHILDHOOD_EVENTS = [
    "年幼時曾被妖獸追殺，幸得高人相救",
    "偶然在山中撿到一枚神秘玉簡，其中隱藏功法殘篇",
    "目睹家人遭人欺壓，立誓要出人頭地",
    "拜入{sect_name}時因根骨出眾受到長老青睞",
]
```

---

## 五、詞庫設計

### 5.1 形容詞詞庫

```python
# data/vocab/adjectives.py

REALM_PRESSURE_ADJ = {
    # 用於描述快突破的狀態
    "high":   ["蓄勢待發", "呼之欲出", "水到渠成", "箭在弦上"],
    "medium": ["穩步前進", "功候將近", "根基漸厚"],
    "low":    ["任重道遠", "尚需磨礪", "初窺門徑"],
}

COMBAT_STYLE_ADJ = {
    "aggressive": ["凌厲", "勢如破竹", "猛烈異常", "排山倒海"],
    "defensive":  ["滴水不漏", "以靜制動", "後發制人"],
    "tricky":     ["詭異莫測", "神出鬼沒", "出奇制勝"],
    "steady":     ["沉穩老練", "不急不躁", "老謀深算"],
}

DEFEAT_DESC = [
    "跌落丈外", "連退數步", "吐血倒地", "盔甲盡碎",
    "靈氣散亂", "神識動盪", "驚出冷汗", "面色蒼白",
]

RETREAT_DESC = [
    "倉皇退走", "含恨離去", "悻悻而返", "負傷潛逃",
    "拱手認輸", "低頭認敗", "扭頭離去", "忍辱吞聲",
]
```

### 5.2 外號詞庫

```python
# data/vocab/epithets.py

# 按成就類型分組
COMBAT_EPITHETS = {
    # (前綴, 後綴) 或完整外號
    "high_kills": [
        ("殺人", "魔頭"), ("血手", "劍客"), ("閻羅", "再世"),
        ("煞", "刀"), "修羅降世", "千人斬",
    ],
    "strong_power": [
        ("無敵", "拳"), ("天下", "第一"), "萬夫莫敵",
        ("劍破", "蒼穹"),
    ],
    "undefeated": [
        "百戰不敗", ("不敗", "劍神"), "戰神臨世",
    ],
}

CULTIVATION_EPITHETS = {
    "young_genius": [
        "曠世天驕", ("百年難遇", "天才"), "少年劍仙",
        ("璀璨", "新星"), "後起之秀",
    ],
    "high_realm_old": [
        ("老而不死", "是為賊"), "長壽真人", "歲月長河",
    ],
    "speed_cultivator": [
        "修煉如龍", "一日千里", ("破境", "狂人"),
    ],
}

CRAFT_EPITHETS = {
    "alchemist": [
        "丹王", "煉丹宗師", ("百草", "先生"), "妙手仙師",
    ],
    "blacksmith": [
        "鑄劍大師", "器道宗師", ("萬兵", "祖師"),
    ],
}

# 組合規則：根據角色的 notable_deeds 決定用哪組詞庫
def select_epithet_category(avatar) -> str:
    if avatar.kill_count >= 50:
        return "COMBAT_HIGH_KILLS"
    if avatar.breakthrough_speed_percentile >= 90:
        return "CULTIVATION_YOUNG_GENIUS"
    if avatar.alchemy_skill >= HIGH_THRESHOLD:
        return "CRAFT_ALCHEMIST"
    # ... 更多條件
    return "COMBAT_STRONG_POWER"  # 默認
```

### 5.3 宗門思考詞庫

```python
# 宗門年度思考（sect_thinker 任務）

SECT_THINKING_TEMPLATES = {
    "EXPANDING": [
        "{sect_name}近年勢力蒸蒸日上，{territory_change}塊地盤已入我囊中。長老們議定，明年繼續擴張，{target_desc}不日將成囊中之物。",
        "本宗近年捷報頻傳，成員境界普遍提升，長老商議決定主動出擊，{strategy_desc}。",
    ],
    "CONSOLIDATING": [
        "元氣需得休養，{sect_name}決定休養生息，加強弟子訓練，靜待時機。",
        "四方局勢複雜，{sect_name}暫守不攻，廣納賢才，以厚積薄發。",
    ],
    "AT_WAR": [
        "與{enemy_sect}的戰事持續，{sect_name}已戰{n}月，雖有消耗，但宗門上下士氣高昂，誓要一決高下。",
        "連番征戰，{sect_name}損失{n}名修士，長老們在是否繼續開戰上意見分歧。",
    ],
    "RECRUITING": [
        "{sect_name}人丁單薄，急需充實門派，近期廣發英雄帖，廣招有志之士。",
        "長老們一致認為，壯大門派實力從提攜後進開始，本年主要精力放在招募和培養弟子上。",
    ],
}
```

---

## 六、文字生成引擎

```python
# src/local_ai/narrative.py

import random
from .data.templates import narrative as N
from .data.templates import backstory as B
from .data.vocab import adjectives as ADJ, epithets as E

class NarrativeEngine:
    
    def generate_combat_story(self, winner, loser, battle_context: dict) -> str:
        """生成戰鬥敘事"""
        # 根據境界差距選模板集合
        realm_gap = get_realm_gap(winner, loser)
        if realm_gap >= 2:
            pool = N.COMBAT_WIN_CRUSHING  # 碾壓勝
        elif battle_context.get("close_battle"):
            pool = N.COMBAT_WIN_CLOSE     # 險勝
        else:
            pool = N.COMBAT_WIN           # 普通勝
        
        template = random.choice(pool)
        
        return template.format(
            winner=winner.name,
            loser=loser.name,
            technique=self._pick_technique(winner),
            n=random.randint(3, 15),
            realm_adj=self._pick_realm_adj(winner),
            defeat_desc=random.choice(ADJ.DEFEAT_DESC),
            retreat_desc=random.choice(ADJ.RETREAT_DESC),
        )
    
    def generate_backstory(self, avatar) -> str:
        """生成角色背景故事"""
        origin_type = self._classify_origin(avatar)
        templates = B.ORIGIN_TEMPLATES_BY_TYPE[origin_type]
        template = random.choice(templates)
        
        return template.format(
            avatar=avatar.name,
            origin_place=random.choice(B.ORIGIN_PLACES[origin_type]),
            parents_desc=self._parents_desc(avatar),
            ambition=self._ambition_by_persona(avatar),
            childhood_event=random.choice(B.CHILDHOOD_EVENTS),
            opportunity=self._opportunity_by_root(avatar),
        )
    
    def generate_nickname(self, avatar) -> str | None:
        """生成外號（若條件滿足）"""
        category = E.select_epithet_category(avatar)
        pool = E.EPITHET_POOLS.get(category, [])
        if not pool:
            return None
        
        choice = random.choice(pool)
        if isinstance(choice, tuple):
            return choice[0] + avatar.name[-1] + choice[1]  # 「殺人李x魔頭」
        return choice  # 完整外號
    
    def _pick_technique(self, avatar) -> str:
        """優先用角色實際功法，否則用通用名"""
        if avatar.techniques:
            return random.choice(avatar.techniques).name
        return random.choice(["雷霆掌法", "御劍術", "靈力拳", "五行指"])
```

---

## 七、詞庫規模估計

| 詞庫 | 條目數目標 |
|---|---|
| 形容詞（境界/性格/戰鬥風格） | 各 15~25 條 |
| 敗陣/撤退描述 | 各 20 條 |
| 死亡描述 | 30 條（按死因） |
| 地名形容詞 | 30 條 |
| 機遇描述 | 20 條 |
| 童年事件 | 25 條 |
| 外號片段（前/後綴各類） | 各 15~30 條 |
| **事件模板總計** | ~200 條 |
| **傳記模板** | 12 條 |

詞庫建立是這個專案的**主要人力投入**（需要大量人工創作修仙風格的文字），也是決定遊戲敘事品質的關鍵。
