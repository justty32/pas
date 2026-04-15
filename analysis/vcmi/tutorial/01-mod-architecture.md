# 01 - Mod 架構與數據繼承

對於 VCMI 來說，一個「遊戲」或一個「模組」本質上是一組 JSON 配置檔案與資產的集合。

## 1. Mod 的進入點：`mod.json`

每個 Mod 必須包含一個 `mod.json`。對於工程師來說，最重要的部分是 `aspects`：

```json
{
  "name" : "My Epic Expansion",
  "version" : "1.0.0",
  "author" : "Senior Dev",
  "modType" : "expansion",
  "compatibility" : { "vcmi" : "1.7.3" }
}
```

## 2. 數據目錄結構

Mod 的資料夾結構應映射引擎的 `config/` 目錄：
- `config/creatures/`: 新兵種。
- `config/factions/`: 新種族。
- `config/artifacts/`: 新寶物。
- `content/sprites/`: 圖像資產。

## 3. JSON Schema 驗證

VCMI 使用強大的驗證機制。在開發過程中，你應該參考 `config/schemas/` 下的定義。
例如，定義一個新兵種時，引擎會根據 `creature.json` schema 檢查你的欄位。

## 4. 數據繼承與覆蓋 (Inheritance & Overriding)

這是 VCMI 數據引擎的核心特性：
- **增量修改**: 如果你想修改原版大天使的屬性，你不需要複製整個文件。只需在你的 Mod 中建立同名的 JSON 並指定你想要修改的欄位。
- **Load Order**: 加載順序決定了最後的覆蓋結果。啟動器 (Launcher) 負責處理這些衝突。

## 5. 資源索引

VCMI 使用邏輯路徑（Logical Paths）而非實體路徑。
`VCMI_lib` 中的 `VCMIDirs.cpp` 和 `CConfigHandler.cpp` 負責將邏輯資源名（如 `HEROES/ARCHER.DEF`）映射到實體文件。

---
**下一章**: [`02-lua-integration.md`](02-lua-integration.md) - 使用 LuaJIT 接管遊戲邏輯。
