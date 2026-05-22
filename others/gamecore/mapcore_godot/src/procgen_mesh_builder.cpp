#include "procgen_mesh_builder.h"

#include <godot_cpp/classes/array_mesh.hpp>
#include <godot_cpp/classes/mesh.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/array.hpp>
#include <godot_cpp/variant/color.hpp>
#include <godot_cpp/variant/packed_color_array.hpp>
#include <godot_cpp/variant/packed_vector3_array.hpp>
#include <godot_cpp/variant/vector3.hpp>

#include <cmath>
#include <vector>

using namespace godot;

static constexpr float KPI = 3.14159265358979323846f;

// ── 確定性 hash（回傳 0..1）────────────────────────────────────────────────────

static float hf(int a, int b) {
    unsigned int h = static_cast<unsigned int>(a * 1619 + b * 31337);
    h ^= (h << 13);
    h = h * (h * h * 15731u + 789221u) + 1376312589u;
    return static_cast<float>(h & 0x7fffffffu) / 2147483647.0f;
}

static float hf3(int a, int b, int c) {
    return hf(a ^ (b * 7919 + c * 31337), b ^ c);
}

// ── 非共享頂點 mesh 建構器 ─────────────────────────────────────────────────────

struct MeshBuf {
    PackedVector3Array verts, norms;
    PackedColorArray   cols;

    void tri(Vector3 a, Vector3 b, Vector3 c, Color col) {
        Vector3 n = (b - a).cross(c - a).normalized();
        verts.append(a); norms.append(n); cols.append(col);
        verts.append(b); norms.append(n); cols.append(col);
        verts.append(c); norms.append(n); cols.append(col);
    }

    Ref<ArrayMesh> build() {
        Array arr;
        arr.resize(Mesh::ARRAY_MAX);
        arr[Mesh::ARRAY_VERTEX] = verts;
        arr[Mesh::ARRAY_NORMAL] = norms;
        arr[Mesh::ARRAY_COLOR]  = cols;
        Ref<ArrayMesh> m;
        m.instantiate();
        m->add_surface_from_arrays(Mesh::PRIMITIVE_TRIANGLES, arr);
        return m;
    }
};

// ── _bind_methods ──────────────────────────────────────────────────────────────

void MapCoreProcGenMeshBuilder::_bind_methods() {
    ClassDB::bind_method(
        D_METHOD("generate_rock", "base_radius", "roughness", "seed"),
        &MapCoreProcGenMeshBuilder::generate_rock,
        DEFVAL(0.5f), DEFVAL(0.2f), DEFVAL(0)
    );
    ClassDB::bind_method(
        D_METHOD("generate_tree_trunk", "height", "radius", "seed"),
        &MapCoreProcGenMeshBuilder::generate_tree_trunk,
        DEFVAL(1.0f), DEFVAL(0.08f), DEFVAL(0)
    );
    ClassDB::bind_method(
        D_METHOD("generate_tree_foliage", "radius", "cone_count", "seed"),
        &MapCoreProcGenMeshBuilder::generate_tree_foliage,
        DEFVAL(0.5f), DEFVAL(3), DEFVAL(0)
    );
}

// ── 岩石 ──────────────────────────────────────────────────────────────────────

Ref<ArrayMesh> MapCoreProcGenMeshBuilder::generate_rock(
    float base_radius, float roughness, int seed)
{
    // UV sphere 骨架：4 個緯度環 × 6 個經度段 = 26 頂點（不含極點×2）
    const int LAT = 4, LON = 6;
    const int N   = 2 + LAT * LON;

    std::vector<Vector3> sp(N);
    sp[0] = {0.0f, 1.0f, 0.0f};
    for (int lat = 0; lat < LAT; lat++) {
        float phi = KPI * (lat + 1) / (LAT + 1);
        float y = std::cos(phi), r = std::sin(phi);
        for (int lon = 0; lon < LON; lon++) {
            float theta = 2.0f * KPI * lon / LON;
            sp[1 + lat * LON + lon] = {r * std::cos(theta), y, r * std::sin(theta)};
        }
    }
    sp[N - 1] = {0.0f, -1.0f, 0.0f};

    // 非均勻縮放（0.6~1.4），打破球形對稱
    float sx = 0.6f + hf(seed,     1) * 0.8f;
    float sy = 0.6f + hf(seed + 1, 2) * 0.8f;
    float sz = 0.6f + hf(seed + 2, 3) * 0.8f;

    // 每頂點沿法線方向施加 noise 位移，再套非均勻縮放
    auto disp = [&](int idx) -> Vector3 {
        Vector3 v = sp[idx];
        float   n = hf3(idx * 997 + seed, idx * 1619 + seed * 7, idx * 37 + seed * 3) - 0.5f;
        Vector3 d = v + v.normalized() * (n * roughness);
        return Vector3(d.x * sx, d.y * sy, d.z * sz) * base_radius;
    };

    // 面色：灰棕基礎色 ±12% 亮度抖動
    const Color rb{0.55f, 0.50f, 0.45f, 1.0f};
    auto fc = [&](int fi) -> Color {
        float s = 0.88f + hf(fi + seed * 13, fi * 7 + seed) * 0.24f;
        return {rb.r * s, rb.g * s, rb.b * s, 1.0f};
    };

    MeshBuf mb;
    int fi = 0;

    // 頂極扇形
    for (int lon = 0; lon < LON; lon++)
        mb.tri(disp(0), disp(1 + lon), disp(1 + (lon + 1) % LON), fc(fi++));

    // 中間格帶（每格兩個三角形）
    for (int lat = 0; lat < LAT - 1; lat++) {
        for (int lon = 0; lon < LON; lon++) {
            int tl = 1 + lat * LON + lon,           tr = 1 + lat * LON + (lon + 1) % LON;
            int bl = 1 + (lat + 1) * LON + lon,     br = 1 + (lat + 1) * LON + (lon + 1) % LON;
            mb.tri(disp(tl), disp(bl), disp(tr), fc(fi++));
            mb.tri(disp(tr), disp(bl), disp(br), fc(fi++));
        }
    }

    // 底極扇形
    for (int lon = 0; lon < LON; lon++)
        mb.tri(disp(N - 1),
               disp(1 + (LAT - 1) * LON + (lon + 1) % LON),
               disp(1 + (LAT - 1) * LON + lon),
               fc(fi++));

    return mb.build();
}

