# PROMPT_TEMPLATES：給執行模型下 prompt 的範本

> 本文是給**規劃者（你自己）**用的 prompt 撰寫手冊。
> 指派任務時，從 `TASKS.md` 挑任務，再用下面的範本組裝 prompt 貼給執行模型。
> 範本不要逐字照抄；挑合適的骨架後替換 `<...>` 即可。

---

## 0. 通用原則（每個 prompt 都要做）

### 0.1 告知角色與邊界
執行模型不知道整個專案脈絡。每個 prompt 開頭都要點明：

- 專案位置（絕對路徑）。
- 本任務是哪個 Milestone 的哪個任務。
- 它**不要**做什麼（避免擅自擴張）。

### 0.2 只給它要讀的檔案
不要讓執行模型自己去翻目錄猜規格。直接列出 2-3 個要讀的絕對路徑。

### 0.3 明確驗收條件
最後用「完成後你要回報 X」結尾。X 必須是可觀察的結果（印出什麼、按下什麼有什麼反應）。

### 0.4 不要讓它改契約
若任務涉及 `GameEvent` / `PlayerAction` / 三方法簽章，加一句：「契約欄位以 `00_master_guide.md` 為準，不得擅自增減欄位」。

### 0.5 語言
執行模型通常也是繁體中文回覆。Prompt 用繁體中文即可。

---

## 1. 範本 A：新元件實作（M1 及之後常用）

用於 `TASKS.md` 中「新建一個 autoload / 節點」類的任務。

```
你是執行模型，負責完成一項具體的 Godot 前端實作任務。

【專案位置】
/home/lorkhan/repo/pas/projects/<new_project_dir>   # 我們的目標專案
/home/lorkhan/repo/pas/projects/godot-open-rpg      # 素材來源（唯讀）

【本次任務】
任務 ID：<T1.3>
任務名稱：<改造 Gamepiece 節點>

【先讀這兩份文件】
1. /home/lorkhan/repo/pas/analysis/godot-open-rpg/target/00_master_guide.md
   （重點看「§7 Gamepiece 規格」）
2. /home/lorkhan/repo/pas/analysis/godot-open-rpg/target/01_extraction_and_modification_guide.md
   （重點看 Gamepiece 章節）

【交付】
建立 /home/lorkhan/repo/pas/projects/<new_project_dir>/src/field/gamepieces/gamepiece.gd，規格：
- 繼承 Node2D（不是 Path2D）
- 必要屬性：entity_id (int)、direction (Directions.Points)、animation (GamepieceAnimation)
- 必要方法：
  - move_to_cell(cell: Vector2i) -> void：用 Tween（0.2s）移動，await 結束
  - play_animation(name: StringName, wait: bool) -> Variant

【限制】
- 不要動任何 autoload。
- 不要修改 godot-open-rpg 專案（那是唯讀素材）。
- 欄位名、方法簽章照規格寫死，不自行改名。

【完成後請回報】
1. 建立了哪些檔案（絕對路徑）
2. Gamepiece 的程式碼片段
3. 如何驗證它能動（例：場景掛上手動呼叫 move_to_cell 看 Tween）
```

---

## 2. 範本 B：從 godot-open-rpg 提取與改造

用於 `TASKS.md` 的 M0 複製素材類任務，或後續要從源專案借用某段邏輯時。

```
你是執行模型，負責從 godot-open-rpg 提取素材並改造。

【專案位置】
源：/home/lorkhan/repo/pas/projects/godot-open-rpg       （唯讀）
目標：/home/lorkhan/repo/pas/projects/<new_project_dir>

【本次任務】
任務 ID：<T0.2>
從源專案複製以下檔案到目標專案的對應路徑：
<列出來源路徑 → 目標路徑的表>

【改造規則】
- 路徑保持一致（src/field/... 對應到 src/field/...）
- 若有 class_name 衝突，保留原名
- 若有 preload 的路徑，改為新專案的路徑
- 不改邏輯，只改路徑

【先讀這份文件確認提取清單】
/home/lorkhan/repo/pas/analysis/godot-open-rpg/target/00_master_guide.md §1

【限制】
- 不要複製列表以外的檔案。
- 不要重構、不要重新命名。
- 遇到 preload 失效時，修正路徑但不重寫檔案內容。

【完成後請回報】
1. 複製了哪些檔案
2. 修改過的 preload 路徑列表
3. 在 Godot 編輯器打開專案，是否有紅字錯誤
```

---

## 3. 範本 C：寫 Mock GameEngine

用於 M1-M7 每個階段要擴充 mock 行為的任務（T1.6、T2.3、T3.2、T4.1、T5.2、T6.2、T7.2）。

