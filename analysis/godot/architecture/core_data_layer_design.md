# 共用 C++ 核心資料層設計分析

> 對應概念來源：`others/godot/godot_core_layer/CONCEPT.md`
> 事實依據：第一個（也是目前唯一活線）GDExtension 模組 `others/gamecore/mapcore_godot`，
> 其核心邏輯庫為 `others/gamecore/mapcore_cpp_square`（見 `mapcore_godot/SConstruct` 第 19、27~41 行的 `CPPPATH` 與來源清單）。

---

## 問題背景

`CONCEPT.md`（第 3~10 行）提出的核心顧慮是：當 GDExtension 模組增多（地圖、生物、動畫、戰鬥、經濟…），若每個模組各自定義資料傳輸格式，會造成三類重複成本：

1. **GDScript 側 API 慣例分裂**：每個模組各有一套回傳型別與 key 命名，腳本工程師要記多套規則。
2. **跨模組資料交換需轉換**：例如戰鬥模組要查地圖地形時，若兩邊資料模型不同就得做格式轉換。
3. **共通概念重複定義**：座標、實體 ID、資源量這些每個模組都會用到的東西被定義多次。

但在動手「設計」共用層之前，必須先承認一個事實：**抽象層不該憑空設計，而該從既有可運作的程式碼倒推**。本倉庫目前只有 `mapcore_godot` 一個活線模組（其餘 `mapcore_py/cpp/square` 系列已非活線），它已經在實務上跑出了一整套 C++ ↔ GDScript 的資料傳輸慣例。本文的立場是：**共用層 = 把 mapcore 已驗證可行的慣例抽離成可被第二、第三個模組複用的形狀**，而不是另起爐灶。

`CONCEPT.md` 第 14~36 行的架構示意（GDScript → GDExtension 橋接層 → gamecore_cpp 共用核心 → 各功能 C++ 庫）方向正確，但其示意把共用層畫在「橋接層之下、各功能庫之上」。實際上 mapcore 的分層證明共用層需要拆成**兩塊**（見後文「共用層應抽出的共通概念」）：一塊是純 C++ 的領域型別（`mapcore::Coord` 那一層），另一塊是 C++ ↔ Variant 的轉換慣例（`MapCoreMapData` 那一層）。這兩塊的依賴規則不同，混為一談會埋下循環依賴的風險。

---

## 既有現況：mapcore 是事實上的第一個模組

mapcore 的分層（由下到上）：

```
mapcore_cpp_square/          純 C++ 領域庫，零 Godot 依賴
  include/mapcore/grid.hpp     → struct Coord { int x, y; }
  include/mapcore/map.hpp      → struct Tile / class TileMap / namespace TerrainType
  include/mapcore/features.hpp → struct WorldFeature / WorldFeatures
  include/mapcore/generation/pipeline.hpp → struct WorldGenResult
        │  （SConstruct 第 27~41 行直接編進 GDExtension）
        ▼
mapcore_godot/src/           GDExtension 橋接層（依賴 godot-cpp + 上面那層）
  map_data.h / .cpp          → class MapCoreMapData : public Resource
  map_generator.h / .cpp     → class MapCoreGenerator : public Node
  terrain_mesh_builder.*     → class MapCoreTerrainMeshBuilder : public RefCounted
  procgen_mesh_builder.*     → class MapCoreProcGenMeshBuilder : public RefCounted
  world_map_2d_renderer.*    → class MapCoreWorldMap2DRenderer : public RefCounted
  register_types.cpp         → ClassDB 註冊入口
```

### 純 C++ 層已定義的領域型別

