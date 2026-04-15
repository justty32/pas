# Scene GUI 系統分析 - Level 2 & 3

## 1. 核心類別：Control (`scene/gui/control.h`)
`Control` 是所有 GUI 組件的基底類別，繼承自 `CanvasItem` (具備 2D 渲染能力)。

### 關鍵機制：
- **錨點與邊距 (Anchors & Margins)**：
    - 使用 `Anchor` 枚舉 (BEGIN, END) 定義相對於父節點的定位。
    - 支援 `LayoutPreset` (如 `PRESET_FULL_RECT`, `PRESET_CENTER`) 快速設定佈局。
- **滑鼠過濾 (Mouse Filter)**：
    - `STOP`: 攔截事件。
    - `PASS`: 處理並向下傳遞。
    - `IGNORE`: 完全忽視事件。
- **焦點管理 (Focus)**：
    - 支援 `FOCUS_CLICK`, `FOCUS_ALL`, `FOCUS_NONE` 等模式。
    - 提供鄰近焦點搜尋機制（上、下、左、右）。
- **主題系統 (Theme)**：
    - 整合了 `Theme` 資源，負責管理字體、顏色、樣式盒 (StyleBox) 等視覺資產。
    - 支援主題覆寫與繼承。
- **尺寸標記 (Size Flags)**：
    - `FILL`, `EXPAND`, `SHRINK_*` 用於控制在 `Container` 中的自動縮放行為。

## 2. 佈局容器：Container (`scene/gui/container.h`)
`Container` 繼承自 `Control`，專門用於管理其子 `Control` 節點的尺寸與位置。

### 常見容器類型：
- **`BoxContainer` (HBox/VBox)**：線性排列子節點。
- **`GridContainer`**：網格化排列。
- **`MarginContainer`**：增加邊距。
- **`ScrollContainer`**：提供捲動區域。
- **`TabContainer`**：頁籤切換佈局。

### 自動佈局原理：
1. **最小尺寸計算**：子節點報告其 `get_minimum_size()`。
2. **排列觸發**：當容器尺寸改變時，觸發 `NOTIFICATION_SORT_CHILDREN`。
3. **子節點定位**：容器根據其邏輯 (如 `HBox`) 呼叫 `fit_child_in_rect()` 來調整子節點。

## 3. 重要組件
- **`BaseButton`**：處理點擊、切換狀態的抽象基類。衍生出 `Button`, `CheckBox`, `TextureButton` 等。
- **`Range`**：處理數值範圍的基類。衍生出 `ScrollBar`, `Slider`, `ProgressBar` 等。
- **`Label`**：顯示文字，支援自動換行與文字對齊。
- **`TextEdit` / `CodeEdit`**：複雜的文字編輯器，支援語法高亮與自動補全。

---
*檔案位置：`scene/gui/control.h`, `scene/gui/container.h`*
