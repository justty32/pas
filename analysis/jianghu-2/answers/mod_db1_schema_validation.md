# 拆解實際 Workshop Mod：db1_Mod.txt schema 驗證 + 能力邊界修正

> 日期：2026-05-23
> 樣本：本機 5 個已訂閱 mod，位於 `~/.local/share/Steam/steamapps/workshop/content/1606180/<id>/`
> 目的：驗證 `architecture/workshop_modding.md` 推測的 schema，並校正「能改什麼」的結論。

## 0. 樣本清單

| Workshop ID | 標題 | 用到的表 | 原型（archetype）|
|---|---|---|---|
| `3634933446` | 化凡秘章 | npc_prototype, scriptsclient, npc_fight, areatrigger, stringlang | **帶行為腳本的劇情 NPC**（有 Graphml/）|
| `3505985647` | 新手保护宝物 | item_base, item_equip, npc_prototype, npc_fight, npc_interact, shop, wordentry, formula_baseattri, stringlang | 新手保護道具/裝備 |
| `3448709751` | 开局福利商人 | item_base, npc_prototype(3), npc_fight(3), npc_interact(3), shop(80), stringlang | 開局福利商人（80 條商品）|
| `3416784651` | 爽文江湖-追忆系列(0.0) | dialoguelist(11), item_base(66), npc_prototype, loot_items, npc_fight, npc_interact, shop(66), stringlang(145) | 大型劇情/內容 mod（有 Graphml/）|
| `3508527292` | 宗门功法 | item_base(7), npc_prototype(2), npc_fight(2), npc_interact(2), shop(21), stringlang(11) | 宗門功法販售（有 Graphml/）|

> 5 個全部用 `npc_prototype` + `npc_fight` + `stringlang`；多數用 `shop` + `npc_interact` + `item_base`。沒有任何一個用到 `way_point` / `npc_xiuxiananim` / `npc_environmentsound`——與「這些表不可 mod」的結論一致。

## 1. ✅ db1_Mod.txt schema 完全符合推測

格式 = `表名|筆數` 標頭行，後接 N 列、欄位以 `#` 分隔。純文字（非 binary）。
以 `化凡秘章` 全檔為例（17 行）：

```
npc_prototype|1
1102451#MIFAJIJUAN#1300000001#0#0#0#0#0#0#0#0#1#221.321#236.865#107.6366#20#1#0#1300000002##62141#50633|50542|82559|82567|82586|82598|82479|53005#100#0##1401#0#0#0####0##0##0#
scriptsclient|6
11345671#id_10000001#
11345672#id_11345672#
…（共 6 列）
npc_fight|1
1102451#5.5#3#10#1.2#19#18###10010##2####
areatrigger|2
400001#1#221.321#236.865#107.6366#0#11345673#11345674#1#4#4#4#0#0#1#0#1##0##AreaTrigger 400001
400002#1#251.9408#234.24#123.197#0#11345675#11345676#1#2#2#2#0#0#1#0#1##0##AreaTrigger 400002
stringlang|2
1300000002#WUFAMIE##
1300000001#MIFAJIJUAN##
```

觀察：
- 子欄位用 `|` 再分隔（如 npc_prototype 的招式組 `50633|50542|...`）——與 `NpcInteract.LoadCSV` 等 `Split("|")` 一致。
- 空欄位就是連續 `#`（如 npc_fight 尾段 `####`）。
- `npc_prototype` 名稱欄位填的是 **stringlang key（MIFAJIJUAN）**，本地化文字在 `stringlang` 表另給。

### 1.1 ID 範圍與白名單 offset 完全吻合（`SweetPotato/DataMgr.cs:174-194`）

| mod 用的表名 | 對應白名單類別 | 原型 ID | 文件記錄的 offset | 吻合？|
|---|---|---|---|---|
| `npc_prototype` | NpcPrototype | 1102451 | 1,000,000+ | ✅ |
| `npc_fight` | NpcFight | 1102451 | 1,000,000+ | ✅ |
| `areatrigger` | Areatrigger | 400001/400002 | 400,000+ | ✅ |
| `stringlang` | Stringlang | 1300000001/2 | 1,300,000,000+ | ✅ |
| `scriptsclient` | ClientScriptsDef | 11345671+ | 10,000,000+ | ✅ |
| `item_base` | ItemPrototype | — | 10,000,000+ | ✅ |
| `item_equip` | ItemEquip | — | 10,000,000+ | ✅ |
| `npc_interact` | NpcInteract | — | 1,200,000,000+ | ✅ |
| `shop` | ShopProto | — | 300,000,000+ | ✅ |
| `wordentry` | WordEntry | — | 300,000,000+ | ✅ |
| `formula_baseattri` | FormulaBaseAttri | — | 5,000,000+ | ✅ |
| `dialoguelist` | Dialoguelist | — | 1,300,000,000+ | ✅ |
| `loot_items` | Loot_items | — | 300,000,000+ | ✅ |

→ **實際 mod 用到 13/21 張白名單表，無一例外落在文件記錄的 ID 範圍。schema 推測驗證通過。**

## 2. ⚠️ 重要修正：mod **能**帶「行為腳本」與資產，不只是純數值表

之前 `workshop_modding.md` §4.2 寫「不能改邏輯 / 不能載資產」。拆 mod 後發現**講得太絕**：

### 2.1 mod 可帶 AutomatScript 行為腳本（yEd 圖）

