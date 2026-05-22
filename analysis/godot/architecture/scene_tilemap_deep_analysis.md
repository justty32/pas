# TileMapLayer / TileSet 深度分析

> 對應原始碼：`scene/2d/tile_map_layer.h/cpp`, `scene/resources/2d/tile_set.h/cpp`

---

## 1. 三層資料階層

Godot 4 的磁磚系統由三個層次組成，職責分明：

```
TileSet（Resource）
  ├─ 全域設定：tile_size、物理層、導航層、地形集、自訂資料層定義
  └─ sources: HashMap<int, Ref<TileSetSource>>
        └─ TileSetAtlasSource（最常見的 Source 類型）
              ├─ texture: Ref<Texture2D>       — 整張 Atlas 貼圖
              ├─ texture_region_size           — 每格大小（像素）
              └─ tiles: HashMap<Vector2i, TileAlternativesData>
                    └─ alternatives: HashMap<int, TileData*>
                          └─ TileData          — 每個 alternative 的物理/渲染屬性
```

- **TileSet**：定義「這個磁磚集有哪些 Sources、哪些物理層、地形規則」——是模板/配置。
- **TileSetAtlasSource**：管理一張 Atlas 貼圖，知道如何切割出各個磁磚，以及每個磁磚的 alternatives。
- **TileData**：每個具體磁磚 alternative 的執行時資料（碰撞多邊形、z-index、material、自訂資料等）。

---

## 2. TileMapCell union——8 bytes 的緊湊 Key

`scene/resources/2d/tile_set.h:60-111`

```cpp
union TileMapCell {
    struct {
        int16_t source_id;         // 指向 TileSet 中的哪個 Source（2 bytes）
        int16_t coord_x;           // Atlas 格子座標 X（2 bytes）
        int16_t coord_y;           // Atlas 格子座標 Y（2 bytes）
        int16_t alternative_tile;  // Alternative ID（含翻轉位元）（2 bytes）
    };
    uint64_t _u64t;                // 整體 8 bytes，可直接作為 hash key

    static uint32_t hash(const TileMapCell &p_hash) {
        return hash_one_uint64(p_hash._u64t);  // 一次 64-bit hash，極快
    }
};
```

**設計要點**：
- Union 讓 `_u64t` 與四個 int16 共用記憶體。讀取欄位用具名成員，整體 hash 用 `_u64t`——不需要複合 hash，零開銷。
- `source_id = -1`、`coord = (-1,-1)`、`alternative = -1` 三個都等於 `INVALID` 時代表「空格子」。
- `set_atlas_coords()` / `get_atlas_coords()` 是薄包裝，把 `Vector2i` 拆入 `coord_x/coord_y`。

### 2.1 Alternative ID 中的翻轉位元

`scene/resources/2d/tile_set.h:628-634`

```cpp
enum TransformBits {
    TRANSFORM_FLIP_H    = 1 << 12,   // 水平翻轉
    TRANSFORM_FLIP_V    = 1 << 13,   // 垂直翻轉
    TRANSFORM_TRANSPOSE = 1 << 14,   // 旋轉 90° 等效
};
// 取出原始 alternative ID（去掉翻轉位元）
static const int16_t UNTRANSFORM_MASK =
    ~(TRANSFORM_FLIP_H + TRANSFORM_FLIP_V + TRANSFORM_TRANSPOSE);
```

`alternative_tile` 的低 12 bits 是真正的 alternative ID（使用者定義的額外磁磚變體），高 3 bits（12–14）是翻轉資訊。這讓翻轉變體不需要額外儲存，節省記憶體。

取得真實 alternative ID：`alternative_tile & UNTRANSFORM_MASK`。

---

## 3. CellData——多系統整合的運行時記錄

`scene/2d/tile_map_layer.h:104-171`

```cpp
struct CellData {
    Vector2i coords;               // 格子座標（邏輯位置）
    TileMapCell cell;              // 磁磚識別資料（source + atlas + alternative）

    // === 渲染系統 ===
    Ref<RenderingQuadrant> rendering_quadrant;
    SelfList<CellData> rendering_quadrant_list_element; // 侵入式鏈結串列節點

    LocalVector<LocalVector<RID>> occluders; // 每個 occlusion layer 的 RID

    // === 物理系統（#ifndef PHYSICS_2D_DISABLED）===
    Ref<PhysicsQuadrant> physics_quadrant;
    SelfList<CellData> physics_quadrant_list_element;

    // === 導航系統 ===
    LocalVector<RID> navigation_regions;

    // === 場景磁磚 ===
    String scene;  // 若是 Scene Tile，儲存場景路徑

    // === 執行時快取 ===
    TileData *runtime_tile_data_cache = nullptr; // _use_tile_data_runtime_update() 的輸出

    // === Dirty 系統 ===
    SelfList<CellData> dirty_list_element; // 侵入式節點：在 TileMapLayer::dirty.cell_list 中
};
```

