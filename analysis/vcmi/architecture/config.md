# VCMI 配置與數據結構分析 (`config/`)

VCMI 是一個數據驅動 (Data-driven) 的引擎。幾乎所有的遊戲規則數值都定義在 `config/` 目錄下的 JSON 檔案中。

## 1. 核心數據模型
- **`gameConfig.json`**: 引擎的全局配置，包括網路超時、資源路徑、渲染設定等。
- **`factions/`**: 定義各個種族（城堡、塔樓等），包含城鎮建築樹與背景音樂。
- **`creatures/`**: 定義所有兵種屬性（生命值、攻擊力、傷害、技能）。
- **`artifacts.json`**: 定義所有寶物的效果及其紅利系統加成。
- **`spells.json`**: 定義魔法消耗、效果類型與等級修正。

## 2. 紅利系統與配置
- VCMI 的強大之處在於，大多數 JSON 配置檔案中都可以直接定義紅利 (`bonuses`)。
- 例如，在 `artifacts.json` 中，一個寶物可以直接包含一組 `bonuses` 陣列，這些加成在遊戲加載時會被解析並掛載到紅利系統圖中。

## 3. Schema 驗證 (`config/schemas/`)
- 為了確保 Mod 數據的正確性，VCMI 包含了一套完整的 JSON Schema。
- 在開發與 Modding 過程中，這用於驗證配置檔案是否符合引擎預期的格式。

## 4. UI 與熱鍵配置
- **`mainmenu.json`**: 定義主選單的 UI 佈局。
- **`keyBindingsConfig.json`**: 定義所有遊戲內操作的預設快捷鍵。

## 5. 跨平台支持
- **`filesystem.json`**: 定義了 VCMI 如何在不同操作系統（Windows, Linux, Android 等）下定位數據目錄。
