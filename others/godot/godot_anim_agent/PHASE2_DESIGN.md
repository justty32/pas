# Phase 2 設計：程序生成與動作組合

接續 `VISION.md` 的 Phase 2。本文件釘死**角色分工**、**組合演算法**與**工具介面**，
作為實作 `anim_compose.py` 的依據。

---

## 1. 核心觀念：AI 不在 Python 工具裏

Phase 2 最容易誤解的一點：「自然語言動作組合」不代表 Python 工具要做 NLP。
真正的分工是——

| 角色 | 負責 | 不負責 |
|------|------|--------|
| **人** | 給意圖：「迅速閃避出殘影，之後跳躍下劈」 | 數值、骨骼、時序 |
| **Claude（session 內）** | 語意解構 → 挑基礎動畫 → 決定順序與銜接策略（**查 metadata 配對，不猜骨骼**） | 機械式拼接的算術 |
| **Python 工具 `anim_compose.py`** | 機械式拼接：時間位移、軌道合併、過渡插值、寫回 `.tres` | 任何語意判斷 |

也就是說：**Claude 把高階意圖翻譯成一串明確的工具指令**，工具只做確定性的資料變換。
這讓組合過程可重現、可檢查、不靠工具端的黑箱。

典型一輪：

```
人：「先閃避再上勾拳」
  ↓ Claude 解構
[dodge, upper_cut]
  ↓ Claude 查 metadata：upper_cut.compatible_after 是否含 dodge？exit/entry 速度是否連續？
合法 → 決定 concat，seam 加 0.05s cross-fade
  ↓ Claude 下指令
python anim_compose.py concat fighter.tres combo_1 dodge upper_cut --blend 0.05
  ↓ 工具機械拼接，寫回新動畫 combo_1
人：在 Godot 重載預覽
```

---

## 2. Metadata 作為配對與銜接依據

接 `anim_metadata.py` 的 `.anim.meta.json`。Phase 2 用到三類欄位：

- **`tags`**：語意配對。Claude 把「閃避」對應到帶 `dodge` tag 的動畫。
- **`compatible_before` / `compatible_after`**：合法性檢查。組合前先確認順序允許，
  避免拼出不自然的銜接（例如 `landing` 不該接在空中動作之前）。
- **`exit_velocity` / `root_motion_delta`**：銜接連續性。判斷 seam 兩側骨骼速度與
  根位移是否連續，決定要不要插過渡或補正。

工具本身**不讀 metadata**——metadata 是 Claude 的決策輸入。工具只接收 Claude 算好的
clip 順序、blend 長度、root motion 補正量等明確參數。

---

## 3. 組合演算法

### 3.1 序列拼接 concat（MVP，本次實作）

把 N 段動畫接成一段新動畫。

1. **時間位移**：第 i 段的起始偏移 `offset[i] = Σ(前面各段有效長度)`。
   無 blend 時有效長度 = clip 長度；有 blend 時 `offset[i] = offset[i-1] + len[i-1] - blend[i]`（段落重疊）。
2. **軌道聯集**：收集所有 clip 的軌道路徑（依 `path` 比對；MVP 假設同 path 同 type）。
3. **逐軌道合併**：對每條路徑，依 clip 順序把各 clip 的 keys（times 位移 `offset[i]`、
   values/transitions 原樣）串接。
4. **seam 去重**：兩段交界若出現時間幾乎相同的 key（`|Δt|<1e-5`），保留後一段的，
   避免 Godot 重複時間 key。
5. **header 欄位**：合併軌道的 `type/interp/loop_wrap/update/imported/enabled` 取自
   **第一個出現該路徑的 clip**。
6. **新 sub_resource**：`length = offset[last] + len[last]`；寫入檔案、登錄到 `[resource] _data`、
   `load_steps` +1。

**MVP 已知限制**（記在 §6）：某 clip 缺少另一 clip 才有的軌道時，該軌道在缺席段落不會
補 hold key，Godot 會在跨段 key 之間直接插值——可能造成該骨骼在缺席段落「漂移」。
這正是 §3.3 銜接修正要處理的；MVP 先接受，並在輸出時印出警告列出「非全程出現」的軌道。

### 3.2 過渡混合 cross-fade（已實作：資料層烘焙）

seam 兩側值不連續時，在重疊區做線性混合。採**資料層烘焙**路徑（確定性，不動場景）：

- 重疊窗 `W = [offset[i+1], offset[i]+len[i]]`，寬度為夾過的 `eff_blend[i]`。
- 對**兩相鄰 clip 都有、且型別一致的數值軌道**：取兩段在 W 內 key 時間的聯集 + 端點，
  逐點線性混合 `value(t) = lerp(sampleA(t), sampleB(t), w)`，`w = (t - W.start) / 寬度`；
  `sampleA/B` 各自在該 clip 的 key 上線性插值（端點外夾住）。