**侵入式鏈結串列（SelfList）**：`SelfList<CellData>` 節點**嵌在 CellData 內部**，避免動態分配。當 CellData 加入某個 quadrant 的 `cells` 鏈結串列時，不需要 `new` 一個額外的節點——節點本身就是 `CellData` 的一個欄位。`in_list()` 可檢查此 CellData 是否已在某個串列中，防止重複插入。

CellData 的複製建構子（L148）**只複製資料欄位，不複製 SelfList 節點**——因為 SelfList 節點的所有者是 CellData 自身，複製後的節點應該是全新的，不屬於任何串列。

---

## 4. TileMapLayer 核心狀態

`scene/2d/tile_map_layer.h:388-421`

```cpp
class TileMapLayer : public Node2D {
    // === 主要儲存 ===
    HashMap<Vector2i, CellData> tile_map_layer_data; // coords → CellData

    // === Quadrant 分塊系統 ===
    int rendering_quadrant_size = 16;   // N×N 格為一個 quadrant（預設 16）
    int physics_quadrant_size = 16;
    HashMap<Vector2i, Ref<RenderingQuadrant>> rendering_quadrant_map;
    HashMap<Vector2i, Ref<PhysicsQuadrant>> physics_quadrant_map;

    // === Dirty 旗標 ===
    struct {
        bool flags[DIRTY_FLAGS_MAX] = { false }; // 層級屬性的骯髒旗標
        SelfList<CellData>::List cell_list;       // 已修改格子的侵入式鏈結串列
    } dirty;
};
```

Quadrant 座標 = `floor(cell_coords / quadrant_size)`，是一個整數 Vector2i。

---

## 5. DirtyFlags 枚舉

`scene/2d/tile_map_layer.h:347-382`

```cpp
enum DirtyFlags {
    DIRTY_FLAGS_LAYER_ENABLED = 0,
    DIRTY_FLAGS_LAYER_IN_TREE,
    DIRTY_FLAGS_LAYER_LOCAL_TRANSFORM,
    DIRTY_FLAGS_LAYER_VISIBILITY,
    DIRTY_FLAGS_LAYER_Y_SORT_ENABLED,      // ← 觸發全量重建
    DIRTY_FLAGS_LAYER_Y_SORT_ORIGIN,
    DIRTY_FLAGS_LAYER_X_DRAW_ORDER_REVERSED,
    DIRTY_FLAGS_LAYER_RENDERING_QUADRANT_SIZE, // ← 觸發全量重建
    DIRTY_FLAGS_LAYER_COLLISION_ENABLED,
    DIRTY_FLAGS_LAYER_PHYSICS_QUADRANT_SIZE,
    // ... 共 28 個旗標
    DIRTY_FLAGS_TILE_SET,                  // ← 觸發全量重建
    DIRTY_FLAGS_MAX,
};
```

`dirty.flags[X] = true` 代表「層級的屬性 X 已改變，需要在下次更新時處理」。`dirty.cell_list` 則記錄哪些**個別格子**被修改，用於增量更新。

---

## 6. set_cell() 的精確流程

`scene/2d/tile_map_layer.cpp:2777-2820`