| 型別 | 定義位置 | 內容 |
|------|---------|------|
| `Coord` | `mapcore_cpp_square/include/mapcore/grid.hpp` 第 14~28 行 | `struct Coord { int x{0}, y{0}; }`，含 `operator+/-/*/==/!=`、`neighbor()`、`neighbors()`，並在第 41~50 行為 `std::hash<Coord>` 特化（可當 `unordered_map` key） |
| 四方向常數 | `grid.hpp` 第 30~32 行 | `extern const std::array<Coord,4> DIRECTIONS;`，順序鎖死 `0=E 1=N 2=W 3=S`（註解第 30 行明言此順序被 rivers 的 edge ownership 依賴） |
| `TerrainType` | `mapcore_cpp_square/include/mapcore/map.hpp` 第 15~27 行 | `namespace TerrainType` 內 11 個 `constexpr uint16_t` 常數（OCEAN=0 … LAKE=10） |
| `Hilliness` | `map.hpp` 第 30~37 行 | `enum class Hilliness : uint8_t`，6 級（UNDEFINED=0 … IMPASSABLE=5） |
| `Tile` | `map.hpp` 第 39~48 行 | POD：`uint16_t terrain` + `uint32_t rivers`（兩條邊 8-bit 流量打包）+ `Hilliness hilliness` + `int32_t feature_id`（-1 = 無）+ `float water_depth` |
| `TileMap` | `map.hpp` 第 53~87 行 | flat `std::vector<Tile>`，索引 `y*width+x`；`get(Coord)`、`tile_at(x,y)`、`in_bounds()`、`for_each()`；`std::shared_ptr<WorldFeatures> features` |
| `WorldFeature` | `mapcore_cpp_square/include/mapcore/features.hpp` 第 13~20 行 | `int id` + `std::string feature_type` + `std::string name` + `std::vector<Coord> tiles` + `Coord center` + `int size` |
| `WorldGenResult` | `mapcore_cpp_square/include/mapcore/generation/pipeline.hpp` 第 21~33 行 | 所有生成中間產物的聚合：`TileMap` + `heightmap` + `moisture` + `temperature_celsius` + `rainfall_mm` + `extra_noise` map + `TerrainRegistry*` + `std::optional<uint64_t> seed` |

關鍵觀察：**這層完全沒有「實體 ID（EntityID）」與「資源量（ResourceAmount）」**。mapcore 是地圖生成模組，它的「最接近實體」的概念是 `WorldFeature::id`（命名大區域的索引，`int`，由 `WorldFeatures::features` 的下標決定，見 `features.hpp` 第 4 行註解「Tile.feature_id 直接索引 features_[]」）。CONCEPT.md 第 51~55 行假設的 `using EntityID = uint64_t` 在現有程式碼中**沒有任何先例**——這點對後文「待決定」很重要。

### GDExtension 橋接層已建立的 API 慣例

`MapCoreMapData`（`map_data.h` 第 14 行起，繼承 `Resource`）是慣例的集中體現。歸納 `map_data.h` 第 28~76 行宣告 + `map_data.cpp` 第 20~67 行 `_bind_methods` 的綁定，可看出**四種回傳形狀**：

| 慣例形狀 | 範例方法（map_data.h 行號）| GDScript 型別 | 對應 C++ 來源 |
|---------|------------------|--------------|--------------|
| **單格純量查詢** | `get_terrain(x,y)` 第 34 行、`get_temperature(x,y)` 第 38 行 | `int` / `float` | `Tile` 欄位、flat vector 索引 |
| **批次純量陣列** | `get_terrain_array()` 第 42 行、`get_height_array()` 第 43 行 | `PackedInt32Array` / `PackedFloat32Array`（flat row-major `y*w+x`，見 map_data.cpp 第 125~136 行） | 整張 `TileMap` / `heightmap` |
| **複雜物件列表** | `get_all_river_edges()` 第 51 行 | `TypedArray<Dictionary>`（每個 dict `{pos:Vector2i, dir:int, strength:int}`，見 map_data.cpp 第 178~190 行） | `iter_river_edges` 回呼 |
| **單一複雜物件** | `get_feature_info(id)` 第 56 行 | `Dictionary`（`{name,type,center,size}`，見 map_data.cpp 第 205~215 行） | `WorldFeature` |
| **座標列表** | `find_path(start,goal)` 第 59 行 | `TypedArray<Vector2i>`（**注意非 Packed**，見下文 API 慣例節） | `mapcore::astar` 回傳 |
| **持久化資料本體** | `MapCoreMapData` 本身 | `Resource` 子類（`Ref<MapCoreMapData>`） | 持有 `std::optional<WorldGenResult>` |

另外三項已成形的慣例：