- 混出的 key 取代窗內兩段原 key；窗外維持各自原 key。
- 只出現於單邊、型別不一致、或 method 軌道：不混合，沿用純拼接（§3.1）。

實作於 `anim_compose.py`（`_sample` + cmd_concat 的 blendable 分支）。
**已知限制**：Quaternion 目前逐分量線性混合（非 SLERP），大旋轉會失真——工具會警告，
列入待辦改用真正的球面插值。AnimationTree 層（`AnimationNodeBlend`/`Transition`）為另一條
不動 clip 資料的路徑，本工具暫不採用。

### 3.3 銜接修正（後續）

依 metadata 的 `exit_velocity` / 末幀值，檢查 seam 兩側同骨骼是否連續；不連續時：
- 插入過渡 key（短時間內補上中間值），或
- 對後段整體做 `offset`（沿用 Phase 1 的 offset 指令）對齊起始姿態。

### 3.4 Root motion 累加（已實作）

避免角色在世界空間「滑回原點」：後一段的位移軌道接續前一段的終點。

- 介面：`--root-motion <track_path>`，由 Claude 指定哪條是位移軌道（通常 `.:position`）。
- 演算法：依 clip 順序累加。第一段不動；之後每段加上
  `off = 前段終點 - 本段起始值`，使本段起始值對齊前段終點（seam 連續）。
  終點位移 = 最後一段套用 off 後的末值。
- 該軌道**不參與 cross-fade**（位移要累加、不是混合）。
- 2D 為 Vector2、3D 為 Vector3，邏輯相同（逐分量累加）。

實作於 `cmd_concat` 的 root motion 預處理段。對照測試（`step_in → punch`）：不加旗標時
step 的前踏在 seam 被 punch 歸零的位移吃掉（角色原地）；加旗標後 punch 接續 x=24 前傾，
位移連續。

---

## 4. 工具介面設計（`anim_compose.py`）

```
# 已實作
python anim_compose.py concat <file> <new_anim> <clip1> <clip2> [...] \
       [--blend <秒>] [--root-motion <track_path>]
    把 clip1, clip2, ... 依序拼成新動畫 <new_anim>，寫回同檔的 AnimationLibrary。
    --blend       相鄰段重疊指定秒數，並對共有數值軌道做 cross-fade 值混合烘焙（§3.2）。
    --root-motion 指定位移軌道，後段接續前段終點累加（§3.4）。

# 後續
python anim_compose.py fix-seam <file> <anim> <seam_time> ...   # 缺席軌道 hold / 起手對齊
```

`concat` 重用 `anim_inspector.py` 的解析/格式化基礎設施
（`parse_tres` / `_extract_tracks` / `_float_list_to_packed` / `_format_values_array` 等），
確保序列化風格與 Phase 1 一致（向量/PackedFloat 元素不帶 `.0`、value Array float 補 `.0`）。

---

## 5. 資料層細節

新增一段 Animation sub_resource 並登錄，需動到三處：

1. **`[gd_resource ... load_steps=N]`**：N += 1。
2. **新 `[sub_resource type="Animation" id="Animation_<new>"]` 區塊**：插在最後一個
   sub_resource 之後、`[resource]` 之前。每條合併軌道重建完整 `tracks/i/*` + `keys` dict。
3. **`[resource] _data = { ... }`**：加一行 `&"<new>": SubResource("Animation_<new>"),`。

合併軌道的 `values` 以**原始 item 字串**串接（不重新解析），讓 method dict、任意值型別
都能原樣通過。

---

## 6. 限制與未決問題

- **缺席軌道漂移**（§3.1 MVP 限制）：clip 間軌道集合不一致時，缺席段落不補 hold key。
- **值混合未烘焙**：`--blend` 目前只重疊時間，未算混合值（§3.2）。
- **同 path 不同 type**：MVP 假設同路徑同軌道型別，未處理衝突。
- **NodePath 比對**：以清理後的字串比對；含 `:property` 的子屬性路徑視為不同軌道（正確）。
- **3D 尚未驗證**：Quaternion 軌道的 concat 機械上可行（原樣串接），但 blend 需 SLERP（後續）。

---

## 7. 端到端範例（idle + punch）

`examples/fighter.tres` 內含 `idle`（1.2s，1 軌）與 `punch`（0.6s，4 軌）。

```
python anim_compose.py concat fighter.tres idle_then_punch idle punch
```

預期：產生 `idle_then_punch`，length = 1.8s；
- `Armature/Torso:rotation` 來自 idle（punch 沒有此軌 → 警告：非全程出現）
- `Armature/UpperArm:rotation` / `ForeArm:rotation` / `.:position` / method 來自 punch，
  times 全部 +1.2s。

---

*記錄時間：2026-05-22*