// ── 樹幹 ──────────────────────────────────────────────────────────────────────

Ref<ArrayMesh> MapCoreProcGenMeshBuilder::generate_tree_trunk(
    float height, float radius, int seed)
{
    const int SIDES = 6;
    // 頂端略細（0.4~0.7 倍基礎半徑），模擬樹幹向上收窄
    float top_r = radius * (0.40f + hf(seed, 42) * 0.30f);

    const Color bc{0.40f, 0.25f, 0.10f, 1.0f};
    auto bkc = [&](int i) -> Color {
        float s = 0.85f + hf(i + seed * 17, i * 3 + seed) * 0.30f;
        return {bc.r * s, bc.g * s, bc.b * s, 1.0f};
    };

    MeshBuf mb;
    for (int i = 0; i < SIDES; i++) {
        int   j  = (i + 1) % SIDES;
        float a0 = 2.0f * KPI * i / SIDES;
        float a1 = 2.0f * KPI * j / SIDES;

        // 頂端各頂點加小量 Y 擾動，讓頂緣不整齊
        float jyi = (hf(seed + i * 3, i * 7 + 1) - 0.5f) * height * 0.06f;
        float jyj = (hf(seed + j * 3, j * 7 + 1) - 0.5f) * height * 0.06f;

        Vector3 bl{radius * std::cos(a0), 0.0f,          radius * std::sin(a0)};
        Vector3 br{radius * std::cos(a1), 0.0f,          radius * std::sin(a1)};
        Vector3 tl{top_r  * std::cos(a0), height + jyi,  top_r  * std::sin(a0)};
        Vector3 tr{top_r  * std::cos(a1), height + jyj,  top_r  * std::sin(a1)};

        mb.tri(bl, br, tl, bkc(i * 2));
        mb.tri(tl, br, tr, bkc(i * 2 + 1));
    }
    return mb.build();
}

// ── 樹冠 ──────────────────────────────────────────────────────────────────────

Ref<ArrayMesh> MapCoreProcGenMeshBuilder::generate_tree_foliage(
    float radius, int cone_count, int seed)
{
    const int SIDES = 5;

    const Color lc{0.15f, 0.40f, 0.15f, 1.0f};
    auto lfc = [&](int ci, int fi) -> Color {
        float s = 0.85f + hf(ci * 31 + fi + seed * 13, ci * 17 + seed * 7) * 0.30f;
        return {lc.r * s, lc.g * s, lc.b * s, 1.0f};
    };

    MeshBuf mb;
    for (int ci = 0; ci < cone_count; ci++) {
        // 每個錐形有隨機的 XZ 偏移、半徑、高度、Y 起始位置（越高的錐起點越高）
        float ox = (hf(ci * 3 + seed, ci + 1) - 0.5f) * radius * 0.40f;
        float oz = (hf(ci * 3 + seed, ci + 2) - 0.5f) * radius * 0.40f;
        float r  = radius * (0.55f + hf(ci + seed, ci * 7 + 3) * 0.90f);
        float h  = r      * (0.90f + hf(ci + seed, ci * 5 + 4) * 0.60f);
        float by = static_cast<float>(ci) / cone_count * radius * 0.35f;

        Vector3 apex{ox, by + h, oz};
        for (int i = 0; i < SIDES; i++) {
            int   j  = (i + 1) % SIDES;
            float a0 = 2.0f * KPI * i / SIDES;
            float a1 = 2.0f * KPI * j / SIDES;
            Vector3 p0{ox + r * std::cos(a0), by, oz + r * std::sin(a0)};
            Vector3 p1{ox + r * std::cos(a1), by, oz + r * std::sin(a1)};
            mb.tri(p0, apex, p1, lfc(ci, i));
        }
    }
    return mb.build();
}