1. **常數對外用 `BIND_CONSTANT`**：`map_data.cpp` 第 56~66 行把 11 個 `static constexpr int TERRAIN_*`（宣告於 `map_data.h` 第 65~75 行）綁出去，GDScript 寫 `MapCoreMapData.TERRAIN_OCEAN`。注意 C++ 核心層的 `TerrainType::OCEAN` 是 `uint16_t`，到了橋接層被重新宣告成 `int`——這是 Variant 只支援 `int64_t` 而非 `uint16_t` 的必然轉換。
2. **生成走 Node + 非同步 signal**：`MapCoreGenerator`（`map_generator.h` 第 9 行，繼承 `Node`）用 `generate_async()` 開 thread，完成後 `call_deferred("_on_thread_done", data)` 再 `emit_signal("generation_completed", data)`（`map_generator.cpp` 第 139、147~148 行）。signal 在 `_bind_methods` 用 `ADD_SIGNAL(MethodInfo("generation_completed", PropertyInfo(Variant::OBJECT, "data", PROPERTY_HINT_RESOURCE_TYPE, "MapCoreMapData")))` 宣告（同檔第 20~21 行）。
3. **資料本體跨幀靠 `Resource` 引用計數**：`WorldGenResult` 在 worker thread 算完後 `std::move` 進 `MapCoreMapData::result_`（`map_generator.cpp` 第 137 行），再以 `Ref<MapCoreMapData>` 傳回主執行緒。因為是 `Resource`，Godot 的引用計數會接手生命週期——這正是 CONCEPT.md 第 79 行「跨幀持有的資料封裝為 Resource」的實證。
4. **無狀態工具用 `RefCounted`**：三個 builder/renderer 都繼承 `RefCounted`（不掛場景樹，GDScript 直接 `.new()`），方法為「吃 `Ref<MapCoreMapData>` 吐 `ArrayMesh`/`Image`」的純函式形態（見 `terrain_mesh_builder.h` 第 10、21 行、`world_map_2d_renderer.h` 第 11、19 行）。

---

## 共用層應抽出的共通概念

以下逐項說明「mapcore 已驗證可行、第二個模組大機率會重複用到」的概念，並給型別建議。原則：**只抽真的會跨模組共用的，不要為了對稱而硬塞**。

### 1. 座標（Coord）— 應抽，但要分清兩種

- **C++ 領域座標**：mapcore 已有 `mapcore::Coord`（`grid.hpp` 第 14 行）。它帶有方格特有的 `neighbor()`/`DIRECTIONS`（4 方向、`0=E 1=N 2=W 3=S`），這些是**方格地圖專屬語意**，不該放進「所有模組共用」的型別。
  - **建議**：共用層只抽一個極簡的 `gamecore::Coord { int x, y; }`（外加 `operator==` 與 `std::hash` 特化），把 `neighbor()`/`DIRECTIONS` 留在 mapcore。`mapcore::Coord` 可改為「`= gamecore::Coord` 的別名 + 自由函式 `neighbor(Coord, int)`」，避免戰鬥/經濟模組被迫吞下方格鄰居語意。理由：座標的「(x,y) 整數對」是真共用，但「鄰居規則」是地圖領域知識。
- **GDScript 邊界座標**：到 Variant 層一律用 `Vector2i`（mapcore 在 `find_path` 的回傳、`get_all_river_edges` 的 `pos` key 都已用 `Vector2i`，見 map_data.cpp 第 184、231 行）。
  - **建議**：把「`mapcore::Coord` ↔ `Vector2i`」的轉換寫成共用 inline helper（`to_vec2i(Coord)` / `to_coord(Vector2i)`），放在橋接層共用標頭，避免每個模組各寫一遍。

### 2. 實體 ID（EntityID）— 暫不抽，先觀察

- 現況：**mapcore 完全沒有 EntityID**。它唯一的「ID」是 `WorldFeature::id`（`int`，`features.hpp` 第 14 行），且語意是「`WorldFeatures::features` 陣列下標」，並非全域唯一實體。
- CONCEPT.md 第 51~53 行的 `using EntityID = uint64_t; constexpr EntityID NULL_ENTITY = 0;` 是合理的**未來方向**，但沒有任何現役程式碼在用。Variant 的整數是 `int64_t`，把 `uint64_t` 傳到 GDScript 會有高位元號截斷風險（超過 2^63 會變負數）。
  - **建議**：**先不要進共用層**。等到第二個真的有「會被建立/銷毀/跨模組引用的實體」的模組（如生物 `CreatureGDExt`）出現時，再從那個模組的實際需求倒推 EntityID 的形狀。若屆時要抽，型別建議用 `int64_t`（與 Variant 對齊、避免截斷）而非 `uint64_t`，並把「ID 分配器」做成共用層的一個小元件（見「待決定」第 2 項）。理由：照本倉庫「從可運作程式碼倒推抽象」的原則，沒有先例的型別不該預先固化。