- `scriptsclient` 表（`SweetPotato/ClientScriptsDef.cs`，44 行）每列 = `腳本ID#腳本檔名#`。
- 腳本圖檔放在 mod 的 `Graphml/Bin/<檔名>.bytes`（編譯後的 yEd graphML）。
- 載入路徑（`Automat.cs:79-82`）:
  ```csharp
  else if (DataMgr.GetModId(m_nScriptID) != 0) {
      string path2 = DataMgr.Instance.GetModPath(GetModId(m_nScriptID)) + "/Graphml/Bin/" + fileName + ".bytes";
      Real_Load(File.ReadAllBytes(path2), null);   // 載入並執行
  }
  ```
  即：腳本 ID 屬 mod 範圍時，直接從 mod 資料夾讀 graph bytes 執行。
- mod 編輯器端對應型別 `ModSpace/YedScript.cs`（在 `ModSpace/DataMgr.cs:84` 的編輯器登記表，`isLoadModOnlyDB: true`）。

`化凡秘章` 的 `id_11345672.bytes` 用 `strings` 拆出的節點函式（即可用的腳本指令庫片段）：

| 節點函式 | 作用 |
|---|---|
| `Entry` / `Exit()` | 流程起訖 |
| `AutoFindPath(226.77,238.36,98.64,90,1102451)` | 令 NPC 1102451 尋路到座標 |
| `IsMoveFinished(1102451)` | 等待移動完成（條件節點）|
| `ShowBlackScreen(3000,510001,8)` | 演出黑幕轉場 |
| `SetNpcPostion(1,251.94,234.24,123.20,0)` | 瞬移 NPC |

這些函式名 = `AutomatManager.cs` 的 `handlerMap[...]` 註冊項（如先前看到的 `handlerMap["EnterXiuXian"]`）。**亦即 mod 能用一套固定的函式詞彙編寫劇情/演出/NPC 行為序列**——這是「資料驅動的視覺腳本」，不是任意 C#。

### 2.2 mod 資源目錄有 4 種（`ModSpace/ResourcePath.cs:9-15`）

```
Graphml/   行為腳本（已確認實際使用）
SFX/       音效
Gui/       介面資源
Scene/     場景資源
```

→ 框架預留了 SFX/Gui/Scene 目錄，**mod 並非完全不能帶資產**。本次 5 個樣本只用到 `Graphml/`，SFX/Gui/Scene 是否完整可用待後續實測。

### 2.3 修正後的能力邊界

| 能力 | 之前說法 | 修正後 |
|---|---|---|
| 改數值表 | ✅ 21 表 | ✅（不變）|
| 改 NPC 行為/劇情序列 | ❌「不能改邏輯」 | **△ 能**——用 AutomatScript yEd 圖（固定函式庫），經 `scriptsclient` + `Graphml/Bin/` |
| 載入資產 | ❌「沒看到」 | **△ 框架預留** SFX/Gui/Scene 目錄，Graphml 已確認；其餘待實測 |
| 任意 C# 邏輯 / 新引擎函式 / 改既有 UI 結構 | ❌ | ❌（不變，仍需 BepInEx）|

> 關鍵區別：官方框架給的是「**用既有函式庫拼裝行為**」的能力（DSL 級），不是「寫新程式碼」的能力。要新函式、改戰鬥決策核心、改 UI 佈局、hook 網路，仍只能 BepInEx。

## 3. workshop.json 實例（驗證 binary 前綴 + JSON）

`化凡秘章/workshop.json`（416 bytes，開頭有 BinaryWriter 長度前綴，其後為 pretty JSON）：

```json
{
    "publishedFileId": 3634933446,
    "fileName": "",
    "title": "化凡秘章",
    "contentFolder": "MyMod2025_12_30_03_39_13",
    "changeNote": "Version 1.0",
    "description": "无描述",
    "previewUrl": "D:\\Users\\asus\\Desktop\\微信图片_20251230162821_86_15.jpg",
    "metadata": "",
    "visibility": 0,
    "modId": 1767083776,
    "tags": "[]"
}
```

- ✅ 印證 `ModPack.cs` 的格式分析：length-prefixed string + 手刻 4-space pretty JSON。
- `modId` = 1767083776 = Unix timestamp（2026-01-...，作者建 mod 的時間），用作條目命名空間。
- `contentFolder` 還留著作者本機的工作資料夾名 `MyMod2025_12_30_...`；`previewUrl` 甚至洩漏作者本機絕對路徑——印證上傳時不清理本機路徑。

## 4. 對你做 mod 的啟示

- **做純數值/物品/商店/NPC/任務 mod**：照這 13 張表的格式寫 `db1_Mod.txt` 即可，ID 用對應 offset 起跳避免衝突。
- **做劇情/演出/觸發式 NPC 行為**（如「走到某點→黑幕→傳送→對話」）：用 `scriptsclient` + `Graphml/Bin/*.bytes`，靠遊戲內 mod 編輯器產生 yEd 圖；函式詞彙以 `AutomatManager.handlerMap` 為準。
- **NPC 自主環境行為**（巡邏路線/休閒動作/環境音/路徑事件）：**仍不行**（那 4 張表不在白名單），只能 BepInEx。詳見 `details/npc_environment_interaction.md`。
- **下一步可做**：把 `AutomatManager.handlerMap` 的完整函式清單拉出來，等於「mod 腳本可用 API 全集」——對做劇情 mod 最有價值。
</content>
