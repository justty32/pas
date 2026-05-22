#pragma once
#include <godot_cpp/classes/node.hpp>
#include <godot_cpp/variant/string.hpp>

#include "map_data.h"

namespace godot {

class MapCoreGenerator : public Node {
    GDCLASS(MapCoreGenerator, Node);

    // ── 地圖尺寸 ─────────────────────────────────────────────────────────────
    int width_  = 64;
    int height_ = 48;

    // seed: 0 = 每次隨機；非 0 = 固定 seed（可重現結果）
    int64_t seed_ = 0;

    // ── 高程 ─────────────────────────────────────────────────────────────────
    float   sea_level_      = 0.4f;
    int     octaves_        = 5;
    float   persistence_    = 0.5f;
    int     base_frequency_ = 4;

    // 地圖形狀遮罩："" | "island" | "archipelago" | "pangaea" | "continents"
    //              | "ring_sea" | "shattered_archipelago"
    String  shape_;
    float   shape_strength_ = 0.85f;

    // 山脊模式："" = 停用 | "plates"（預設）| "global"
    String  ridge_mode_     = "";
    float   ridge_weight_   = 0.0f;
    int     num_plates_     = 20;

    // ── 系統開關 ─────────────────────────────────────────────────────────────
    bool enable_climate_  = true;
    bool enable_rivers_   = true;
    bool enable_features_ = true;

    // ── 內部 ─────────────────────────────────────────────────────────────────
    mapcore::generation::WorldGenParams _build_params() const;
    void _generate_thread();
    void _on_thread_done(Ref<MapCoreMapData> data);
    void _on_thread_failed(String message);

protected:
    static void _bind_methods();

public:
    // 同步生成（小地圖 / Editor 工具用）
    Ref<MapCoreMapData> generate();

    // 非同步生成；完成後 emit generation_completed(data)
    void generate_async();

    // ── 屬性 getter / setter ─────────────────────────────────────────────────
    void    set_width(int v)           { width_  = v; }
    int     get_width() const          { return width_; }
    void    set_height(int v)          { height_ = v; }
    int     get_height() const         { return height_; }
    void    set_seed(int64_t v)        { seed_   = v; }
    int64_t get_seed() const           { return seed_; }

    void  set_sea_level(float v)       { sea_level_      = v; }
    float get_sea_level() const        { return sea_level_; }
    void  set_octaves(int v)           { octaves_        = v; }
    int   get_octaves() const          { return octaves_; }
    void  set_persistence(float v)     { persistence_    = v; }
    float get_persistence() const      { return persistence_; }
    void  set_base_frequency(int v)    { base_frequency_ = v; }
    int   get_base_frequency() const   { return base_frequency_; }

    void   set_shape(const String& v)  { shape_          = v; }
    String get_shape() const           { return shape_; }
    void   set_shape_strength(float v) { shape_strength_ = v; }
    float  get_shape_strength() const  { return shape_strength_; }

    void   set_ridge_mode(const String& v) { ridge_mode_   = v; }
    String get_ridge_mode() const          { return ridge_mode_; }
    void   set_ridge_weight(float v)       { ridge_weight_ = v; }
    float  get_ridge_weight() const        { return ridge_weight_; }
    void   set_num_plates(int v)           { num_plates_   = v; }
    int    get_num_plates() const          { return num_plates_; }

    void set_enable_climate(bool v)    { enable_climate_  = v; }
    bool get_enable_climate() const    { return enable_climate_; }
    void set_enable_rivers(bool v)     { enable_rivers_   = v; }
    bool get_enable_rivers() const     { return enable_rivers_; }
    void set_enable_features(bool v)   { enable_features_ = v; }
    bool get_enable_features() const   { return enable_features_; }
};

} // namespace godot
