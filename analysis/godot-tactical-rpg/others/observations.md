# 觀察與註記（重構遺留、資料不一致、可疑邏輯）

> 路徑相對於 `projects/godot-tactical-rpg/`。本檔記錄分析過程中發現、但不屬於架構描述的「值得日後注意」之處。皆為觀察，未修改任何原始碼。

---

## 1. 重複的 service 檔（同 class_name 兩份）

4.3 重構（@mbusson）後，多個 service 同時存在「短名」與「長名」兩個檔案，**內容完全相同、宣告同一個 `class_name`**：

| 目錄 | 兩個同名檔 | class_name |
|---|---|---|
| `data/models/world/combat/participant/service/` | `service.gd` 與 `ptcpt_serv.gd` | `TacticsParticipantService` |
| `data/models/view/camera/tactics/service/` | `service.gd` 與 `t_cam_serv.gd` | `TacticsCameraService` |
| `data/models/view/control/tactics/service/` | `service.gd` 與 `t_ctrl_serv.gd` | `TacticsControlsService` |
| `data/models/view/control/input/capture/service/` | `service.gd` 與 `inp_capt_serv.gd` | `InputCaptureService` |

GDScript 不允許兩個檔案宣告相同 `class_name`，正常情況會報「Class hides an autoload singleton / already exists」之類錯誤。推測其一其實內容已被取代或專案靠載入順序/某種機制容忍。**這是重構期的命名過渡遺留**，建議釐清哪個才是正本、刪除另一個。分析時以兩者內容一致為前提，引用以實際被 `_init`/`new()` 使用的類別為準。

> 影響：對 Create/Patch 模式而言，若要修改這些 service，需先確認哪個檔案真正生效，避免改了不被載入的那份。

---

## 2. StatsResource 欄位 schema 不一致

`StatsResource`（`data/models/world/stats/stats_res.gd`）目前的欄位是：
`override_name, expertise, strategy, level, sprite, movement, jump, max_health, attack_range, attack_power`。

但**部分舊 hero `.tres` 仍寫著已不存在的欄位**：
- `hero/knight.tres:12-19` 含 `mp=3`（應為 `movement`）、`armor`、`crit_rate`、`crit_dmg`、`def`、`stab`、`resi`——這些欄位 `stats_res.gd` 都沒有，載入時被忽略。最嚴重的是它用 `mp` 而非 `movement`，導致 knight 的移動力取**預設值 3**（`stats_res.gd:23`）而非檔案意圖的數值。
- 對照 `mob/skeleton.tres` 則是**乾淨的新格式**（用 `movement=5`），無多餘欄位。

> 結論：新增職業 `.tres` 時請以 `mob/skeleton.tres` 為範本，只填 `stats_res.gd` 實際存在的欄位（教學 `tutorial/how_to_add_a_class.md` 已據此撰寫）。舊 hero 檔有「升級成新 schema」的清理空間。

---

## 3. 未被使用的預留欄位 / hook

| 欄位 | 位置 | 現況 |
|---|---|---|
| `strategy`（Tank/Flank/Physical/Distance/Support） | `stats_res.gd:13` | AI 決策完全沒讀它，純標記。是「不同 AI 性格」的預留 hook |
| `starting_skills: Array[String]` | `expertise.gd:11` | 載入後無人消費，是技能系統的預留掛載點 |
| `pawn_moved` / `pawn_attacked` / `turn_ended` 訊號 | `pawn_res.gd:6-10` | 範本內訂閱者稀少，供擴充用 |
| `modifiers: Dictionary` | `stats.gd:8` | 已宣告但未實作數值修飾流程 |

這些都是擴充戰棋深度（技能、buff、AI 性格）的天然切入點。

---

## 4. 可疑邏輯（疑似 bug）

### 4.1 友軍可穿越的條件式
`arena/service/service.gd:62-64`（BFS 走訪）：
```gdscript
elif not (allies_on_map.size() > 0):
    if not (_neighbor.get_tile_occupier() in allies_on_map):
        _add_to_tiles_list.call(_neighbor)
```
外層 `elif not (allies_on_map.size() > 0)` 表示「**當有友軍清單時，這個 elif 反而不成立**」，於是內層「友軍格可穿越」的判斷在傳了友軍時根本進不去。意圖應是「當該格被佔據、且佔據者是友軍時可穿越」，條件式疑似寫反。實際表現：被佔據的格（無論敵我）大多直接被當作不可走訪。建議實測「能否穿越己方 pawn」並修正此條件。

### 4.2 攝影機聚焦時的冗餘賦值
`camera/service/movement.gd:74`：`camera.velocity = camera.velocity`（自我賦值，無作用），無害但可清理。

### 4.3 DebugLog 註記的歷史 crash
`debug.gd:135,149` 兩處註解 `# todo: got a crash 'cause no dict_entry.message`——表示部分 `debug_dict` 條目用 `string` 鍵而非 `message` 鍵（如 `nearest_target_found`、`nearest_target`，`debug.gd:57-66`），導致 `has('message')` 為 false 而不印。除錯訊息不一致，非功能性問題。

---

## 5. 範本的「刻意留白」清單（非 bug，是設計）

| 留白 | 位置 | 說明 |
|---|---|---|
| 關卡載入器 | `data/main.gd` | 開頭明示是 placeholder，預期被使用者自訂的 loader 取代 |
| 死亡/移除 pawn | 無 | 血量歸零只灰階、不移除、不擋路判定外 |
| 勝負判定 | 無 | 無「全滅即勝」等結束條件 |
| 存檔/讀檔 | 無 | `stats.gd` 註解提到可改造成存檔工具，但未實作 |
| 傷害深度 | `combat.gd` | 僅單一 `attack_power`，無防禦/命中/暴擊/克制 |

這些是把它定位為「最小可玩骨架」的結果，也是 Create 模式衍生時最值得補強的方向。

---

## 6. 對應的 Patch 連結

（目前尚無對應 patch；若日後針對上述 4.1 友軍穿越 bug 或 schema 清理製作 patch，於此記錄連結。）
