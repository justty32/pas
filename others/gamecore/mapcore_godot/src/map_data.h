#pragma once
#include <godot_cpp/classes/resource.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/packed_float32_array.hpp>
#include <godot_cpp/variant/packed_int32_array.hpp>
#include <godot_cpp/variant/packed_vector2i_array.hpp>
#include <godot_cpp/variant/typed_array.hpp>
#include <godot_cpp/variant/vector2i.hpp>
#include <optional>

#include "mapcore/generation/pipeline.hpp"

namespace godot {

class MapCoreMapData : public Resource {
    GDCLASS(MapCoreMapData, Resource);

    std::optional<mapcore::generation::WorldGenResult> result_;
    friend class MapCoreGenerator;

    bool _in_bounds(int x, int y) const noexcept;

protected:
    static void _bind_methods();

public:
    MapCoreMapData() = default;

    // ── 地圖尺寸 ─────────────────────────────────────────────────────────────
    int     get_width()     const;
    int     get_height()    const;
    int64_t get_seed_used() const;

    // ── 單格查詢 ─────────────────────────────────────────────────────────────
    int   get_terrain     (int x, int y) const;   // TerrainType 常數 0~10
    int   get_hilliness   (int x, int y) const;   // 0=UNDEFINED … 5=IMPASSABLE
    float get_water_depth (int x, int y) const;
    float get_height_value(int x, int y) const;
    float get_temperature (int x, int y) const;   // 攝氏；-999 = 未生成氣候
    float get_rainfall    (int x, int y) const;   // mm；-1 = 未生成氣候

    // ── 批次查詢（一次取整張地圖，渲染用）────────────────────────────────────
    PackedInt32Array   get_terrain_array()     const;   // flat row-major [y*w+x]
    PackedFloat32Array get_height_array()      const;
    PackedFloat32Array get_temperature_array() const;
    PackedFloat32Array get_rainfall_array()    const;

    // ── 河流（direction: 0=E 1=N 2=W 3=S）──────────────────────────────────
    bool has_river_edge    (int x, int y, int direction) const;
    int  get_river_strength(int x, int y, int direction) const;
    // 回傳所有有河流的邊：Array of Dictionary {pos:Vector2i, dir:int, strength:int}
    TypedArray<Dictionary> get_all_river_edges() const;

    // ── Features（命名大區域）────────────────────────────────────────────────
    int        get_feature_id_at(int x, int y)     const;  // -1 = 無
    int        get_feature_count()                 const;
    Dictionary get_feature_info(int feature_id)    const;  // {name,type,center,size}

    // ── 尋路 ─────────────────────────────────────────────────────────────────
    PackedVector2iArray find_path(Vector2i start, Vector2i goal,
                                  float river_crossing_cost = 0.0f) const;

    // ── 地形 ID 常數（GDScript 用 MapCoreMapData.TERRAIN_OCEAN 存取）────────
    static constexpr int TERRAIN_OCEAN     = 0;
    static constexpr int TERRAIN_COAST     = 1;
    static constexpr int TERRAIN_PLAINS    = 2;
    static constexpr int TERRAIN_GRASSLAND = 3;
    static constexpr int TERRAIN_DESERT    = 4;
    static constexpr int TERRAIN_TUNDRA    = 5;
    static constexpr int TERRAIN_SNOW      = 6;
    static constexpr int TERRAIN_FOREST    = 7;
    static constexpr int TERRAIN_HILL      = 8;
    static constexpr int TERRAIN_MOUNTAIN  = 9;
    static constexpr int TERRAIN_LAKE      = 10;
};

} // namespace godot
