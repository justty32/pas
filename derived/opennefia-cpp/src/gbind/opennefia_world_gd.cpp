#include "opennefia_world_gd.h"

#include "core/components/meta_data_component.h"
#include "core/components/spatial_component.h"
#include "core/maps/map_data.h"

#include <godot_cpp/variant/rect2i.hpp>
#include <godot_cpp/variant/color.hpp>

using namespace godot;

// ---- static binding --------------------------------------------------------

void opennefia_gd::OpenNefiaWorld::_bind_methods() {
    ClassDB::bind_method(D_METHOD("get_map_width"),  &OpenNefiaWorld::get_map_width);
    ClassDB::bind_method(D_METHOD("get_map_height"), &OpenNefiaWorld::get_map_height);
    ClassDB::bind_method(D_METHOD("is_walkable", "x", "y"), &OpenNefiaWorld::is_walkable);
    ClassDB::bind_method(D_METHOD("generate_map_image", "cell_px"), &OpenNefiaWorld::generate_map_image);
    ClassDB::bind_method(D_METHOD("tick"), &OpenNefiaWorld::tick);
}

// ---- ctor / lifecycle -------------------------------------------------------

opennefia_gd::OpenNefiaWorld::OpenNefiaWorld() = default;

void opennefia_gd::OpenNefiaWorld::_ready() {
    setup_test_world();
}

// ---- 測試世界建構 -----------------------------------------------------------
//
// 20×15 的地圖：邊界為牆（blocks_sight, !walkable），內部為地板（walkable）。
// 一個 hero 實體放在中央 (10, 7)。
void opennefia_gd::OpenNefiaWorld::setup_test_world() {
    constexpr int W = 20, H = 15;

    // 1. 建地圖實體
    map_entity_ = em_.create();
    auto& map = em_.emplace<opennefia::MapData>(map_entity_, W, H);

    for (int x = 0; x < W; ++x) {
        for (int y = 0; y < H; ++y) {
            bool is_border = (x == 0 || x == W-1 || y == 0 || y == H-1);
            auto& tile = map.at(x, y);
            if (is_border) {
                tile.terrain = 1;  // 牆地形 id
                tile.flags   = opennefia::TILE_BLOCKS_SIGHT;  // !walkable
            } else {
                tile.terrain = 0;  // 地板地形 id
                tile.flags   = opennefia::TILE_WALKABLE;
            }
        }
    }

    // 2. 建 hero 實體
    hero_entity_ = em_.create();
    em_.emplace<opennefia::MetaDataComponent>(hero_entity_, "hero", true);
    em_.emplace<opennefia::SpatialComponent>(hero_entity_, W/2, H/2);
}

// ---- 地圖查詢 ---------------------------------------------------------------

int opennefia_gd::OpenNefiaWorld::get_map_width() const {
    if (map_entity_ == entt::null) return 0;
    return em_.get<opennefia::MapData>(map_entity_).width;
}

int opennefia_gd::OpenNefiaWorld::get_map_height() const {
    if (map_entity_ == entt::null) return 0;
    return em_.get<opennefia::MapData>(map_entity_).height;
}

bool opennefia_gd::OpenNefiaWorld::is_walkable(int x, int y) const {
    if (map_entity_ == entt::null) return false;
    const auto& map = em_.get<opennefia::MapData>(map_entity_);
    if (!map.in_bounds(x, y)) return false;
    return map.at(x, y).is_walkable();
}

// ---- 圖片生成 ---------------------------------------------------------------
//
// 三色：地板 = 棕 / 牆 = 深黑 / hero = 黃
// 回傳 FORMAT_RGB8 的 Image；GDScript 用 ImageTexture.create_from_image() 轉為貼圖。
godot::Ref<godot::Image> opennefia_gd::OpenNefiaWorld::generate_map_image(int cell_px) const {
    if (map_entity_ == entt::null) return {};

    const auto& map = em_.get<opennefia::MapData>(map_entity_);
    int img_w = map.width  * cell_px;
    int img_h = map.height * cell_px;

    Ref<Image> img = Image::create(img_w, img_h, false, Image::FORMAT_RGB8);

    const Color floor_color(0.40f, 0.35f, 0.25f);
    const Color wall_color (0.12f, 0.10f, 0.08f);
    const Color hero_color (1.00f, 0.90f, 0.20f);

    for (int x = 0; x < map.width; ++x) {
        for (int y = 0; y < map.height; ++y) {
            Color c = map.at(x, y).is_walkable() ? floor_color : wall_color;
            img->fill_rect(Rect2i(x * cell_px, y * cell_px, cell_px, cell_px), c);
        }
    }

    // hero 標記（疊蓋在地板色之上）
    if (em_.registry().valid(hero_entity_)) {
        const auto* sp = em_.registry().try_get<opennefia::SpatialComponent>(hero_entity_);
        if (sp && map.in_bounds(sp->x, sp->y)) {
            img->fill_rect(Rect2i(sp->x * cell_px, sp->y * cell_px, cell_px, cell_px), hero_color);
        }
    }

    return img;
}

// ---- tick -------------------------------------------------------------------

void opennefia_gd::OpenNefiaWorld::tick() {
    // Phase F2：目前為空；未來接移動 AI、回合推進。
}
