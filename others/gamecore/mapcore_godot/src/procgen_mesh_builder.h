#pragma once
#include <godot_cpp/classes/array_mesh.hpp>
#include <godot_cpp/classes/ref_counted.hpp>

namespace godot {

// 程序生成低多邊形 3D 幾何：岩石、樹幹、樹冠。
// 所有方法回傳非共享頂點 ArrayMesh（flat shading 用）。
// 搭配 MaterialLibrary.make_vertex_color() 使用。
class MapCoreProcGenMeshBuilder : public RefCounted {
    GDCLASS(MapCoreProcGenMeshBuilder, RefCounted);

protected:
    static void _bind_methods();

public:
    // 岩石：UV sphere（4lat×6lon）+ per-vertex noise 位移 + 非均勻縮放
    // base_radius: 基礎半徑（建議 0.3~1.2）
    // roughness:   頂點位移幅度（建議 0.1~0.4）
    // seed:        決定性亂數種子，相同 seed 產生相同 mesh
    Ref<ArrayMesh> generate_rock(
        float base_radius = 0.5f,
        float roughness   = 0.2f,
        int   seed        = 0
    );

    // 樹幹：六稜柱（頂端略細，Y 微擾動）
    Ref<ArrayMesh> generate_tree_trunk(
        float height = 1.0f,
        float radius = 0.08f,
        int   seed   = 0
    );

    // 樹冠：多個互相重疊的錐形（2~4 個），高度/偏移略有差異
    // cone_count: 錐形數量（建議 2~4）
    Ref<ArrayMesh> generate_tree_foliage(
        float radius     = 0.5f,
        int   cone_count = 3,
        int   seed       = 0
    );
};

} // namespace godot