### 3. 資源量（ResourceAmount）— 暫不抽

- 現況：mapcore 沒有任何「貨幣/材料數量」概念。CONCEPT.md 第 55 行的 `using ResourceAmount = int32_t` 同樣零先例。
  - **建議**：**先不抽**，等經濟/物品模組出現再說。`int32_t` 的選型本身合理（夠大、與 Variant `int` 相容），但「資源量」常伴隨「資源種類 ID」「上下限 clamp」「溢位策略」等領域規則，這些規則由第一個用到的模組定義才不會抽錯。

### 4. 查詢回傳慣例 — 應抽（這是最有價值的共用資產）

mapcore 已跑出的「四形狀 + 兩生命週期」慣例（見上一節）就是共用層**最該標準化**的東西，因為它直接決定 GDScript 工程師的學習成本。這部分不是抽「型別」，而是抽「規則文件 + 少量 helper」。詳見下一節「統一 API 慣例」。

### 5. Dictionary key 詞彙表 — 應抽

- 現況：mapcore 的 dict 已用 `pos` / `dir` / `strength`（河流）、`name` / `type` / `center` / `size`（feature）等 key（map_data.cpp 第 184~186、210~213 行）。CONCEPT.md 第 78 行已要求「結構不固定的物件用 Dictionary，但需在文件中明確定義 key」。
  - **建議**：在共用層維護一份「跨模組共用 key 詞彙表」（純文件 + 可選的 `constexpr StringName` 常數），約定如 `pos`（一律 `Vector2i`）、`center`（一律 `Vector2i`）、`id`（一律 `int`）等通用 key 的型別與語意。各模組私有的 key 仍由各模組文件定義。理由：key 拼字/型別不一致是 `Dictionary` 介面最易出錯處，集中約定成本極低、收益高。

### 6. 種子 / 決定性（seed）— 應抽為慣例

