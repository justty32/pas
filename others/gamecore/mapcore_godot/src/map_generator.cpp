#include "map_generator.h"

#include <godot_cpp/classes/worker_thread_pool.hpp>
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

// ── _bind_methods ─────────────────────────────────────────────────────────────

void MapCoreGenerator::_bind_methods() {
    // 生成方法
    ClassDB::bind_method(D_METHOD("generate"),       &MapCoreGenerator::generate);
    ClassDB::bind_method(D_METHOD("generate_async"), &MapCoreGenerator::generate_async);

    // 內部 deferred callback（不對外，但需要 ClassDB 知道）
    ClassDB::bind_method(D_METHOD("_on_thread_done",   "data"),    &MapCoreGenerator::_on_thread_done);
    ClassDB::bind_method(D_METHOD("_on_thread_failed", "message"), &MapCoreGenerator::_on_thread_failed);

    // Signal
    ADD_SIGNAL(MethodInfo("generation_completed",
        PropertyInfo(Variant::OBJECT, "data", PROPERTY_HINT_RESOURCE_TYPE, "MapCoreMapData")));
    ADD_SIGNAL(MethodInfo("generation_failed",
        PropertyInfo(Variant::STRING, "message")));

    // 屬性綁定 ─ 尺寸
    ClassDB::bind_method(D_METHOD("set_width",  "v"), &MapCoreGenerator::set_width);
    ClassDB::bind_method(D_METHOD("get_width"),       &MapCoreGenerator::get_width);
    ClassDB::bind_method(D_METHOD("set_height", "v"), &MapCoreGenerator::set_height);
    ClassDB::bind_method(D_METHOD("get_height"),      &MapCoreGenerator::get_height);
    ClassDB::bind_method(D_METHOD("set_seed",   "v"), &MapCoreGenerator::set_seed);
    ClassDB::bind_method(D_METHOD("get_seed"),        &MapCoreGenerator::get_seed);
    ADD_PROPERTY(PropertyInfo(Variant::INT, "width",  PROPERTY_HINT_RANGE, "4,1024,1"), "set_width",  "get_width");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "height", PROPERTY_HINT_RANGE, "4,1024,1"), "set_height", "get_height");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "seed"),                                     "set_seed",   "get_seed");

    // 屬性綁定 ─ 高程
    ClassDB::bind_method(D_METHOD("set_sea_level",      "v"), &MapCoreGenerator::set_sea_level);
    ClassDB::bind_method(D_METHOD("get_sea_level"),           &MapCoreGenerator::get_sea_level);
    ClassDB::bind_method(D_METHOD("set_octaves",        "v"), &MapCoreGenerator::set_octaves);
    ClassDB::bind_method(D_METHOD("get_octaves"),             &MapCoreGenerator::get_octaves);
    ClassDB::bind_method(D_METHOD("set_persistence",    "v"), &MapCoreGenerator::set_persistence);
    ClassDB::bind_method(D_METHOD("get_persistence"),         &MapCoreGenerator::get_persistence);
    ClassDB::bind_method(D_METHOD("set_base_frequency", "v"), &MapCoreGenerator::set_base_frequency);
    ClassDB::bind_method(D_METHOD("get_base_frequency"),      &MapCoreGenerator::get_base_frequency);
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "sea_level",     PROPERTY_HINT_RANGE, "0.1,0.9,0.01"), "set_sea_level",     "get_sea_level");
    ADD_PROPERTY(PropertyInfo(Variant::INT,   "octaves",       PROPERTY_HINT_RANGE, "1,10,1"),        "set_octaves",       "get_octaves");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "persistence",   PROPERTY_HINT_RANGE, "0.1,1.0,0.01"), "set_persistence",   "get_persistence");
    ADD_PROPERTY(PropertyInfo(Variant::INT,   "base_frequency",PROPERTY_HINT_RANGE, "1,16,1"),        "set_base_frequency","get_base_frequency");

    // 屬性綁定 ─ 形狀
    ClassDB::bind_method(D_METHOD("set_shape",          "v"), &MapCoreGenerator::set_shape);
    ClassDB::bind_method(D_METHOD("get_shape"),               &MapCoreGenerator::get_shape);
    ClassDB::bind_method(D_METHOD("set_shape_strength", "v"), &MapCoreGenerator::set_shape_strength);
    ClassDB::bind_method(D_METHOD("get_shape_strength"),      &MapCoreGenerator::get_shape_strength);
    ADD_PROPERTY(PropertyInfo(Variant::STRING, "shape"),          "set_shape",          "get_shape");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT,  "shape_strength",  PROPERTY_HINT_RANGE, "0.0,1.0,0.01"), "set_shape_strength", "get_shape_strength");

    // 屬性綁定 ─ 山脊
    ClassDB::bind_method(D_METHOD("set_ridge_mode",   "v"), &MapCoreGenerator::set_ridge_mode);
    ClassDB::bind_method(D_METHOD("get_ridge_mode"),         &MapCoreGenerator::get_ridge_mode);
    ClassDB::bind_method(D_METHOD("set_ridge_weight", "v"), &MapCoreGenerator::set_ridge_weight);
    ClassDB::bind_method(D_METHOD("get_ridge_weight"),       &MapCoreGenerator::get_ridge_weight);
    ClassDB::bind_method(D_METHOD("set_num_plates",   "v"), &MapCoreGenerator::set_num_plates);
    ClassDB::bind_method(D_METHOD("get_num_plates"),         &MapCoreGenerator::get_num_plates);
    ADD_PROPERTY(PropertyInfo(Variant::STRING, "ridge_mode"),                                          "set_ridge_mode",   "get_ridge_mode");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT,  "ridge_weight", PROPERTY_HINT_RANGE, "0.0,1.0,0.01"), "set_ridge_weight",  "get_ridge_weight");
    ADD_PROPERTY(PropertyInfo(Variant::INT,    "num_plates",   PROPERTY_HINT_RANGE, "2,64,1"),        "set_num_plates",    "get_num_plates");

    // 屬性綁定 ─ 系統開關
    ClassDB::bind_method(D_METHOD("set_enable_climate",  "v"), &MapCoreGenerator::set_enable_climate);
    ClassDB::bind_method(D_METHOD("get_enable_climate"),        &MapCoreGenerator::get_enable_climate);
    ClassDB::bind_method(D_METHOD("set_enable_rivers",   "v"), &MapCoreGenerator::set_enable_rivers);
    ClassDB::bind_method(D_METHOD("get_enable_rivers"),         &MapCoreGenerator::get_enable_rivers);
    ClassDB::bind_method(D_METHOD("set_enable_features", "v"), &MapCoreGenerator::set_enable_features);
    ClassDB::bind_method(D_METHOD("get_enable_features"),       &MapCoreGenerator::get_enable_features);
    ADD_PROPERTY(PropertyInfo(Variant::BOOL, "enable_climate"),  "set_enable_climate",  "get_enable_climate");
    ADD_PROPERTY(PropertyInfo(Variant::BOOL, "enable_rivers"),   "set_enable_rivers",   "get_enable_rivers");
    ADD_PROPERTY(PropertyInfo(Variant::BOOL, "enable_features"), "set_enable_features", "get_enable_features");
}