```cpp
void TileMapLayer::set_cell(const Vector2i &p_coords, int p_source_id,
                             const Vector2i &p_atlas_coords, int p_alternative_tile) {
    // 1. 查找或不存在
    HashMap<Vector2i, CellData>::Iterator E = tile_map_layer_data.find(p_coords);

    // 2. 部分 INVALID 視為完全 INVALID（三者必須同時有效或同時無效）
    if (/* 三者有一無效但非全部無效 */) {
        source_id = INVALID_SOURCE;
        atlas_coords = INVALID_ATLAS_COORDS;
        alternative_tile = INVALID_TILE_ALTERNATIVE;
    }

    // 3. 早期返回①：格子不存在且要設為空 → 無需任何操作
    if (!E) {
        if (source_id == TileSet::INVALID_SOURCE) return;
        // 建立新的 CellData 並插入
        CellData new_cell_data;
        new_cell_data.coords = p_coords;
        E = tile_map_layer_data.insert(p_coords, new_cell_data);
    } else {
        // 早期返回②：格子存在但值未改變 → 無需任何操作
        if (E->value.cell.source_id == source_id &&
            E->value.cell.get_atlas_coords() == atlas_coords &&
            E->value.cell.alternative_tile == alternative_tile) return;
    }

    // 4. 更新 cell 欄位
    TileMapCell &c = E->value.cell;
    c.source_id = source_id;
    c.set_atlas_coords(atlas_coords);
    c.alternative_tile = alternative_tile;

    // 5. 加入 dirty cell list（侵入式：若 dirty_list_element 已在串列中則跳過）
    if (!E->value.dirty_list_element.in_list()) {
        dirty.cell_list.add(&(E->value.dirty_list_element));
    }

    // 6. 排隊更新
    _queue_internal_update();
    used_rect_cache_dirty = true;
}
```

`erase_cell()` 就是 `set_cell(coords, INVALID, INVALID, INVALID)` 的別名。

---

## 7. Quadrant 結構詳解

### 7.1 RenderingQuadrant

`scene/2d/tile_map_layer.h:206-235`

```cpp
class RenderingQuadrant : public RefCounted {
    Vector2i quadrant_coords;                  // Quadrant 在 quadrant 空間的座標
    SelfList<CellData>::List cells;            // 此 quadrant 內所有格子的侵入式鏈結串列
    List<RID> canvas_items;                    // 一個 quadrant 可能有多個 canvas_item！
    Vector2 canvas_items_position;             // 所有 canvas_item 的共同基準位置

    SelfList<RenderingQuadrant> dirty_quadrant_list_element; // 在更新佇列中的節點
};
```

**關鍵**：`canvas_items` 是 `List<RID>`，不是單一 RID。同一個 quadrant 內，如果不同格子使用了不同的 `Material` 或不同的 `z_index`，就需要建立多個 canvas_item——每個 canvas_item 代表一個「相同 material + 相同 z_index」的群組。

### 7.2 PhysicsQuadrant

`scene/2d/tile_map_layer.h:238-330`

```cpp
class PhysicsQuadrant : public RefCounted {
    Vector2i quadrant_coords;
    SelfList<CellData>::List cells;

    // bodies 依 PhysicsBodyKey 分組——不同物理層、不同速度的格子生成不同剛體
    HashMap<PhysicsBodyKey, PhysicsBodyValue, PhysicsBodyKeyHasher> bodies;
    LocalVector<Ref<ConvexPolygonShape2D>> shapes;
};

struct PhysicsBodyKey {
    int physics_layer;
    Vector2 linear_velocity;
    real_t angular_velocity;
    bool one_way_collision;
    real_t one_way_collision_margin;
    int64_t y_origin; // 僅 one_way_collision=true 時使用，避免垂直方向合併
};
```

設計目的：同一個 quadrant 內，屬性相同的格子會合併成**一個物理剛體**（多個碰撞形狀），減少 PhysicsServer 的 Body 數量。

---

## 8. _rendering_update() 的兩路更新邏輯

`scene/2d/tile_map_layer.cpp:220-420`

### 判斷是否需要全量重建

```cpp
// 以下任一旗標為 true → quadrant 形狀整個失效，需要全量重建
bool quadrant_shape_changed =
    dirty.flags[DIRTY_FLAGS_LAYER_Y_SORT_ENABLED] ||
    dirty.flags[DIRTY_FLAGS_TILE_SET] ||
    (is_y_sort_enabled() && (
        dirty.flags[DIRTY_FLAGS_LAYER_Y_SORT_ORIGIN] ||
        dirty.flags[DIRTY_FLAGS_LAYER_X_DRAW_ORDER_REVERSED] ||
        dirty.flags[DIRTY_FLAGS_LAYER_LOCAL_TRANSFORM]
    )) ||
    (!is_y_sort_enabled() && dirty.flags[DIRTY_FLAGS_LAYER_RENDERING_QUADRANT_SIZE]);
```

### 路徑 A：全量重建

