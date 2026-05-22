#include "world_map_2d_renderer.h"

#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/typed_array.hpp>
#include <godot_cpp/variant/dictionary.hpp>

namespace godot {

void MapCoreWorldMap2DRenderer::_bind_methods() {
    ClassDB::bind_method(
        D_METHOD("generate_terrain_image", "data", "cell_px"),
        &MapCoreWorldMap2DRenderer::generate_terrain_image, DEFVAL(8));
    ClassDB::bind_method(
        D_METHOD("draw_rivers", "image", "data", "cell_px"),
        &MapCoreWorldMap2DRenderer::draw_rivers, DEFVAL(8));
}

// ── 地形顏色表 ────────────────────────────────────────────────────────────────

static Color terrain_color(int t) {
    switch (t) {
        case MapCoreMapData::TERRAIN_OCEAN:     return Color(0.10f, 0.25f, 0.55f);
        case MapCoreMapData::TERRAIN_COAST:     return Color(0.25f, 0.50f, 0.75f);
        case MapCoreMapData::TERRAIN_PLAINS:    return Color(0.70f, 0.80f, 0.40f);
        case MapCoreMapData::TERRAIN_GRASSLAND: return Color(0.35f, 0.65f, 0.30f);
        case MapCoreMapData::TERRAIN_DESERT:    return Color(0.85f, 0.78f, 0.45f);
        case MapCoreMapData::TERRAIN_TUNDRA:    return Color(0.65f, 0.70f, 0.75f);
        case MapCoreMapData::TERRAIN_SNOW:      return Color(0.90f, 0.93f, 0.97f);
        case MapCoreMapData::TERRAIN_FOREST:    return Color(0.18f, 0.42f, 0.18f);
        case MapCoreMapData::TERRAIN_HILL:      return Color(0.60f, 0.55f, 0.40f);
        case MapCoreMapData::TERRAIN_MOUNTAIN:  return Color(0.50f, 0.45f, 0.40f);
        case MapCoreMapData::TERRAIN_LAKE:      return Color(0.20f, 0.45f, 0.70f);
        default:                                return Color(0.50f, 0.50f, 0.50f);
    }
}

// ── API 實作 ──────────────────────────────────────────────────────────────────

Ref<Image> MapCoreWorldMap2DRenderer::generate_terrain_image(
        Ref<MapCoreMapData> data, int cell_px) {
    ERR_FAIL_COND_V(data.is_null(), Ref<Image>());
    ERR_FAIL_COND_V(cell_px < 1, Ref<Image>());

    int w = data->get_width();
    int h = data->get_height();
    Ref<Image> img = Image::create(w * cell_px, h * cell_px, false, Image::FORMAT_RGB8);

    PackedInt32Array arr = data->get_terrain_array();
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            img->fill_rect(
                Rect2i(x * cell_px, y * cell_px, cell_px, cell_px),
                terrain_color(arr[y * w + x]));
        }
    }
    return img;
}

void MapCoreWorldMap2DRenderer::draw_rivers(
        Ref<Image> image, Ref<MapCoreMapData> data, int cell_px) {
    ERR_FAIL_COND(image.is_null());
    ERR_FAIL_COND(data.is_null());
    ERR_FAIL_COND(cell_px < 1);

    // 河流線段厚度（像素），最少 1px，隨 cell_px 等比縮放（上限 3px）
    int thick = Math::clamp(cell_px / 4, 1, 3);
    Color river_col(0.12f, 0.30f, 0.72f);

    TypedArray<Dictionary> edges = data->get_all_river_edges();
    for (int i = 0; i < edges.size(); ++i) {
        Dictionary d = edges[i];
        Vector2i pos = d["pos"];
        int dir = d["dir"];
        int x = pos.x * cell_px;
        int y = pos.y * cell_px;
        int cp = cell_px;

        Rect2i rect;
        switch (dir) {
            case 0: // East：右邊界
                rect = Rect2i(x + cp - thick, y, thick, cp); break;
            case 1: // North：上邊界
                rect = Rect2i(x, y, cp, thick); break;
            case 2: // West：左邊界
                rect = Rect2i(x, y, thick, cp); break;
            case 3: // South：下邊界
                rect = Rect2i(x, y + cp - thick, cp, thick); break;
            default:
                continue;
        }
        image->fill_rect(rect, river_col);
    }
}

} // namespace godot