// ── 內部：組裝 WorldGenParams ─────────────────────────────────────────────────

mapcore::generation::WorldGenParams MapCoreGenerator::_build_params() const {
    mapcore::generation::WorldGenParams p;

    p.sea_level      = sea_level_;
    p.octaves        = octaves_;
    p.persistence    = persistence_;
    p.base_frequency = base_frequency_;

    p.heightmap_params.shape          = shape_.utf8().get_data();
    p.heightmap_params.shape_strength = shape_strength_;
    p.heightmap_params.ridge_mode     = ridge_mode_.utf8().get_data();
    p.heightmap_params.ridge_weight   = ridge_weight_;
    p.heightmap_params.num_plates     = num_plates_;

    p.climate  = enable_climate_;
    p.rivers   = enable_rivers_;
    p.features = enable_features_;

    return p;
}

// ── 同步生成 ──────────────────────────────────────────────────────────────────

Ref<MapCoreMapData> MapCoreGenerator::generate() {
    std::optional<uint64_t> seed_opt;
    if (seed_ != 0) seed_opt = static_cast<uint64_t>(seed_);

    auto result = mapcore::generation::generate_world(
        width_, height_, seed_opt, _build_params());

    Ref<MapCoreMapData> data;
    data.instantiate();
    data->result_ = std::move(result);
    return data;
}

// ── 非同步生成 ────────────────────────────────────────────────────────────────

void MapCoreGenerator::generate_async() {
    WorkerThreadPool::get_singleton()->add_task(
        callable_mp(this, &MapCoreGenerator::_generate_thread));
}

void MapCoreGenerator::_generate_thread() {
    // 在 worker thread 中執行；禁止操作場景樹
    std::optional<uint64_t> seed_opt;
    if (seed_ != 0) seed_opt = static_cast<uint64_t>(seed_);

    try {
        auto result = mapcore::generation::generate_world(
            width_, height_, seed_opt, _build_params());

        Ref<MapCoreMapData> data;
        data.instantiate();
        data->result_ = std::move(result);

        call_deferred("_on_thread_done", data);
    } catch (const std::exception& e) {
        call_deferred("_on_thread_failed", String(e.what()));
    } catch (...) {
        call_deferred("_on_thread_failed", String("unknown error in generate_world"));
    }
}

void MapCoreGenerator::_on_thread_done(Ref<MapCoreMapData> data) {
    emit_signal("generation_completed", data);
}

void MapCoreGenerator::_on_thread_failed(String message) {
    emit_signal("generation_failed", message);
}
