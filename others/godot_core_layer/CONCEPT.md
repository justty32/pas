# 共用 C++ 核心資料層

## 問題背景

隨著 GDExtension 模組增多（地圖、生物、動畫、戰鬥、經濟…），若各模組各自定義資料傳輸格式，會產生：
- GDScript 側需要記住多套 API 慣例
- 跨模組資料交換困難（地圖資料傳給戰鬥模組需要轉換）
- 重複定義相同概念（座標、實體 ID、資源量…）

**目標**：建立一個共用的 C++ 資料層，作為所有 GDExtension 模組的共同基礎。

---

## 架構示意

```
GDScript（Godot 表現層）
    │  統一 API 慣例（PackedArray / TypedArray<Dictionary> / Resource）
    ▼
┌─────────────────────────────────────────┐
│         GDExtension 橋接層              │
│  MapCoreGDExt  │  CreatureGDExt  │ ...  │
└────────┬───────┴────────┬────────┴──────┘
         │                │
         ▼                ▼
┌─────────────────────────────────────────┐
│         gamecore_cpp（共用核心層）       │
│  - 統一座標/實體/資源結構               │
│  - 跨模組資料交換介面                   │
│  - 序列化慣例                           │
└─────────────────────────────────────────┘
         │                │
         ▼                ▼
  mapcore_cpp_square   creature_cpp   ...
  （各功能 C++ 函式庫）
```

---

## 共用核心層應定義的內容

### 1. 基礎資料型別

```cpp
// gamecore/types.h
namespace gamecore {

// 世界座標（地圖格子）
struct Coord { int x, y; };

// 實體唯一 ID（跨模組通用）
using EntityID = uint64_t;
constexpr EntityID NULL_ENTITY = 0;

// 資源量（貨幣、材料等）
using ResourceAmount = int32_t;

// 方向（四方向 or 六方向，視地圖類型）
enum class Dir4 : uint8_t { N, E, S, W };
enum class Dir6 : uint8_t { NE, N, NW, SW, S, SE };

}
```

### 2. C++ ↔ GDScript 傳輸慣例

| C++ 型別 | GDScript 型別 | 用途 |
|---------|--------------|------|
| `vector<Coord>` | `PackedVector2iArray` | 路徑、座標列表 |
| `vector<float>` | `PackedFloat32Array` | 數值陣列（高度、溫度…） |
| `vector<int>` | `PackedInt32Array` | 枚舉陣列（地形類型…） |
| 複雜物件列表 | `TypedArray<Dictionary>` | 河流邊、特徵資訊 |
| 單一複雜物件 | `Dictionary` | 查詢結果 |
| 持久化資料 | `Resource` subclass | 地圖資料、生物定義 |

**規則**：
- 批量資料優先用 `PackedArray`（效能好）
- 結構不固定的物件用 `Dictionary`，但需在文件中明確定義 key
- 跨幀持有的資料封裝為 `Resource`（才能被 Godot 的引用計數管理）

### 3. 模組間資料交換

各 C++ 模組之間直接用 C++ struct 溝通，**不透過 GDScript**。例如：

```cpp
// 戰鬥模組查詢地圖模組的地形
// ✅ 正確：C++ 直接呼叫
const mapcore::Tile& tile = map_data.tile_at(coord);
bool passable = tile.terrain != mapcore::TERRAIN_OCEAN;

// ❌ 錯誤：繞道 GDScript 再傳回 C++
```

GDScript 只負責觸發行為和接收結果顯示，不做中間人。

---

## 現有先例（mapcore_godot）

`mapcore_cpp_square` + `mapcore_godot` 已建立了這套模式的原型：
- C++ 函式庫：`mapcore_cpp_square/`（純 C++，無 Godot 依賴）
- GDExtension 橋接：`mapcore_godot/src/`（map_data.h, map_generator.h）
- 傳輸格式：`PackedInt32Array`（地形）、`PackedFloat32Array`（高度/溫度）、`TypedArray<Dictionary>`（河流）

新模組照此模式擴展即可。

---

## 待設計

- [ ] `gamecore/types.h` 的實際位置與 CMakeLists 整合方式
- [ ] EntityID 的分配機制（集中分配 vs 各模組自管）
- [ ] 跨模組 C++ 介面的頭文件組織（單一 `gamecore/api.h` vs 分散）
- [ ] 序列化格式（存檔讀檔）：JSON / binary / Godot `.tres`

---

*記錄時間：2026-05-22*
*狀態：概念階段，尚未設計，等待後續規劃*