- 現況：mapcore 用 `std::optional<uint64_t> seed`（`pipeline.hpp` 第 29 行），到 GDScript 用 `int64_t`（`get_seed_used`，map_data.h 第 31 行；`MapCoreGenerator::seed_` 也是 `int64_t`，map_generator.h 第 17 行，`0 = 每次隨機`）。procgen mesh 也用 `int seed` 做確定性 hash（`procgen_mesh_builder.h` 第 24 行）。
  - **建議**：共用層約定「對外 seed 一律 `int64_t`、`0 = 隨機」的慣例（純文件約定，不需共用型別）。理由：多個模組都會需要「可重現」能力，統一語意可讓存檔/重現流程一致。

---

## 統一 API 慣例

把 mapcore 的實作整理成可被新模組照抄的規則。

### PackedArray — 同型大量純量

- **適用**：一次回傳整張地圖/整個陣列的同型數值（地形 enum、高度、溫度…）。
- **型別對照（以 godot-cpp 實際存在的標頭為準，位於 `mapcore_godot/godot-cpp/gen/include/godot_cpp/variant/`）**：
  - `vector<int>` → `PackedInt32Array`（`packed_int32_array.hpp`）—— enum 陣列，如 `get_terrain_array()`。
  - `vector<float>` → `PackedFloat32Array`（`packed_float32_array.hpp`）—— 數值場，如高度/溫度/降雨。
  - mesh 頂點 → `PackedVector3Array`（`packed_vector3_array.hpp`）、頂點色 → `PackedColorArray`（`packed_color_array.hpp`）—— terrain/procgen mesh builder 內部用。
- **重要事實校正**：CONCEPT.md 第 69 行建議「`vector<Coord>` → `PackedVector2iArray`」用於路徑，**但本 godot-cpp 檢出版本沒有 `packed_vector2i_array.hpp`**（`gen/include/godot_cpp/variant/` 下只有 `packed_vector2_array.hpp`，是 float 版的 `PackedVector2Array`）。這正是 mapcore 的 `find_path` 改用 `TypedArray<Vector2i>` 而非 Packed 版的原因（map_data.h 第 59 行、map_data.cpp 第 219~233 行）。
  - **慣例結論**：整數座標列表用 `TypedArray<Vector2i>`；只有當座標可接受浮點時才用 `PackedVector2Array`。**不要**在文件裡承諾不存在的 `PackedVector2iArray`。
- **記憶體佈局約定**：批次陣列一律 flat row-major `y*width+x`（map_data.cpp 第 132~134 行已如此），GDScript 端靠 `get_width()` 還原二維。

### TypedArray<Dictionary> — 不定長的複雜物件列表

- **適用**：每個元素是「欄位不固定/含多型別」的物件，且數量不定。範例：`get_all_river_edges()` 回傳每條河流邊一個 dict（map_data.cpp 第 178~190 行）。
- **代價**：每個 `Dictionary` 都有 Variant 裝箱開銷，**不適合幾萬筆以上的熱資料**。河流邊只有數百~數千條，可接受；整張地圖逐格絕不可用此形狀（要用 PackedArray）。
- **約定**：dict 的 key 必須在模組文件列出，型別固定，並盡量複用共用 key 詞彙表（見上節第 5 點）。

### Dictionary — 單一複雜查詢結果

- **適用**：查單一物件、欄位異質。範例：`get_feature_info(id)` 回 `{name,type,center,size}`（map_data.cpp 第 205~215 行）。
- **失敗約定**：查無資料回**空 Dictionary**（map_data.cpp 第 206~209 行），GDScript 用 `is_empty()` 判斷；單格純量查詢則回「哨兵值」（如 `get_temperature` 越界回 `-999.0f`、`get_terrain` 越界回 `TERRAIN_OCEAN`，見 map_data.cpp 第 84~85、109~110 行）。**建議**把這套「失敗回空容器 / 哨兵值」的約定明文化進共用慣例。

### Resource subclass — 跨幀持久 / 需引用計數的資料本體

- **適用**：要被多個節點持有、要跨幀存活、要能存檔的資料。範例：`MapCoreMapData : Resource` 持有整個 `WorldGenResult`（map_data.h 第 14、17 行）。
- **理由**：`Resource` 繼承自 `RefCounted`，生命週期由引用計數自動管理；非同步生成把資料 `std::move` 進 Resource 後即可安全地跨 thread/跨幀傳遞（map_generator.cpp 第 137~139、147~148 行）。
- **約定**：純粹「吃資料吐衍生物」的無狀態工具改用 `RefCounted`（如三個 builder）；要掛在場景樹、要收引擎回呼/驅動 thread 的用 `Node`（如 `MapCoreGenerator`）。

### 一張選型決策表

| 你要回傳的東西 | 用 | 不要用 |
|--------------|----|-------|
| 整張地圖的同型數值 | `PackedInt32/Float32Array` | `Array` / 逐格 `Dictionary` |
| 整數座標路徑/列表 | `TypedArray<Vector2i>` | `PackedVector2iArray`（此 godot-cpp 無此型別）|
| 浮點座標列表 | `PackedVector2Array` | — |
| 數百~數千筆的異質物件列表 | `TypedArray<Dictionary>` | PackedArray（裝不下異質欄位）|
| 數萬筆以上熱資料 | 拆成多個 PackedArray（SoA） | `TypedArray<Dictionary>`（裝箱太貴）|
| 單一查詢結果 | `Dictionary`（查無回空）| 多個 out 參數 |
| 跨幀/可存檔的資料本體 | `Resource` 子類 | 裸指標 / `Object*` |
| 無狀態純函式工具 | `RefCounted` | `Node`（不必掛樹）|
| 要掛場景樹/驅動 thread/收回呼 | `Node` | `RefCounted` |
| enum 常數對外 | `BIND_CONSTANT`（值用 `int`）| GDScript 端硬寫魔術數字 |

---

## 模組如何依賴共用層

關鍵是**把共用層拆成兩塊、各有獨立的依賴方向**，否則很容易做出循環依賴。

```
                ┌─────────────────────────────────────────────┐
   GDScript ───►│  Variant 慣例（規則文件 + StringName 詞彙表  │
                │  + Coord↔Vector2i helper）                   │  ← 共用層 B
                └───────────────▲─────────────────────────────┘
                                │ 依賴 godot-cpp
   ┌───────────────────┐  ┌─────┴──────────┐
   │ MapCoreGDExt 橋接 │  │ CreatureGDExt …│   各模組的 GDExtension 橋接層
   └─────────▲─────────┘  └──────▲─────────┘
             │ 依賴             │
   ┌─────────┴─────────┐  ┌──────┴─────────┐
   │ mapcore_cpp_square│  │ creature_cpp … │   各模組純 C++ 領域庫
   └─────────▲─────────┘  └──────▲─────────┘
             │ 依賴             │
        ┌────┴──────────────────┴────┐
        │ gamecore::Coord 等領域中性型別 │  ← 共用層 A（純 C++，零 Godot 依賴）
        └─────────────────────────────┘