```cpp
if (quadrant_shape_changed) {
    // 釋放所有 canvas_item RID
    for (auto &kv : rendering_quadrant_map) {
        for (const RID &ci : kv.value->canvas_items) {
            rs->free_rid(ci);
        }
        kv.value->cells.clear();
    }
    rendering_quadrant_map.clear();
    _rendering_was_cleaned_up = true;
    // 之後對所有格子呼叫 _rendering_quadrants_update_cell()
}
```

### 路徑 B：增量更新（只處理 dirty cell list）

```cpp
if (_rendering_was_cleaned_up || dirty.flags[DIRTY_FLAGS_TILE_SET] || dirty.flags[DIRTY_FLAGS_LAYER_IN_TREE]) {
    // 全量：遍歷 tile_map_layer_data
    for (auto &kv : tile_map_layer_data) {
        _rendering_quadrants_update_cell(kv.value, dirty_rendering_quadrant_list);
    }
} else {
    // 增量：只遍歷 dirty.cell_list
    for (SelfList<CellData> *el = dirty.cell_list.first(); el; el = el->next()) {
        _rendering_quadrants_update_cell(*el->self(), dirty_rendering_quadrant_list);
    }
}
```

### Canvas Item 按 Material / Z-Index 分組

`scene/2d/tile_map_layer.cpp:318-384`

```cpp
// 在一個 quadrant 內，排序後遍歷所有格子
Ref<Material> prev_material;
int prev_z_index = 0;
RID prev_ci;

for (CellData &cell_data : rendering_quadrant->cells) {
    Ref<Material> mat = tile_data->get_material();
    int tile_z_index = tile_data->get_z_index();

    // material 或 z_index 改變 → 建立新的 canvas_item
    if (prev_ci == RID() || prev_material != mat || prev_z_index != tile_z_index) {
        ci = rs->canvas_item_create();
        rs->canvas_item_set_parent(ci, get_canvas_item());
        rs->canvas_item_set_z_index(ci, tile_z_index);
        if (mat.is_valid()) rs->canvas_item_set_material(ci, mat->get_rid());
        rendering_quadrant->canvas_items.push_back(ci);
        prev_ci = ci;
        prev_material = mat; prev_z_index = tile_z_index;
    } else {
        ci = prev_ci;  // 同一 canvas_item 繼續繪製
    }

    // 繪製此格子（產生一個 CommandRect）
    draw_tile(ci, local_tile_pos - quadrant_base, tile_set, source_id, atlas_coords, alt, ...);
}
```

這讓同一個 quadrant 內**相鄰且屬性相同的格子共享一個 canvas_item**，批次合併繪製命令。

---

## 9. 完整更新呼叫鏈

```
使用者呼叫 set_cell(coords, source, atlas, alt)
  └─ tile_map_layer_data.insert() 或更新
  └─ dirty.cell_list.add(&cell_data.dirty_list_element)
  └─ _queue_internal_update()
       └─ [MessageQueue 延遲] → _deferred_update()
            └─ _rendering_update()
            └─ _physics_update()
            └─ _navigation_update()
            └─ dirty.cell_list.clear()
            └─ memset(dirty.flags, 0, sizeof(dirty.flags))

_rendering_update():
  ├─ [quadrant_shape_changed]
  │     → 釋放所有 RID，清空 quadrant map
  │     → 全量遍歷所有格子
  └─ [增量]
        → 只遍歷 dirty.cell_list 中的格子
        → _rendering_quadrants_update_cell()
             → 找到對應的 RenderingQuadrant（或建立新的）
             → 將 cell_data 加入 quadrant.cells
             → 加入 dirty_rendering_quadrant_list
  → 遍歷 dirty_rendering_quadrant_list
       → 清除舊 canvas_item
       → 對 cells 排序（Y-sort 模式按 Y 座標）
       → 按 material/z_index 分組建立 canvas_item
       → draw_tile() → canvas_item_add_texture_rect_region() → CommandRect
```

---

## 10. padded_texture——防止紋理出血

`scene/resources/2d/tile_set.h:673-678`

```cpp
bool use_texture_padding = true;
Ref<CanvasTexture> padded_texture;         // 帶有 1px 邊距的擴充版貼圖
bool padded_texture_needs_update = false;
void _update_padded_texture();
Ref<ImageTexture> _create_padded_image_texture(const Ref<Texture2D> &p_source);
```

**問題根源**：GPU 在 bilinear filtering 時，一個格子邊緣的 UV 座標可能取樣到相鄰格子的像素（特別是 Atlas 貼圖），造成「出血（bleeding）」邊框。

