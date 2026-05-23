# Save / Load 系統剖析

> 來源：`../../../../SourceCode/Assembly-CSharp/SweetPotato/GameSaving.cs`（2620 行）  
> 日期：2026-05-22

## TL;DR

- **存檔不加密、不壓縮**，主要內容是 **LitJson pretty-printed JSON 純文字**。
- 每個槽位由 **兩個檔案** 組成：一個 binary header（給選單列表用）、一個 `.json`（完整遊戲狀態）。
- 槽位上限：**8 個**（`MaxFileNum = 8`）。
- 存檔目錄：Linux 為 `~/.config/unity3d/inmotiongame/下一站江湖Ⅱ/`、Windows 為 `%LOCALAPPDATA%Low\inmotiongame\下一站江湖Ⅱ\`。
- 存檔版本 < 77 是舊格式（JSON 嵌在 binary header 內），>= 77 為現行格式（JSON 拆檔）。

## 1. 路徑配置

| 用途 | 路徑（runtime） | 程式碼位置 |
|---|---|---|
| 主存檔目錄 | `Application.persistentDataPath + "/Save2/"` | `GameSaving.GetSavePath()` @ 1252 |
| 自動存檔 | `<Save2>/Auto/` | `GameSaving.GetAutoSavePath()` @ 1233 |
| 本地設定 | `Application.persistentDataPath + "/Local/"` | `GameSaving.GetLocalPath()` @ 1243 |
| DB 持久化 | `Application.persistentDataPath + "/DB/"` | `GameSaving.GetDBPersistentDataPath()` @ 1261 |
| 雲端存檔（Steam Cloud）變體 | `<Save2>/<filename>_Y` | `Save()` @ 1308 |

旗標 `private static bool saveInPersistentDataPath = true`（@ 284）控制是否走 persistentDataPath，理論上可以切到 `Application.dataPath`（遊戲安裝目錄下），但實際走 persistent。

**本機（Linux + Proton）實際路徑（已確認）**：

```
~/.local/share/Steam/steamapps/compatdata/1606180/pfx/drive_c/users/steamuser/AppData/LocalLow/inmotiongame/下一站江湖Ⅱ/
├── Save2/              # 存檔（含 Auto/）
├── Local/
│   └── localfile       # 設定檔（玩家姓名/密碼/畫質等，binary header 格式）
├── DB/                 # 觸發後才會出現
├── AnnouncementRes/    # 公告下載快取
├── Player.log          # Unity 執行 log（current）
└── Player-prev.log     # 上一次執行 log
```

（Steam App ID **1606180** = 下一站江湖Ⅱ。原生 Linux 是 `~/.config/unity3d/inmotiongame/下一站江湖Ⅱ/`，但這版本是 Windows build 透過 Proton 跑，所以走 `compatdata/.../LocalLow/`。）

## 2. 每個存檔槽的兩個檔案

對於檔名 `savefile_0`（舉例），目錄會出現：

```
Save2/
├── savefile_0          # binary header（無副檔名）— 給 UI 列表用
└── savefile_0.json     # 完整 JSON 狀態（pretty-printed）
```

自動存檔則在 `Save2/Auto/autosavefile`（同樣 binary + `.json`）。

### 2.1 Binary header 格式

由 `BinaryWriter.Write(string)` 寫入，字串前 1 byte 是 varint 長度（.NET binary string encoding）。

順序（`Save()` 內的 `Action action = delegate` @ 1495）：

| # | 欄位 | 型別 | 範例 |
|---:|---|---|---|
| 1 | `playerName` | string | 玩家姓名 |
| 2 | `saveTime` | string | `2026/05/22 19:30:01` |
| 3 | `gameTime` | string（含 float） | `3600.5` |
| 4 | `posX` | string（含 float） | 玩家所在 X |
| 5 | `posZ` | string（含 float） | 玩家所在 Z |
| 6 | `filename` | string | `savefile_0` |
| 7 | `gameVersion` | string（含 int） | `77` 以上 |
| 8 | `gameDiff` | string（含 int） | 0~4，難度 |
| 9 | `modelId` | string（含 int） | 玩家服飾 |
| 10 | `maintaskName` | string | 當前主線 quest id |
| 11 | `gameType`（**只有 v≥77**） | string（含 int） | 0~4 GAME_TYPE |

舊版（v < 77）後面還會接一個 string 放完整 JSON；新版則只放 metadata，JSON 在 `.json` 檔。

### 2.2 JSON 主檔（`.json`）

由 LitJson `JsonStreamWriter` + 自製 `JsonWriterWrap`（`../../../../SourceCode/Assembly-CSharp/SweetPotato/JsonWriterWrap.cs`）寫入，**pretty print = true**（@ 1322），所以人眼可讀、可直接用編輯器修改。

頂層 key（節錄；完整內容見 `Save()` @ 1325–1479）：

```json
{
  "playername": "...",
  "saveTime": "...",
  "gameTime": ...,
  "filename": "...",
  "posX": ..., "posZ": ...,
  "gameVersion": 77,
  "dbVersion": 1,
  "m_GameDiff": 0,
  "m_volumeGlobal": 1.0,
  "triggerMusic": "...",
  "m_DLC_version": ...,
  "m_playerRoleType": 0,
  "m_playerTitleId": ...,
  "m_ItemIdGenerator": ...,
  "m_CanFiniseEntrustKeys": [...],
  "m_LifeSkillUseCount": {...},
  "m_EntrustWinedNpc": [...],
  "m_EntrustKilledNpc": [...],
  "m_DeadEntityInfoDir": {...},
  "m_CustomSpellSfx": {...},
  "m_CustomWeaponSfx": {...},
  "m_CustomQingGongAnim": [...],
  "m_itemRandomCreateCount": {...},
  "SHCS": ..., "characterLine": ..., "CurGameType": ...,
  "xiaonejianghu": ..., "zhenshijianghu": ...,
  "m_CurrentDiffWin": ...,

  "playerentity": { "<guid>": { ... PlayerEntity 完整狀態 ... } },
  "Entitys":     { "<guid>": { ... 每個 NPC/物件 ... }, ... },
  "allentityids": [...],
  "npcGuidProidDic": {...},
  "currentDistanceIndex": ...,

  /* Singleton<*>.Save 寫入的 key（每個 Manager 自己決定 key 名）*/
  /* 以下為呼叫順序，實際 key 看各 Manager 的 Save() 實作 */
  "ShopStoreSystem...":        ...,
  "ArtistrySystem...":         ...,
  "RelationShipManager...":    ...,
  "NpcBubbleChatRegulator...": ...,
  "TeamManager...":            ...,
  "RefreshManager...":         ...,
  "RandomNpcManager...":       ...,
  "ConditionPrototype...":     ...,
  "ShotcutExecuter...":        ...,
  "SystemState...":            ...,
  "SectSystem...":             ...,
  "MapAreaEventManager...":    ...,
  "XuanShangManager...":       ...,
  "VirtualEventManager...":    ...,
  "BuYeJingManager...":        ...,
  "GrowManager...":            ...,
  "EntrustGlobalManager...":   ...,
  "XiaYunLuManager...":        ...,
  "ShangChengManager...":      ...,
  "FuBenManager...":           ...,
  "MenPaiManager...":          ...,
  "MenPaiZhongMenDaBiManager...": ...,
  "MenPaiWarManager...":       ...,
  "XunWenManager...":          ...,
  "WordEntryGlobalManager...": ...,
  "JailManager...":            ...,
  "QingLouManager...":         ...,
  "NpcConditionalDialogueManager...": ...,
  "GameManualManager...":      ...
}
```

各 Manager Save 的呼叫順序見 `Save()` 1446–1474。

## 3. 寫入流程（`Save()` @ 1299）

```
Save(fi, isAuto, isYun, isThreadSave)
├─ 決定 path（主/Auto/_Y）
├─ Sync2Entity()                                  # 玩家狀態回寫 entity
├─ 寫 JSON 到 <path>.json.tmp（pretty）
│   ├─ 寫頂層 meta key
│   ├─ Dialoguelist.Save / SpellPrototype.Save / SpellEffect.Save / MiJiPage.Save
│   ├─ Entrust / WorldManager / ItemStorage 條件性寫入
│   ├─ 寫 playerentity { guid: PlayerEntity.Save(...) }
│   ├─ 寫 Entitys { guid: UnitEntity.Save(...) for each NPC/物件 in WorldManager.GetEntityDir() }
│   └─ 25+ Singleton.Save(jsonWriterWrap)
├─ File.Move(<path>.json.tmp → <path>.json)        # 原子替換
├─ 寫 binary header 到 <path>（覆寫 11 個欄位）
└─ GC.Collect()
```

例外處理：寫 JSON 失敗時會嘗試刪掉 `.tmp`，**但 binary header 不會回滾**。

## 4. 讀取流程（`Load()` @ 1565）

```
Load(path, preParseJsonData = null)
├─ HintUILayer.Push("LoadingView")
├─ ClearData()
├─ if (preParseJsonData != null) jsonData = preParseJsonData
│   else 開 <path>（binary header）解出 FileInfoItemData：
│       └─ 讀 11 個 string → metadata
│   └─ 然後決定如何取 JSON：
│       v < 77：JSON 嵌在 binary header 尾端，由 BinaryReader.ReadString() 取得
│       v >= 77：若 binary 後面還有資料就讀，否則去開 <path>.json
├─ jsonData["playerentity"]["1"] → PlayerEntity.LoadUseModId(...)
├─ 還原各種 EntrustManager / WorldManager 欄位
├─ 呼叫 Dialoguelist.Load / SpellPrototype.Load / SpellEffect.Load / MiJiPage.Load
├─ saveFileVersion = jsonData["gameVersion"]
│   └─ if AppGame.Instance.forceRewriteSaveFileVersion > 10:
│        saveFileVersion = AppGame.Instance.forceRewriteSaveFileVersion
│   └─ VersionChange.Init()                       # 跨版本資料遷移
├─ 逐 key 還原（每個都帶 ContainsKey 防呆）
└─ 在 jsonData["Entitys"] 上重建世界 NPC（後面還有，未完整貼）
```

關鍵旁路：**`AppGame.Instance.forceRewriteSaveFileVersion`** — 在 inspector / GM 工具可以強迫指定版本，繞過自動 detect。

## 5. 序列化機制

### 5.1 反射式 `[GameSaveKey]` 屬性

```csharp
[GameSaveKey("m_VirtualEvents")]
public List<VirtualEvent> m_VirtualEvents = new();
```

對應 helper：`Tools.GetGameSaveKey(this, "m_VirtualEvents")` @ `SweetPotato/Tools.cs:4127` — 用 reflection 找 field/property/member 上的 `GameSaveKey` attribute，回傳 attribute 內的 `keyName`，作為 JSON key。

實際使用範圍很小，僅 6 個檔案：
- `VirtualEventManager.cs`、`VirtualEvent.cs`
- `SweetPotato/FuBen.cs`、`SweetPotato/FuBenManager.cs`
- `SweetPotato/EntrustManager.cs`
- `SweetPotato/Tools.cs`（helper 本身）

大部分系統直接用硬編碼 key（如 `"playername"`、`"m_GameDiff"`），不走 attribute。

### 5.2 LitJson 寫入

`JsonWriterWrap`（`SweetPotato/JsonWriterWrap.cs`，189 行）是輕量包裝：
- `WriteProperty(key, value)` — 直接寫 primitive
- `WritePropertyJson(key, obj)` — 經 `JsonMapper.ToJson(obj)` 序列化後當成字串內嵌（注意：是字串，不是 nested object！）
- `NewJsonData(key)` — 嵌入新的 object

`WritePropertyJson` 的「字串內嵌 JSON」是這個系統的怪癖：實際讀檔時要先 `jsonData[key].ToString()` 再 `JsonMapper.ToObject<T>(s)`。這也是為什麼 JSON 中你會看到字串值是被脫逸過的 JSON：`"m_CanFiniseEntrustKeys": "[\\"key1\\",\\"key2\\"]"`。

## 6. Mod 開發者實用情報

### 6.1 可以做什麼

1. **Save editor**：直接讀 `.json`，改數值，寫回。完全沒加密。
2. **作弊腳本**：BepInEx plugin patch `GameSaving.Save` postfix，在 metadata 加東西、或在 `playerentity` 注入物品。
3. **跨遊戲版本升級**：用 `forceRewriteSaveFileVersion` 強迫走 `VersionChange.Init()` 流程。
4. **存檔 inspector**：解 binary header + JSON，自製選單外的存檔列表。

### 6.2 需要小心

- Binary header 與 JSON 必須一致（修 JSON 不改 header → UI 列表不會反映變更）；穩妥做法是修完 JSON 後重存一次讓遊戲重寫 header。
- 改 `playerentity` 子物件時要連同 `Entitys`、`allentityids`、`npcGuidProidDic` 一致（GUID 重複會壞）。
- `m_ItemIdGenerator` 是物品 ID 自增器，注入新物品時要遞增。
- 異常處理不完整：寫 JSON 失敗時 binary header 可能殘留舊版（已述）。
- v < 77 → v >= 77 的 schema 跳過大量遊戲版本（76 之前 JSON 嵌在 binary，77 之後拆檔）。寫 mod 不要假設你拿到的存檔是哪一版，先看 `saveFileVersion`。

### 6.3 Harmony patch 點建議

| 想做 | 目標 method | Patch 類型 |
|---|---|---|
| Save 完通知/額外處理 | `GameSaving.Save` | Postfix |
| Load 完注入物品/狀態 | `GameSaving.Load` | Postfix（async！注意） |
| 攔截 entity 寫入 | `UnitEntity.Save` | Prefix/Postfix |
| 自訂 key 持久化 | `GameSaving.Save` | Transpiler 或 Postfix 直接寫檔 |

`Load` 是 `async void`（@ 1565），patch 時要用 `MethodInfo` 拿到非同步狀態機（或 patch `MoveNext`），不能直接 patch wrapper。

## 7. 相關類別索引

| 類別 | 位置 |
|---|---|
| `GameSaving`（單例） | `SourceCode/Assembly-CSharp/SweetPotato/GameSaving.cs` |
| `GameSaving.FileInfoItemData` | 同上（巢狀，存檔槽 metadata DTO） |
| `GameSaving.ModID` | 同上（Workshop mod 識別 DTO） |
| `JsonWriterWrap` | `SweetPotato/JsonWriterWrap.cs` |
| `GameSaveKey` (Attribute) | `SweetPotato/GameSaveKey.cs` |
| `Tools.GetGameSaveKey` | `SweetPotato/Tools.cs:4127` |
| `SaveFolderCreate` (MonoBehaviour) | `SaveFolderCreate.cs`（dev 工具，建立 `Application.dataPath/SaveData`，runtime 沒用到主流程） |
| `VersionChange.Init` | （存檔版本遷移入口，待 trace） |

## 8. 待補

- [ ] `VersionChange.Init` 跨版本遷移細節
- [ ] `PlayerEntity.Save` 結構（最大的單一物件）
- [ ] `WorldManager.GetEntityDir` 哪些 entity `IsNeedSave()`
- [ ] Steam Cloud（`_Y` 後綴）的觸發點
- [ ] Settings（非戰局，例如音量、畫質）存哪邊 — 應該在 `Local/` 下，需驗證
