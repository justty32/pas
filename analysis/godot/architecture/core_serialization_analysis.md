# Godot 序列化與存檔架構分析 - Level 2 & 5

## 1. 資源序列化核心
Godot 的存檔系統主要建立在資源 (`Resource`) 的序列化基礎之上。

### 關鍵類別：
- **`ResourceSaver` / `ResourceLoader`**：全域單例入口，負責分發儲存/載入請求。
- **`ResourceFormatSaver` / `ResourceFormatLoader`**：抽象基類，定義了如何處理特定格式（如 `.tres`, `.tscn`, `.res`, `.scn`）。
- **`PackedScene`**：特殊的資源，用於序列化整個節點樹及其屬性。

## 2. 存檔檔案格式分析

### 文字格式 (.tscn / .tres)
- **基於標籤的結構**：
    - `[gd_scene ...]` 或 `[gd_resource ...]`：檔案標頭，包含類型、載入器與 UID。
    - `[ext_resource ...]`：引用外部資源。
    - `[sub_resource ...]`：內嵌在檔案中的資源（如一個節點專用的 `RectangleShape2D`）。
    - `[node ...]`：定義節點層級與屬性。
- **優點**：易於版本控制 (Git Friendly)、人類可讀、手動修改方便。
- **處理器**：`ResourceFormatSaverText` 與 `ResourceFormatLoaderText`。

### 二進制格式 (.scn / .res)
- **自定義二進制佈局**：
    - 包含字串表、資源索引與壓縮的 Variant 資料。
- **優點**：載入速度快、檔案體積小。
- **處理器**：`ResourceFormatSaverBinary` 與 `ResourceFormatLoaderBinary`。

## 3. 序列化邏輯流程
1. **遍歷屬性**：透過 `_get_property_list()` 取得物件所有需要持久化的屬性。
2. **處理引用**：識別屬性中的 `Ref<Resource>`。若資源有路徑則存為 `ext_resource`，否則遞迴序列化為 `sub_resource`。
3. **Variant 轉換**：使用 `VariantWriter` (文字) 或直接二進制寫入將資料轉為位元流。

## 4. 數據流向
- **場景存檔**：編輯器 -> `PackedScene` -> `ResourceSaver` -> `.tscn` 檔案。
- **遊戲存檔**：自定義 `Resource` 物件 -> `ResourceSaver` -> `.tres` 檔案。

---
*檔案位置：`core/io/resource_saver.h`, `core/io/resource_loader.h`, `scene/resources/packed_scene.h`*