```
你是執行模型，要擴充 GDScript 版 Mock GameEngine。

【專案位置】
/home/lorkhan/repo/pas/projects/<new_project_dir>

【本次任務】
任務 ID：<T2.3>
當前 Milestone：<M2 訊息日誌 + 狀態列>
要做的擴充：<玩家 MOVE 後追加 LOG_MESSAGE 與 STATS_UPDATE>

【先讀這兩份文件】
1. /home/lorkhan/repo/pas/analysis/godot-open-rpg/target/00_master_guide.md（§4 事件表、§5 動作表、§10 該 Milestone 的驗收）
2. 當前的 mock：/home/lorkhan/repo/pas/projects/<new_project_dir>/src/mock/mock_game_engine.gd

【交付】
修改 mock_game_engine.gd：
- 在 submit_action 處理 MOVE 的分支裡，於原本事件之後追加：
  - LOG_MESSAGE{ text: "你往<方向>走了一步", category: "movement" }
  - STATS_UPDATE{ data: { hp: 當前hp - 1 } }
- 內部需記住當前 hp 值。

【契約限制】
事件欄位以 00_master_guide.md §4 為準，不得增加欄位。

【完成後請回報】
1. 變更後的完整 submit_action 程式碼
2. 執行遊戲，按方向鍵 3 次，截圖日誌與 HP 欄位
```

---

## 4. 範本 D：Debug / 驗收未過

當規劃者發現任務交付不合驗收時使用。

```
你剛完成的任務 <T1.6 Mock GameEngine (M1)> 未通過驗收。

【問題現象】
<描述具體現象：例如「按方向鍵玩家沒有移動，console 印出了 submit_action 但 tick 沒回傳 ENTITY_MOVE」>

【你該做的事】
1. 先讀 /home/lorkhan/repo/pas/analysis/godot-open-rpg/target/00_master_guide.md §10 M1 驗收條件。
2. 不要改任何驗收不要求的地方。
3. 找到根因，告訴我是哪一行有問題、為什麼會造成這個現象。
4. 提出最小修改。

【限制】
- 不要重寫整個檔案。只改有問題的部分。
- 不要為了讓它跑通而偷偷跳過某個事件。
- 若你認為規格本身有矛盾，停下來問我，別自己決定。

【完成後請回報】
1. 根因說明
2. 最小 diff
3. 再次執行的結果
```

---

## 5. 範本 E：純文件閱讀（不寫碼）

少數任務只需要讀規格後確認某件事。例：「列出 M3 會用到的所有 GameEvent」。

```
你這次不需要寫程式，只需要閱讀文件回答問題。

【請閱讀】
/home/lorkhan/repo/pas/analysis/godot-open-rpg/target/00_master_guide.md

【請回答】
<具體問題，例如「M3 Milestone 中會用到哪些 GameEvent？列出事件名與用途。」>

【限制】
- 只根據文件內容回答，不要臆測。
- 若文件沒提到，直接說「文件中未說明」。
- 不要建議修改文件。
```

---

## 6. 組裝 prompt 時的檢查清單

貼給執行模型前，依序確認：

- [ ] 專案位置寫了絕對路徑
- [ ] 任務 ID 對得上 `TASKS.md`
- [ ] 要讀的文件不超過 3 份
- [ ] 交付物具體（檔案路徑、類別名、方法簽章）
- [ ] 有「不要做 X」的限制
- [ ] 有明確驗收條件
- [ ] 若涉及契約，有「契約以 00_master_guide.md 為準」的聲明

---

## 7. 常見陷阱（過去觀察到的）

### 7.1 執行模型自行擴張欄位
- 現象：GameEvent 多了一個規格沒有的欄位。
- 對策：Prompt 明寫「欄位以 00_master_guide.md §4 為準」。

### 7.2 把後端邏輯寫進前端
- 現象：Gamepiece 裡出現「檢查是否撞牆」這種規則判斷。
- 對策：Prompt 加「前端不做規則判斷，撞牆與否由後端決定並送回 LOG_MESSAGE」。

### 7.3 一次做多個任務
- 現象：被指派 T1.3，卻順手把 T1.4 也做了，結果風格不一致。
- 對策：Prompt 加「本次只做 T<X>，其他任務不要碰」。

### 7.4 忘記註冊到 Autoload
- 現象：建立了 `DisplayAPI.gd` 但沒加到 `project.godot` 的 Autoload 區塊。
- 對策：交付條目加「在 project.godot 註冊為 autoload」。

### 7.5 用 Path2D 而不是 Tween
- 現象：Gamepiece 還沿用 godot-open-rpg 的 Path2D 連續移動。
- 對策：Prompt 加「移動用 Tween 跳格 + await，不用 Path2D」。

---

## 8. 當執行模型說「完成」時，規劃者該做的事

1. **讀它回報的程式碼片段**，不要直接相信它說的結果。
2. **親自跑 Godot 專案**，執行該 Milestone 的驗收條件。
3. **檢查契約欄位**：有沒有多欄位、少欄位、欄位型別錯誤。
4. **查它有沒有碰不該碰的檔案**：用 `git status` / `git diff`。
5. 通過 → 標記 `TASKS.md` 該任務完成，指派下一個。
6. 未通過 → 用範本 D 繼續 debug。

---

## 9. 何時更新本文件

- 發現某類 bug 反覆出現 → 加進 §7 常見陷阱。
- 新增一種任務類型（規格裡沒有的工作流程）→ 加新範本。
- 執行模型的行為模式改變 → 更新通用原則。
