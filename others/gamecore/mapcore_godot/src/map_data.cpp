#include "map_data.h"

#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/string.hpp>

#include "mapcore/pathfinding.hpp"
#include "mapcore/rivers.hpp"

using namespace godot;

// ── 內部工具 ──────────────────────────────────────────────────────────────────

bool MapCoreMapData::_in_bounds(int x, int y) const noexcept {
    if (!result_) return false;
    return x >= 0 && y >= 0 && x < result_->tile_map.width() && y < result_->tile_map.height();
}

// ── _bind_methods ─────────────────────────────────────────────────────────────

void MapCoreMapData::_bind_methods() {
    // 尺寸
    ClassDB::bind_method(D_METHOD("get_width"),     &MapCoreMapData::get_width);
    ClassDB::bind_method(D_METHOD("get_height"),    &MapCoreMapData::get_height);
    ClassDB::bind_method(D_METHOD("get_seed_used"), &MapCoreMapData::get_seed_used);

    // 單格查詢
    ClassDB::bind_method(D_METHOD("get_terrain",      "x", "y"), &MapCoreMapData::get_terrain);
    ClassDB::bind_method(D_METHOD("get_hilliness",    "x", "y"), &MapCoreMapData::get_hilliness);
    ClassDB::bind_method(D_METHOD("get_water_depth",  "x", "y"), &MapCoreMapData::get_water_depth);
    ClassDB::bind_method(D_METHOD("get_height_value", "x", "y"), &MapCoreMapData::get_height_value);
    ClassDB::bind_method(D_METHOD("get_temperature",  "x", "y"), &MapCoreMapData::get_temperature);
    ClassDB::bind_method(D_METHOD("get_rainfall",     "x", "y"), &MapCoreMapData::get_rainfall);

    // 批次查詢
    ClassDB::bind_method(D_METHOD("get_terrain_array"),     &MapCoreMapData::get_terrain_array);
    ClassDB::bind_method(D_METHOD("get_height_array"),      &MapCoreMapData::get_height_array);
    ClassDB::bind_method(D_METHOD("get_temperature_array"), &MapCoreMapData::get_temperature_array);
    ClassDB::bind_method(D_METHOD("get_rainfall_array"),    &MapCoreMapData::get_rainfall_array);

    // 河流
    ClassDB::bind_method(D_METHOD("has_river_edge",     "x", "y", "direction"), &MapCoreMapData::has_river_edge);
    ClassDB::bind_method(D_METHOD("get_river_strength", "x", "y", "direction"), &MapCoreMapData::get_river_strength);
    ClassDB::bind_method(D_METHOD("get_all_river_edges"),                        &MapCoreMapData::get_all_river_edges);

    // Features
    ClassDB::bind_method(D_METHOD("get_feature_id_at", "x", "y"),       &MapCoreMapData::get_feature_id_at);
    ClassDB::bind_method(D_METHOD("get_feature_count"),                   &MapCoreMapData::get_feature_count);
    ClassDB::bind_method(D_METHOD("get_feature_info", "feature_id"),     &MapCoreMapData::get_feature_info);

    // 尋路
    ClassDB::bind_method(D_METHOD("find_path", "start", "goal", "river_crossing_cost"),
                         &MapCoreMapData::find_path, DEFVAL(0.0f));

    // 地形 ID 常數
    BIND_CONSTANT(TERRAIN_OCEAN);
    BIND_CONSTANT(TERRAIN_COAST);
    BIND_CONSTANT(TERRAIN_PLAINS);
    BIND_CONSTANT(TERRAIN_GRASSLAND);
    BIND_CONSTANT(TERRAIN_DESERT);
    BIND_CONSTANT(TERRAIN_TUNDRA);
    BIND_CONSTANT(TERRAIN_SNOW);
    BIND_CONSTANT(TERRAIN_FOREST);
    BIND_CONSTANT(TERRAIN_HILL);
    BIND_CONSTANT(TERRAIN_MOUNTAIN);
    BIND_CONSTANT(TERRAIN_LAKE);
}

// ── 尺寸 ─────────────────────────────────────────────────────────────────────

int MapCoreMapData::get_width() const {
    return result_ ? result_->tile_map.width() : 0;
}
int MapCoreMapData::get_height() const {
    return result_ ? result_->tile_map.height() : 0;
}
int64_t MapCoreMapData::get_seed_used() const {
    if (!result_ || !result_->seed) return 0;
    return static_cast<int64_t>(*result_->seed);
}

// ── 單格查詢 ─────────────────────────────────────────────────────────────────

int MapCoreMapData::get_terrain(int x, int y) const {
    if (!_in_bounds(x, y)) return TERRAIN_OCEAN;
    const auto* t = result_->tile_map.get(mapcore::Coord(x, y));
    return t ? static_cast<int>(t->terrain) : TERRAIN_OCEAN;
}

int MapCoreMapData::get_hilliness(int x, int y) const {
    if (!_in_bounds(x, y)) return 0;
    const auto* t = result_->tile_map.get(mapcore::Coord(x, y));
    return t ? static_cast<int>(t->hilliness) : 0;
}

float MapCoreMapData::get_water_depth(int x, int y) const {
    if (!_in_bounds(x, y)) return 0.0f;
    const auto* t = result_->tile_map.get(mapcore::Coord(x, y));
    return t ? t->water_depth : 0.0f;
}

