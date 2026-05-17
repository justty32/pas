# 城市架構深化：人口與情感系統 (源碼剖析)

在 Freeciv 中，城市的產出不僅取決於地形，還深受「人口心情」的直接影響。若城市陷入暴動 (Disorder)，所有產能將會停擺。為了精確模擬各種政策、建築與軍事行為對民眾的影響，Freeciv 實作了一套具備「階段追溯性」的情感矩陣。

本文件深入剖析 `common/city.c` 中關於人口情感的底層計算流水線。

## 1. 核心資料結構：情感矩陣
在 `struct city` 中，人口心情由以下矩陣記錄：
```c
citizens feel[CITIZEN_LAST][FEELING_LAST];
```
- **第一維 (`CITIZEN_LAST`)**: 區分四種狀態：`HAPPY` (快樂), `CONTENT` (平靜), `UNHAPPY` (不滿), `ANGRY` (憤怒)。
- **第二維 (`FEELING_LAST`)**: 記錄心情變化的 6 個處理階段。這保證了每次 UI 顯示與 AI 決策都能清楚知道「是哪個因素讓民眾不高興」。

---

## 2. 情感計算流水線 (The Happiness Pipeline)
每當城市更新 (`city_refresh_from_main_map`)，系統會依序執行以下 6 個函數，將前一個階段的結果複製並修改到下一個階段。

### 階段 1：基礎心情 (`citizen_base_mood`)
這是在沒有任何外在影響下的天生心情。
- **規則**: 沒有人天生是快樂的 (`happy = 0`)。
- **運算邏輯**:
    1. 從玩家帝國層級讀取 `base_content` (帝國規模越小，天生平靜的人越多) 與 `base_angry`。
    2. 扣除專家 (Specialists 不受心情影響)。
    3. 剩下的平民，根據帝國規模分配為 `CONTENT` 與 `ANGRY`。
    4. 既非平靜、也非憤怒的剩餘人口，全部歸類為 `UNHAPPY`。

### 階段 2：奢華度分配 (`citizen_happy_luxury`)
將城市產出的 `O_LUXURY` 投入消費。
- **規則**: 每轉化一個階級，消耗 `game.info.happy_cost` (通常為 2 點奢華度)。
- **升級順序**:
    1. 優先消除憤怒: `ANGRY` $\rightarrow$ `UNHAPPY` (消耗 1 份)。
    2. 提升平靜: `CONTENT` $\rightarrow$ `HAPPY` (消耗 1 份)。
    3. 大幅提升: `UNHAPPY` $\rightarrow$ `HAPPY` (消耗 2 份，雙倍成本)。
    4. 剩餘資源: `UNHAPPY` $\rightarrow$ `CONTENT` (消耗 1 份)。

### 階段 3：建築安撫 (`citizen_content_buildings`)
處理具備 `EFT_MAKE_CONTENT` 效果的建築（如：神廟、競技場）。
- **規則**: 建築只能讓人「平靜」，不能讓人「快樂」。
- **運算邏輯**: 優先將 `ANGRY` $\rightarrow$ `UNHAPPY`，若還有剩餘效果則 `UNHAPPY` $\rightarrow$ `CONTENT`。

### 階段 4：國籍衝突 (`citizen_happiness_nationality`)
這是 Freeciv 非常擬真的部分。當城市被佔領後，內部會存在外國僑民。
- **規則**: 如果擁有者目前正與僑民的母國交戰，會觸發 `EFT_ENEMY_CITIZEN_UNHAPPY_PCT`。
- **降級順序**: 根據開戰的僑民比例，強制將 `CONTENT` $\rightarrow$ `UNHAPPY`，甚至 `HAPPY` $\rightarrow$ `UNHAPPY`。這種設計使得吞併敵國城市後極易爆發內亂。

### 階段 5：軍隊影響 (`citizen_happy_units`)
軍事行動對國內的雙面刃影響。
- **正面：戒嚴 (Martial Law)**: 
    - 駐紮在城內的軍事單位會提供 `EFT_MAKE_CONTENT`，將 `ANGRY` $\rightarrow$ `UNHAPPY` $\rightarrow$ `CONTENT`。這在專制體制下是維持治安的主要手段。
- **負面：厭戰 (Military Away)**:
    - 在共和或民主體制下，離開城市的攻擊性單位會產生 `unit_happy_upkeep`。這會強制將 `HAPPY` 或 `CONTENT` 降級為 `UNHAPPY`。

### 階段 6：奇觀與最終結算 (`citizen_happy_wonders`)
處理具備全球/大陸效果的奇觀（如：巴哈大教堂、女權運動）。
- **特效 `EFT_MAKE_HAPPY`**: 可以直接將 `CONTENT` $\rightarrow$ `HAPPY`。
- **特效 `EFT_NO_UNHAPPY`**: 極端強大的效果，強制將所有 `UNHAPPY` 與 `ANGRY` 歸零並轉為 `CONTENT`。

---

## 3. 暴動判定與結果
在 6 個階段計算完畢後，系統會檢查 `FEELING_FINAL` 的數據。
- **慶典 (Rapture)**: 若沒有 `UNHAPPY`/`ANGRY`，且 `HAPPY` 數量大於等於總人口的一半，城市進入慶典。
- **暴動 (Disorder)**: 若 `UNHAPPY` + $2 \times$ `ANGRY` 的數量超過 `HAPPY`，城市陷入暴動。
- **暴動懲罰**: `unhappy_penalty` 枚舉會發揮作用，通常會導致城市的 `O_SHIELD` (產能) 淨產出歸零，也就是所謂的「罷工」。

## 4. 工程見解
Freeciv 捨棄了簡單的「總滿意度 = 正面分數 - 負面分數」這種容易產生漏洞的設計。

相反，它透過**逐級升降轉換** (例如 `angry--`, `unhappy++`) 的狀態機模式，確保了：
1. **人口守恆**: 無論怎麼轉換，人口總數永遠不變，避免了除錯時的數量丟失。
2. **邊際效益遞減**: 奢華度提升 `UNHAPPY` 到 `HAPPY` 需要雙倍成本，這在數學上防止了後期金錢過多導致的無限溢出。
3. **優先級明確**: 戒嚴 (`FEELING_MARTIAL`) 永遠在建築 (`FEELING_EFFECT`) 之後計算，確保了政策的優先順序在程式碼層面被嚴格執行。
