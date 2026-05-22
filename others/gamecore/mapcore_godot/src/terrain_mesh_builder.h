#pragma once
#include <godot_cpp/classes/array_mesh.hpp>
#include <godot_cpp/classes/ref_counted.hpp>
#include "map_data.h"

namespace godot {

// 從 MapCoreMapData 生成 Low Poly 3D 地形 ArrayMesh。
// 採用非共享頂點（每個三角面各自獨立頂點）以實現 flat shading。
class MapCoreTerrainMeshBuilder : public RefCounted {
    GDCLASS(MapCoreTerrainMeshBuilder, RefCounted);

protected:
    static void _bind_methods();

public:
    // 生成地形 ArrayMesh
    // tile_size:    每格世界單位大小（建議 1.0 = 1 m/格）
    // height_scale: heightmap 0~1 乘以此倍率得到世界 Y（建議 3.0）
    // jitter_amp:   頂點高度擾動幅度，增加有機感（建議 0.05）
    Ref<ArrayMesh> generate_terrain_mesh(
        Ref<MapCoreMapData> data,
        float tile_size    = 1.0f,
        float height_scale = 3.0f,
        float jitter_amp   = 0.05f
    );
};

} // namespace godot
