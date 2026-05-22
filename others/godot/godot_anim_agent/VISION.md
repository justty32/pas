# AI 動畫代理人：設計構想

## 核心問題

動作編輯耗時且需要大量反覆調整。傳統流程：人工逐幀調整 → 在編輯器預覽 → 再調整。
目標：讓 AI agent 接手繁瑣的數值調整，人只負責意圖層面的指示。

---

## Phase 1：基礎讀寫工作流程

**前提**：Godot 的 `.tres` / `.animlib` 動畫資源是純文字格式，可直接讀寫。

**流程**：

```
使用者在 Godot 編輯器中製作動畫雛形（幾個關鍵幀）
    ↓
存檔 → .tres / .animlib 文字檔
    ↓
開啟 Claude Code session，指向動畫檔案
    ↓
Agent 讀取 + 輸出摘要（哪些骨骼、時間點、數值範圍）
    ↓
使用者給出指示（CLI 直接輸入 或 提供 text 描述）
    ↓
Agent 修改 .tres 檔案
    ↓
使用者在 Godot 重新載入場景，預覽結果
    ↓
重複迭代
```

**使用者指示的形式**：
- CLI 直說：「把出拳速度加快 30%，在 0.1s 達到最大角度」
- 文字文件：描述動作的風格或參考（「像蝴蝶拳，柔和快速」）
- 數值直接指定：「UpperArm 在 0.15s 時 rotation 要到 1.8 rad」

---

## Phase 2：程序生成與動作組合

### 2a. 簡單程序生成（直接調整 Node 屬性）

最基礎：依據出拳目標位置，用反向運動學計算骨骼旋轉，直接在 GDScript 中操作 `Bone2D.rotation`。
這不需要 AI，純數學即可。

### 2b. 複雜連串動作的 AI 組合

目標：給出一個自然語言動作描述，agent 能自動：

1. **解構**：把「迅速閃避出殘影，之後跳躍下劈」拆成子動作列表
2. **查詢動畫庫**：對應到現有基礎動畫（dodge, jump, down-slash）
3. **組合排序**：決定時序，插入過渡幀
4. **銜接修正**：
   - 檢查銜接點各骨骼狀態是否連續
   - 必要時插入 cross-fade blend 或修改 AnimationTree
   - 「殘影」效果 → 觸發 shader/後製，需動到 GDScript
5. **輸出**：修改後的 `.animlib` + 可能修改的 `.gd` 腳本

### 2c. 動畫 Metadata 系統（關鍵基礎設施）

為讓 Phase 2 可靠運作，每個基礎動畫需要旁置一份 metadata：

```json
{
  "name": "upper_cut",
  "tags": ["attack", "upper_body", "air_ok"],
  "entry_frame": 0,
  "exit_frame": 12,
  "exit_velocity": { "UpperArm": 0.0, "ForeArm": -0.5 },
  "root_motion_delta": { "x": 0.0, "y": -8.0 },
  "compatible_after": ["dash", "idle", "crouch"],
  "compatible_before": ["landing", "idle", "any_ground"]
}
```

Agent 做組合時先查 metadata 配對，不是靠猜骨骼狀態。

---

## 技術挑戰

| 挑戰 | 說明 | 解法 |
|------|------|------|
| 銜接點狀態一致性 | A 動畫結束與 B 動畫開始的骨骼位置/速度可能不連續 | Metadata + cross-fade blend |
| 根位移連續性 | 角色在世界空間的位置需要連貫 | 追蹤 root motion delta |
| 視覺特效整合 | 殘影、衝擊波等是 shader，不在動畫資料裡 | 動畫事件 (method track) 觸發 GDScript |
| Godot `.tres` 格式複雜度 | AnimationLibrary 巢狀 sub_resource，值類型多樣 | anim_inspector.py 做格式轉換 |

---

## 3D 版本的差異

核心概念（Phase 1 讀寫、Phase 2 組合）在 3D 完全適用，差異在資料格式與 track 類型。

### 資源格式

| 面向 | 2D | 3D |
|-----|----|----|
| 動畫儲存 | `.tres` / `.animlib` | `.animlib`（同）；mesh + skeleton 在 `.glb` |
| Bone2D track | `position: Vector2`, `rotation: float` | `position: Vector3`, `rotation: Quaternion` |
| Root motion | 2D position 偏移 | 3D 根骨骼 transform 偏移 |
| 模型來源 | 自建 Sprite2D 樹 | Blender → `.glb` 導入，包含 AnimationLibrary |

### `.glb` 動畫導入

Blender 匯出 `.glb` 時可以包含多個 Action（動畫片段），Godot 導入後自動放進 AnimationLibrary。
Agent Phase 1 要能讀取這些動畫，需要處理 `.glb` 或 Godot 導入後產生的 `.animlib`。

建議 Phase 1 workflow：
1. 在 Godot 編輯器把 `.glb` 動畫匯出成獨立 `.animlib` 文字檔
2. Agent 對 `.animlib` 做讀寫（同 2D 流程）
3. 修改完匯回場景