```

依賴規則（單向、無環）：

1. **共用層 A（純 C++ 領域型別）**：`gamecore::Coord`、未來的 `EntityID` 等。**零 Godot 依賴**，可被任何純 C++ 領域庫 include。它是最底層，不依賴任何人。
2. **各模組純 C++ 領域庫**（mapcore_cpp_square、未來 creature_cpp）：依賴共用層 A，**彼此之間用 C++ struct 直接溝通，不繞 GDScript**（CONCEPT.md 第 83~94 行的「✅ C++ 直接呼叫 / ❌ 繞道 GDScript」原則正確）。要注意的是：跨模組直接 include 對方標頭會產生模組間耦合，建議只在「明確相依」的方向上允許（如戰鬥依賴地圖，地圖不依賴戰鬥），避免雙向 include。
3. **各模組 GDExtension 橋接層**：依賴 godot-cpp、自己的領域庫、以及共用層 B（Variant 慣例）。橋接層之間**不應互相依賴**（各自只在 `register_types.cpp` 註冊自己的 class，如 mapcore 的做法，見 register_types.cpp 第 14~22 行）。
4. **共用層 B（Variant 慣例）**：依賴 godot-cpp。它提供 `Coord↔Vector2i` helper、共用 `StringName` key 常數、以及（純文件的）回傳形狀規則。它**不依賴任何領域庫**（否則就把地圖知識洩漏給所有模組）。

避免循環的兩條鐵律：
- **領域庫絕不 include 橋接層**（map_data.h 可以 include `mapcore/...`，但 `mapcore/map.hpp` 絕不能 include `map_data.h`）。mapcore 現況已遵守此向（map_data.h 第 10 行 include `mapcore/generation/pipeline.hpp`，反向不存在）。
- **共用層 A 與 B 互不依賴**：A 是純 C++、B 是 Godot 慣例，兩者只在「橋接層內」交會（橋接層同時 include 兩者）。

---

## 漸進落地路徑

從 mapcore 現況推進到有共用層，建議**小步走、每步可驗證**，不要一次大重構。

**階段 0（現況）**：只有 mapcore，慣例隱含在 `map_data.*` 裡，未抽出。

**階段 1：把慣例寫成文件（零程式碼改動）**
- 把本文「統一 API 慣例」那節變成一份各模組必讀的規範（可放 `others/gamecore/specs/` 或共用層 README）。
- 此時不動任何 `.cpp`/`.h`。新模組照文件抄即可，先用文件統一，再考慮抽程式碼。

**階段 2：抽 `gamecore::Coord`（共用層 A 的種子）**
- 新增 `gamecore/coord.hpp`（純 C++，零 Godot 依賴）：`struct Coord { int x, y; }` + `operator==` + `std::hash`。
- 把 `mapcore::Coord` 改寫為「`using Coord = gamecore::Coord;` + 把 `neighbor()`/`DIRECTIONS` 改成自由函式或留在 mapcore 命名空間」。
- 用 mapcore 既有測試（`mapcore_cpp_square/tests/`）驗證行為不變。**這步是純 C++、有測試保護，風險最低，適合當第一刀。**

**階段 3：抽 `Coord↔Vector2i` helper + key 詞彙表（共用層 B 的種子）**
- 新增橋接層共用標頭（如 `gamecore_godot_common.hpp`）：放 `to_vec2i`/`to_coord` inline 函式與共用 `StringName` 常數（`pos`/`center`/`id`…）。
- 把 `map_data.cpp` 中手寫的 `Vector2i(c.x, c.y)`（第 184、211、231 行）改為呼叫 helper。行為不變、純重構。

**階段 4：第二個模組落地，反向驗證共用層**
- 真正寫第二個模組（如生物）時，**只允許複用共用層 A/B 已有的東西**；凡是「想抽但 mapcore 沒先例」的（EntityID、ResourceAmount），等這個模組明確需要時才回頭加進共用層 A。
- 這步是檢驗共用層抽象是否正確的唯一可靠方法：能被第二個模組無痛複用，才算抽對。

**階段 5：依需求補 EntityID 分配器 / 序列化慣例**
- 視第二個模組是否需要全域唯一實體、是否需要存檔，再決定是否進入「待決定」清單裡的 EntityID 與序列化議題。

---

## 待決定（逐項建議）

對應 CONCEPT.md 第 109~114 行「待設計」四項，逐項給出具體建議。

1. **`gamecore/types.h` 的實際位置與 CMakeLists 整合方式**
   - **建議**：拆成兩個檔、放兩個地方，不要叫 `types.h` 一鍋燴。純 C++ 領域型別放 `others/gamecore/gamecore_cpp/include/gamecore/coord.hpp`（與 `mapcore_cpp_square` 平級的新庫）；Godot 慣例 helper 放各 GDExtension 共用的 `gamecore_godot_common.hpp`。整合方式照 mapcore 現成做法——`mapcore_godot/SConstruct` 第 17~22 行用 `CPPPATH` 加 include 路徑、第 27~50 行把核心 `.cpp` 直接編進 GDExtension；新共用庫同樣用 `CPPPATH` 暴露標頭即可（`Coord` 全 inline 可不需 `.cpp`）。理由：mapcore 已證明「純標頭核心 + SCons 直接編入」可行，沿用最省事；分兩檔是為了守住「共用層 A 零 Godot 依賴」的鐵律。

2. **EntityID 的分配機制（集中分配 vs 各模組自管）**
   - **建議**：**現在不決定**，因為沒有任何模組在用 EntityID（mapcore 只有局部的 `WorldFeature::id`）。等第一個有實體的模組出現時，採「集中分配器」：共用層 A 提供一個 `gamecore::IdAllocator`（單純遞增的 `int64_t` 計數器 + `NULL_ENTITY = 0`），各模組向它要 ID。理由：集中分配能保證跨模組唯一（這是 CONCEPT 第 7~8 行「跨模組資料交換」的前提）；用 `int64_t` 而非 CONCEPT 第 52 行的 `uint64_t` 是為了與 Variant 整數對齊、避免高位元截斷成負數。各模組自管會讓「同一個 ID 在不同模組指不同東西」，違背共用初衷。

3. **跨模組 C++ 介面的頭文件組織（單一 `gamecore/api.h` vs 分散）**
   - **建議**：**分散，按領域分檔**（`gamecore/coord.hpp`、未來 `gamecore/entity.hpp`…），不要單一 `api.h`。理由：mapcore 自己就是分散組織（`grid.hpp`/`map.hpp`/`features.hpp`/`generation/pipeline.hpp` 各司其職，見 `mapcore_cpp_square/include/mapcore/`），編譯依賴清晰、改一處不會牽動全部。單一 `api.h` 會讓任何模組改動都觸發全量重編，且鼓勵不必要的耦合。若需要「一次引入全部」的便利，可額外提供一個只 `#include` 各分檔的 `gamecore/all.hpp`，但它不是唯一入口。

