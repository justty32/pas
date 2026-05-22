#pragma once
#include <godot_cpp/classes/image.hpp>
#include <godot_cpp/classes/ref_counted.hpp>

#include "map_data.h"

namespace godot {

// 從 MapCoreMapData 生成 2D 俯視世界地圖 Image。
// 每格對應 cell_px×cell_px 像素；河流畫在格子邊界。
class MapCoreWorldMap2DRenderer : public RefCounted {
    GDCLASS(MapCoreWorldMap2DRenderer, RefCounted);

protected:
    static void _bind_methods();

public:
    // 回傳一張 RGB8 Image，每格為 cell_px 像素寬高，以地形顏色填色。
    Ref<Image> generate_terrain_image(Ref<MapCoreMapData> data, int cell_px = 8);

    // 在既有 Image 上就地繪製河流（藍色線段，厚度 ~2px）。
    void draw_rivers(Ref<Image> image, Ref<MapCoreMapData> data, int cell_px = 8);
};

} // namespace godot