float MapCoreMapData::get_height_value(int x, int y) const {
    if (!result_) return 0.0f;
    int idx = y * result_->tile_map.width() + x;
    if (idx < 0 || idx >= static_cast<int>(result_->heightmap.size())) return 0.0f;
    return result_->heightmap[idx];
}

float MapCoreMapData::get_temperature(int x, int y) const {
    if (!result_ || result_->temperature_celsius.empty()) return -999.0f;
    int idx = y * result_->tile_map.width() + x;
    if (idx < 0 || idx >= static_cast<int>(result_->temperature_celsius.size())) return -999.0f;
    return result_->temperature_celsius[idx];
}

float MapCoreMapData::get_rainfall(int x, int y) const {
    if (!result_ || result_->rainfall_mm.empty()) return -1.0f;
    int idx = y * result_->tile_map.width() + x;
    if (idx < 0 || idx >= static_cast<int>(result_->rainfall_mm.size())) return -1.0f;
    return result_->rainfall_mm[idx];
}

// ── 批次查詢 ─────────────────────────────────────────────────────────────────

PackedInt32Array MapCoreMapData::get_terrain_array() const {
    PackedInt32Array out;
    if (!result_) return out;
    const int sz = result_->tile_map.size();
    out.resize(sz);
    int w = result_->tile_map.width();
    int h = result_->tile_map.height();
    for (int y = 0; y < h; ++y)
        for (int x = 0; x < w; ++x)
            out[y * w + x] = static_cast<int>(result_->tile_map.tile_at(x, y).terrain);
    return out;
}

PackedFloat32Array MapCoreMapData::get_height_array() const {
    PackedFloat32Array out;
    if (!result_) return out;
    const auto& hm = result_->heightmap;
    out.resize(static_cast<int>(hm.size()));
    for (int i = 0; i < static_cast<int>(hm.size()); ++i)
        out[i] = hm[i];
    return out;
}

PackedFloat32Array MapCoreMapData::get_temperature_array() const {
    PackedFloat32Array out;
    if (!result_ || result_->temperature_celsius.empty()) return out;
    const auto& v = result_->temperature_celsius;
    out.resize(static_cast<int>(v.size()));
    for (int i = 0; i < static_cast<int>(v.size()); ++i) out[i] = v[i];
    return out;
}

PackedFloat32Array MapCoreMapData::get_rainfall_array() const {
    PackedFloat32Array out;
    if (!result_ || result_->rainfall_mm.empty()) return out;
    const auto& v = result_->rainfall_mm;
    out.resize(static_cast<int>(v.size()));
    for (int i = 0; i < static_cast<int>(v.size()); ++i) out[i] = v[i];
    return out;
}

// ── 河流 ─────────────────────────────────────────────────────────────────────

bool MapCoreMapData::has_river_edge(int x, int y, int direction) const {
    if (!_in_bounds(x, y)) return false;
    return mapcore::has_river_edge(result_->tile_map, mapcore::Coord(x, y), direction);
}

int MapCoreMapData::get_river_strength(int x, int y, int direction) const {
    if (!_in_bounds(x, y)) return 0;
    return mapcore::get_river_strength(result_->tile_map, mapcore::Coord(x, y), direction);
}

TypedArray<Dictionary> MapCoreMapData::get_all_river_edges() const {
    TypedArray<Dictionary> out;
    if (!result_) return out;
    mapcore::iter_river_edges(result_->tile_map,
        [&](const mapcore::Coord& c, int dir, int strength) {
            Dictionary d;
            d["pos"]      = Vector2i(c.x, c.y);
            d["dir"]      = dir;
            d["strength"] = strength;
            out.push_back(d);
        });
    return out;
}

// ── Features ─────────────────────────────────────────────────────────────────

int MapCoreMapData::get_feature_id_at(int x, int y) const {
    if (!_in_bounds(x, y)) return -1;
    const auto* t = result_->tile_map.get(mapcore::Coord(x, y));
    return t ? t->feature_id : -1;
}

int MapCoreMapData::get_feature_count() const {
    if (!result_ || !result_->tile_map.features) return 0;
    return static_cast<int>(result_->tile_map.features->size());
}

Dictionary MapCoreMapData::get_feature_info(int feature_id) const {
    Dictionary d;
    if (!result_ || !result_->tile_map.features) return d;
    const auto* f = result_->tile_map.features->get(feature_id);
    if (!f) return d;
    d["name"]   = String(f->name.c_str());
    d["type"]   = String(f->feature_type.c_str());
    d["center"] = Vector2i(f->center.x, f->center.y);
    d["size"]   = f->size;
    return d;
}

// ── 尋路 ─────────────────────────────────────────────────────────────────────

PackedVector2iArray MapCoreMapData::find_path(Vector2i start, Vector2i goal,
                                               float river_crossing_cost) const {
    PackedVector2iArray out;
    if (!result_) return out;
    auto path = mapcore::astar(
        result_->tile_map,
        mapcore::Coord(start.x, start.y),
        mapcore::Coord(goal.x, goal.y),
        river_crossing_cost);
    if (!path) return out;
    out.resize(static_cast<int>(path->size()));
    for (int i = 0; i < static_cast<int>(path->size()); ++i)
        out[i] = Vector2i((*path)[i].x, (*path)[i].y);
    return out;
}