4. **序列化格式（存檔讀檔）：JSON / binary / Godot `.tres`**
   - **建議**：**優先用 Godot `.tres`（`Resource` 序列化）**，因為資料本體已經是 `Resource` 子類（`MapCoreMapData`）。理由：(a) `Resource` 天生可被 Godot 的 `ResourceSaver`/`ResourceLoader` 存成 `.tres`/`.res`，零額外程式碼；(b) 與現有「跨幀資料封裝為 Resource」慣例一致（CONCEPT 第 79 行、map_data.cpp 的 Resource 設計）；(c) 編輯器可直接檢視。**但有前提**：目前 `MapCoreMapData` 的真正資料藏在 C++ 側的 `std::optional<WorldGenResult> result_`（map_data.h 第 17 行），它**不是** Godot `_bind` 的屬性，預設不會被 `.tres` 序列化。要走這條路，需把要存的欄位（或一個壓縮過的 blob，如把整張 `TileMap` 打包成 `PackedByteArray`）用 `ADD_PROPERTY` 暴露成 Resource 屬性。大地圖建議存 binary blob（`PackedByteArray`）而非逐格 dict，避免 `.tres` 文字膨脹。JSON 僅建議用於「需要人類可讀/跨工具」的小型設定，不適合整張地圖這類熱資料。

---

*記錄時間：2026-05-23*
*狀態：架構設計分析；共用層尚未實作，本文給出從 mapcore 現況倒推的抽取建議與漸進落地路徑*