### Root Motion（3D 更重要）

3D 中 root motion 是讓角色在世界空間自然移動的關鍵（避免滑步）。
Metadata 的 `root_motion_delta` 在 3D 需擴展為 Vector3：

```json
"root_motion_delta": { "x": 0.2, "y": 0.0, "z": 0.0 }
```

AnimationTree 的 `root_motion_track` 需指向根骨骼的 position track。

### Quaternion Interpolation

3D 骨骼旋轉用 Quaternion，不是 float。
Agent 修改旋轉時不能直接加減數值，需要用球面插值（SLERP）計算中間幀。
實作上可先轉換為 Euler 角處理，最後再轉回 Quaternion 存檔。

---

## 目前進度

- [x] Phase 1 工具架構（此目錄）
- [x] Phase 1 工具實作：`anim_inspector.py`（summary/tracks/set-key/scale-time/offset/scale-value）
- [x] set-key 支援向量值軌道（Vector2/3/4、Quaternion），補上 `offset`/`scale-value` 批次數值操作
- [x] Metadata 格式定案：`anim_metadata.py`（init/show/set-tag/compat）
- [x] Phase 1 實際測試（範例：`examples/fighter.tres`；inspector 六指令 + metadata 全指令跑通）
- [x] Phase 2 設計：`PHASE2_DESIGN.md`（角色分工：人/Claude/工具；組合演算法；工具介面）
- [x] Phase 2 機械原語：`anim_compose.py concat`（序列拼接 + `--blend` 時間重疊；idle+punch 實測）
- [ ] Phase 2 進階：cross-fade 值混合烘焙、銜接連續性補正（fix-seam）、root motion 累加
- [ ] Phase 2 端到端：Claude 自然語言 → metadata 配對 → compose 指令的實際走查
- [ ] 確認 3D .animlib 格式結構（待有 Godot 3D 場景後測試）

### 2026-05-22 首次實測修 bug 紀錄

工具撰寫時假設 value 軌道的 `values` 也是 `PackedFloat32Array`，但 Godot 實際存成
一般 Array（`[0.0, 0.5, ...]` 或 `[Vector2(...), ...]`）。拿 `examples/fighter.tres`
首測時暴露三個問題，已修：

1. **`tracks` 全軌道印「無法解析 keys 資料」** — values 解析只認 `PackedFloat32Array`，
   不認 `[...]` 一般 Array。
2. **`scale-time` 清空所有 values + 丟掉 `transitions`/`update`**
   （`_replace_track_keys` 用未解析到的 `values=[]` 重建整個 keys dict，等於資料毀損）。
3. **`set-key` 直接 `IndexError`**（values 為空但 times 有內容）。

修法：
- 用括號感知的 `_field_value_span` 定位欄位，能處理 `PackedFloat32Array(...)`、
  `[...]`、巢狀 `{...}` 與純量。
- 改外科式替換 `_replace_keys_field`：只動目標欄位，`transitions`/`update`/其他欄位
  原封不動，對任何軌道類型都安全。
- `cmd_set_key` 偵測到非 float 軌道（Vector2/method）時明確拒絕，插入新 key 時同步
  插入 `transitions=1.0`。
- `cmd_scale_time` 只縮放 `times` 與 `length`，不碰 values。

### 2026-05-22 補強編輯能力（向量值軌道 + 批次操作）

把 Phase 1 的編輯能力從「只能改純量 float」補齊到向量，作為 Phase 2 的前置基礎：

1. **值解析改為結構化分量**：新增 `_parse_value_item`，把每個 key 解析成
   `(vtype, comps)`，自動辨別 `float` / `Vector2` / `Vector3` / `Vector4` /
   `Quaternion` / `other`（method dict 等）。`_parse_values` 回傳 `{vtype, comps, items}`，
   取代原本的 `(kind, floats, items)` 三元組。
2. **`set-key` 支援向量**：輸入如 `".:position" 0.3 "Vector2(12, -4)"`，型別需與
   軌道一致（不一致明確拒絕）；method/dict 軌道仍拒絕。
3. **新增 `offset`**：整條軌道逐分量平移（delta 型別需與軌道一致）。
4. **新增 `scale-value`**：整條軌道數值乘上純量。
5. **Quaternion 防呆**：offset/scale-value 對 Quaternion 逐分量運算會破壞單位長度，
   印出警告（仍執行）；3D 旋轉建議用 set-key 指定完整四元數。

序列化格式對齊引擎以減少無謂 diff：
- 向量分量與 **PackedFloat32Array 元素**（times/transitions）走 `_fmt_real`，
  整數值不帶 `.0`（比照 Godot `rtos`）。
- value Array 裡的 float 仍用 `_fmt_float` 保留 `.0`（比照 Variant float 序列化）。

實測（`examples/fighter.tres` 副本）：單一 key 編輯整檔僅一行 diff；向量
set-key 插入後 times/transitions 維持整數風格且正確排序；offset/scale-value
數值正確；型別不符與 method 軌道皆正確拒絕。

---

*記錄時間：2026-05-22*