**解法**：`_create_padded_image_texture()` 為 Atlas 中每個磁磚的邊緣**向外複製 1 像素**，形成一圈重複的邊框。實際 UV 採樣仍在原始像素範圍內，但 bilinear filter 即使超出邊界也只取樣到重複的邊緣色，而非相鄰磁磚的顏色。

`padded_texture` 是 `CanvasTexture` 類型，可附帶 normal map 等設定。渲染時實際使用的是 `padded_texture` 而非原始 `texture`（當 `use_texture_padding = true` 時）。

---

## 11. TileSetAtlasSource 的 Atlas 資料結構

`scene/resources/2d/tile_set.h:636-665`

```cpp
struct TileAlternativesData {
    Vector2i size_in_atlas = Vector2i(1, 1);   // 此磁磚佔 Atlas 多少格（多格磁磚）
    Vector2i texture_offset;                   // 貼圖內的像素偏移

    // 動畫
    int animation_columns = 0;                 // 動畫幀橫向排列數量
    Vector2i animation_separation;             // 幀間距
    real_t animation_speed = 1.0;
    TileAnimationMode animation_mode;
    LocalVector<real_t> animation_frames_durations; // 每幀持續時間

    // Alternatives（包含 alternative 0 = 基本磁磚）
    HashMap<int, TileData *> alternatives;     // alternative_id → TileData
    Vector<int> alternatives_ids;             // 有序 ID 列表
    int next_alternative_id = 1;
};

HashMap<Vector2i, TileAlternativesData> tiles;           // atlas_coords → 資料
HashMap<Vector2i, Vector2i> _coords_mapping_cache;       // 任意座標 → 所屬磁磚左上角
```

- `tiles`：以 Atlas 座標（磁磚左上角格子）為 key。
- `_coords_mapping_cache`：對於多格磁磚，把所有被佔用的格子座標映射回磁磚的起始座標，加速 `has_tile()` 查詢。
- `alternatives`：alternative 0 是「標準磁磚」，正整數是使用者自定義的變體（不同材質、Z-index 等）。
- `alternatives_ids` 中不包含翻轉位元——翻轉是在 `TileMapCell.alternative_tile` 的高位元記錄的，對 `TileData` 查詢時需先用 `UNTRANSFORM_MASK` 取出真實 ID。

---

## 12. Sprite2D vs TileMapLayer 繪製路徑對比

| 特性 | Sprite2D | TileMapLayer |
|------|---------|-------------|
| 每幀重繪觸發 | `queue_redraw()` → `NOTIFICATION_DRAW` | `_queue_internal_update()` → deferred update |
| 繪製命令單位 | 1 個 `CommandRect` | N 個 `CommandRect`（每個格子一個） |
| Canvas Item 數量 | 1 個（節點本身） | 多個（每個 quadrant 1~M 個，依 material/z_index 分組） |
| 更新策略 | 全量（每次 NOTIFICATION_DRAW 重新繪製） | 增量（dirty cell list）或全量（quadrant_shape_changed） |
| 貼圖來源 | 單一 Texture2D | TileSetAtlasSource 的 padded_texture |
| 翻轉資訊 | dst_rect 負尺寸 | alternative_tile 高位元（TransformBits） |

---

## 13. 設計重點總結

| 設計 | 效果 |
|------|------|
| `TileMapCell` union 8 bytes | `hash_one_uint64` 一次完成 hash，無複合 key 開銷 |
| `alternative_tile` 高位元存翻轉 | 翻轉不佔 HashMap slot，節省記憶體 |
| `CellData` 侵入式 `SelfList` | dirty list 插入/移除 O(1)，無 heap 分配 |
| Quadrant 分塊（16×16）| 限制每次增量更新的範圍；quadrant 層級的批次合併 |
| `dirty.flags + dirty.cell_list` 雙層 Dirty | 層級屬性（Y-sort 等）vs 個別格子變更分開追蹤 |
| `material/z_index` 分組 canvas_item | 跨格子的繪製命令能被 RenderingServer 批次合併 |
| `padded_texture` 1px 邊框 | bilinear filter 不出血，無需在 UV 座標上縮退 |
| `_coords_mapping_cache` | 多格磁磚的任意子格快速映射回磁磚起點 |

---

*原始碼版本：Godot Engine 4.7.dev*
*分析日期：2026-05-22*
