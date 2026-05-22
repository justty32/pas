#include "terrain_mesh_builder.h"

#include <godot_cpp/classes/array_mesh.hpp>
#include <godot_cpp/classes/mesh.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/array.hpp>
#include <godot_cpp/variant/color.hpp>
#include <godot_cpp/variant/packed_color_array.hpp>
#include <godot_cpp/variant/packed_float32_array.hpp>
#include <godot_cpp/variant/packed_int32_array.hpp>
#include <godot_cpp/variant/packed_vector3_array.hpp>
#include <godot_cpp/variant/vector3.hpp>

#include <vector>

using namespace godot;

// ── 工具函式 ──────────────────────────────────────────────────────────────────

// 基於座標的確定性 hash，回傳 0..1。用於可重現的頂點 jitter 與面色抖動。
static float hash_f(int a, int b) {
    unsigned int h = static_cast<unsigned int>(a * 1619 + b * 31337);
    h ^= (h << 13);
    h = h * (h * h * 15731u + 789221u) + 1376312589u;
    return static_cast<float>(h & 0x7fffffffu) / static_cast<float>(0x7fffffffu);
}

static Color terrain_to_color(int terrain) {
    switch (terrain) {
        case MapCoreMapData::TERRAIN_OCEAN:     return Color(0.08f, 0.25f, 0.55f, 1.0f);
        case MapCoreMapData::TERRAIN_COAST:     return Color(0.20f, 0.45f, 0.70f, 1.0f);
        case MapCoreMapData::TERRAIN_PLAINS:    return Color(0.65f, 0.70f, 0.35f, 1.0f);
        case MapCoreMapData::TERRAIN_GRASSLAND: return Color(0.30f, 0.60f, 0.25f, 1.0f);
        case MapCoreMapData::TERRAIN_DESERT:    return Color(0.80f, 0.70f, 0.38f, 1.0f);
        case MapCoreMapData::TERRAIN_TUNDRA:    return Color(0.60f, 0.65f, 0.70f, 1.0f);
        case MapCoreMapData::TERRAIN_SNOW:      return Color(0.85f, 0.90f, 0.95f, 1.0f);
        case MapCoreMapData::TERRAIN_FOREST:    return Color(0.15f, 0.40f, 0.15f, 1.0f);
        case MapCoreMapData::TERRAIN_HILL:      return Color(0.55f, 0.48f, 0.35f, 1.0f);
        case MapCoreMapData::TERRAIN_MOUNTAIN:  return Color(0.60f, 0.58f, 0.55f, 1.0f);
        case MapCoreMapData::TERRAIN_LAKE:      return Color(0.15f, 0.40f, 0.65f, 1.0f);
        default:                                return Color(0.50f, 0.50f, 0.50f, 1.0f);
    }
}

// 在基礎色上施加 ±8% 明度抖動，讓相鄰面有細微色差（low poly 視覺關鍵）
static Color vary_color(Color base, float t) {
    float s = 0.92f + t * 0.16f;
    return Color(base.r * s, base.g * s, base.b * s, 1.0f);
}

// ── _bind_methods ─────────────────────────────────────────────────────────────

void MapCoreTerrainMeshBuilder::_bind_methods() {
    ClassDB::bind_method(
        D_METHOD("generate_terrain_mesh", "data", "tile_size", "height_scale", "jitter_amp"),
        &MapCoreTerrainMeshBuilder::generate_terrain_mesh,
        DEFVAL(1.0f), DEFVAL(3.0f), DEFVAL(0.05f)
    );
}

// ── 主要生成函式 ──────────────────────────────────────────────────────────────

Ref<ArrayMesh> MapCoreTerrainMeshBuilder::generate_terrain_mesh(
    Ref<MapCoreMapData> data, float tile_size, float height_scale, float jitter_amp)
{
    if (!data.is_valid()) return {};
    const int W = data->get_width();
    const int H = data->get_height();
    if (W < 2 || H < 2) return {};

    PackedFloat32Array heights  = data->get_height_array();
    PackedInt32Array   terrains = data->get_terrain_array();

    // ── 預計算每個格點的世界 Y（含確定性 jitter）────────────────────────────
    std::vector<float> vert_y(static_cast<size_t>(W * H));
    for (int z = 0; z < H; ++z) {
        for (int x = 0; x < W; ++x) {
            float raw = heights[z * W + x] * height_scale;
            float j   = (hash_f(x, z) - 0.5f) * 2.0f * jitter_amp;
            vert_y[static_cast<size_t>(z * W + x)] = raw + j;
        }
    }

    // ── 分配輸出陣列（非共享頂點：每 quad 6 個頂點，flat shading）────────────
    const int num_quads = (W - 1) * (H - 1);
    PackedVector3Array verts;
    PackedVector3Array norms;
    PackedColorArray   cols;
    verts.resize(num_quads * 6);
    norms.resize(num_quads * 6);
    cols.resize(num_quads * 6);

    // ── 逐格填充三角形 ────────────────────────────────────────────────────────
    int vi = 0;
    for (int z = 0; z < H - 1; ++z) {
        for (int x = 0; x < W - 1; ++x) {
            // 四個角點（world space）
            Vector3 tl(static_cast<float>(x)   * tile_size, vert_y[static_cast<size_t>(z * W + x)],           static_cast<float>(z)   * tile_size);
            Vector3 tr(static_cast<float>(x+1) * tile_size, vert_y[static_cast<size_t>(z * W + x + 1)],       static_cast<float>(z)   * tile_size);
            Vector3 bl(static_cast<float>(x)   * tile_size, vert_y[static_cast<size_t>((z+1) * W + x)],       static_cast<float>(z+1) * tile_size);
            Vector3 br(static_cast<float>(x+1) * tile_size, vert_y[static_cast<size_t>((z+1) * W + x + 1)],   static_cast<float>(z+1) * tile_size);

            Color base = terrain_to_color(terrains[z * W + x]);

            // 三角形 1：TL, BL, TR（CCW，法線朝 +Y）
            Vector3 n1 = (bl - tl).cross(tr - tl).normalized();
            Color   c1 = vary_color(base, hash_f(x * 2, z * 2));
            verts[vi] = tl; norms[vi] = n1; cols[vi] = c1; ++vi;
            verts[vi] = bl; norms[vi] = n1; cols[vi] = c1; ++vi;
            verts[vi] = tr; norms[vi] = n1; cols[vi] = c1; ++vi;

            // 三角形 2：TR, BL, BR
            Vector3 n2 = (bl - tr).cross(br - tr).normalized();
            Color   c2 = vary_color(base, hash_f(x * 2 + 1, z * 2 + 1));
            verts[vi] = tr; norms[vi] = n2; cols[vi] = c2; ++vi;
            verts[vi] = bl; norms[vi] = n2; cols[vi] = c2; ++vi;
            verts[vi] = br; norms[vi] = n2; cols[vi] = c2; ++vi;
        }
    }

    // ── 組裝 ArrayMesh ────────────────────────────────────────────────────────
    Array arrays;
    arrays.resize(Mesh::ARRAY_MAX);
    arrays[Mesh::ARRAY_VERTEX] = verts;
    arrays[Mesh::ARRAY_NORMAL] = norms;
    arrays[Mesh::ARRAY_COLOR]  = cols;

    Ref<ArrayMesh> mesh;
    mesh.instantiate();
    mesh->add_surface_from_arrays(Mesh::PRIMITIVE_TRIANGLES, arrays);
    return mesh;
}
