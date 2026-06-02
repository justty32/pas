#include "opennefia_world_gd.h"

#include "core/components/meta_data_component.h"
#include "core/components/spatial_component.h"
#include "core/components/npc_ai_component.h"
#include "core/components/health_component.h"
#include "core/maps/map_data.h"
#include "core/systems/npc_ai_system.h"
#include "core/systems/fov_system.h"

#include <godot_cpp/variant/rect2i.hpp>
#include <godot_cpp/variant/color.hpp>

using namespace godot;

// ---- static binding --------------------------------------------------------

void opennefia_gd::OpenNefiaWorld::_bind_methods() {
    ClassDB::bind_method(D_METHOD("get_map_width"),  &OpenNefiaWorld::get_map_width);
    ClassDB::bind_method(D_METHOD("get_map_height"), &OpenNefiaWorld::get_map_height);
    ClassDB::bind_method(D_METHOD("is_walkable", "x", "y"), &OpenNefiaWorld::is_walkable);
    ClassDB::bind_method(D_METHOD("generate_map_image", "cell_px"), &OpenNefiaWorld::generate_map_image);

    ClassDB::bind_method(D_METHOD("move", "dx", "dy"), &OpenNefiaWorld::move);
    ClassDB::bind_method(D_METHOD("wait_turn"), &OpenNefiaWorld::wait_turn);

    ClassDB::bind_method(D_METHOD("get_hero_x"),      &OpenNefiaWorld::get_hero_x);
    ClassDB::bind_method(D_METHOD("get_hero_y"),      &OpenNefiaWorld::get_hero_y);
    ClassDB::bind_method(D_METHOD("get_turn_count"),  &OpenNefiaWorld::get_turn_count);
    ClassDB::bind_method(D_METHOD("get_hero_hp"),     &OpenNefiaWorld::get_hero_hp);
    ClassDB::bind_method(D_METHOD("get_hero_max_hp"), &OpenNefiaWorld::get_hero_max_hp);

    ADD_SIGNAL(MethodInfo("world_changed"));
    ADD_SIGNAL(MethodInfo("hero_bumped_wall"));
    ADD_SIGNAL(MethodInfo("hero_bumped_npc",
        PropertyInfo(Variant::STRING, "npc_id")));
    ADD_SIGNAL(MethodInfo("npc_died",
        PropertyInfo(Variant::STRING, "npc_id")));
    ADD_SIGNAL(MethodInfo("game_over"));
}

// ---- ctor / lifecycle -------------------------------------------------------

opennefia_gd::OpenNefiaWorld::OpenNefiaWorld() = default;

void opennefia_gd::OpenNefiaWorld::_ready() {
    setup_test_world();
    recompute_fov();  // 初始視野（英雄出生位置）
}

// ---- 測試世界建構 -----------------------------------------------------------
//
// 20×15 地圖，邊界牆，內部地板。
// hero 在中央 (10, 7)，3 隻 NPC 分散於四角附近（可走格）。
void opennefia_gd::OpenNefiaWorld::setup_test_world() {
    constexpr int W = 20, H = 15;

    // 地圖
    map_entity_ = em_.create();
    auto& map = em_.emplace<opennefia::MapData>(map_entity_, W, H);

    for (int x = 0; x < W; ++x) {
        for (int y = 0; y < H; ++y) {
            bool is_border = (x == 0 || x == W-1 || y == 0 || y == H-1);
            auto& tile = map.at(x, y);
            if (is_border) {
                tile.terrain = 1;
                tile.flags   = opennefia::TILE_BLOCKS_SIGHT;
            } else {
                tile.terrain = 0;
                tile.flags   = opennefia::TILE_WALKABLE;
            }
        }
    }

    // Hero（HP 20/20）
    hero_entity_ = em_.create();
    em_.emplace<opennefia::MetaDataComponent>(hero_entity_, "hero", true);
    em_.emplace<opennefia::SpatialComponent>(hero_entity_, W/2, H/2);
    em_.emplace<opennefia::HealthComponent>(hero_entity_, 20, 20);

    // 3 隻 NPC（HP 10/10，放在可走格，遠離邊界）
    struct NpcSpawn { int x, y; const char* id; };
    constexpr NpcSpawn SPAWNS[3] = {
        { 3,     3,    "npc_a" },
        { W - 4, 3,    "npc_b" },
        { W / 2, H-4,  "npc_c" },
    };
    for (auto& s : SPAWNS) {
        auto e = em_.create();
        em_.emplace<opennefia::MetaDataComponent>(e, s.id, true);
        em_.emplace<opennefia::SpatialComponent>(e, s.x, s.y);
        em_.emplace<opennefia::NpcAiComponent>(e);
        em_.emplace<opennefia::HealthComponent>(e, 10, 10);
    }

    // 註冊 NPC AI 系統
    em_.add_system(opennefia::npc_ai_system);
}

// ---- 視野計算 ---------------------------------------------------------------

void opennefia_gd::OpenNefiaWorld::recompute_fov() {
    if (hero_entity_ == entt::null || map_entity_ == entt::null) return;
    const auto* sp = em_.registry().try_get<opennefia::SpatialComponent>(hero_entity_);
    if (!sp) return;
    auto& map = em_.get<opennefia::MapData>(map_entity_);
    opennefia::compute_fov(map, sp->x, sp->y, 8);
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

// ---- 圖片生成（FOV 三層霧中戰爭）------------------------------------------
//
// 未探索：黑  ／  探索未見：40% 亮度  ／  可見：原色
// NPC：只在可見格顯示（紅）；Hero 永遠顯示（黃，疊在最上層）

godot::Ref<godot::Image> opennefia_gd::OpenNefiaWorld::generate_map_image(int cell_px) const {
    if (map_entity_ == entt::null) return {};

    const auto& map = em_.get<opennefia::MapData>(map_entity_);
    Ref<Image> img = Image::create(map.width * cell_px, map.height * cell_px,
                                   false, Image::FORMAT_RGB8);

    const Color floor_color(0.40f, 0.35f, 0.25f);
    const Color wall_color (0.12f, 0.10f, 0.08f);
    const Color hero_color (1.00f, 0.90f, 0.20f);
    const Color npc_color  (0.90f, 0.20f, 0.20f);
    const Color black      (0.00f, 0.00f, 0.00f);

    // 地板 / 牆（依 FOV 狀態決定亮度）
    for (int x = 0; x < map.width; ++x) {
        for (int y = 0; y < map.height; ++y) {
            Color c;
            if (map.is_visible(x, y)) {
                c = map.at(x, y).is_walkable() ? floor_color : wall_color;
            } else if (map.is_explored(x, y)) {
                Color base = map.at(x, y).is_walkable() ? floor_color : wall_color;
                c = Color(base.r * 0.4f, base.g * 0.4f, base.b * 0.4f);
            } else {
                c = black;
            }
            img->fill_rect(Rect2i(x*cell_px, y*cell_px, cell_px, cell_px), c);
        }
    }

    // NPC（紅點，只在可見格顯示）
    auto npc_view = em_.registry().view<opennefia::NpcAiComponent,
                                        opennefia::SpatialComponent>();
    for (auto e : npc_view) {
        const auto& sp = npc_view.get<opennefia::SpatialComponent>(e);
        if (map.is_visible(sp.x, sp.y))
            img->fill_rect(Rect2i(sp.x*cell_px, sp.y*cell_px, cell_px, cell_px), npc_color);
    }

    // Hero（黃點，永遠顯示，疊在最上層）
    if (em_.registry().valid(hero_entity_)) {
        const auto* sp = em_.registry().try_get<opennefia::SpatialComponent>(hero_entity_);
        if (sp && map.in_bounds(sp->x, sp->y))
            img->fill_rect(Rect2i(sp->x*cell_px, sp->y*cell_px, cell_px, cell_px), hero_color);
    }

    return img;
}

// ---- 動作介面 ---------------------------------------------------------------

bool opennefia_gd::OpenNefiaWorld::move(int dx, int dy) {
    if (game_over_) return false;
    if (hero_entity_ == entt::null || map_entity_ == entt::null) return false;

    auto* sp = em_.registry().try_get<opennefia::SpatialComponent>(hero_entity_);
    if (!sp) return false;

    int nx = sp->x + dx;
    int ny = sp->y + dy;
    const auto& map = em_.get<opennefia::MapData>(map_entity_);

    // 牆壁碰撞
    if (!map.in_bounds(nx, ny) || !map.at(nx, ny).is_walkable()) {
        emit_signal("hero_bumped_wall");
        return false;
    }

    // NPC 碰撞：英雄攻擊 NPC（扣 3 HP；若死亡則銷毀實體）
    auto& reg = em_.registry();
    auto npc_view = reg.view<opennefia::NpcAiComponent,
                             opennefia::SpatialComponent,
                             opennefia::MetaDataComponent>();
    for (auto e : npc_view) {
        const auto& npc_sp = npc_view.get<opennefia::SpatialComponent>(e);
        if (npc_sp.x == nx && npc_sp.y == ny) {
            const auto& meta = npc_view.get<opennefia::MetaDataComponent>(e);
            String npc_id(meta.proto_id.c_str());

            auto* npc_hp = reg.try_get<opennefia::HealthComponent>(e);
            if (npc_hp) {
                npc_hp->hp -= 3;
                if (npc_hp->hp <= 0) {
                    reg.destroy(e);
                    emit_signal("npc_died", npc_id);
                } else {
                    emit_signal("hero_bumped_npc", npc_id);
                }
            } else {
                emit_signal("hero_bumped_npc", npc_id);
            }
            advance_turn();
            return true;
        }
    }

    // 正常移動
    sp->x = nx;
    sp->y = ny;
    advance_turn();
    return true;
}

void opennefia_gd::OpenNefiaWorld::wait_turn() {
    if (game_over_) return;
    advance_turn();
}

void opennefia_gd::OpenNefiaWorld::advance_turn() {
    ++turn_count_;
    recompute_fov();                  // 先算 FOV（英雄移動後的視野）
    opennefia::SystemCtx ctx{ bus_ };
    em_.tick(ctx);                    // 執行所有系統（npc_ai_system 等；NPC 可能攻擊英雄）

    // 英雄死亡偵測（NPC 攻擊後）
    if (!game_over_) {
        if (const auto* hp = em_.registry().try_get<opennefia::HealthComponent>(hero_entity_)) {
            if (hp->hp <= 0) {
                game_over_ = true;
                emit_signal("game_over");
            }
        }
    }

    emit_signal("world_changed");
}

// ---- 狀態查詢 ---------------------------------------------------------------

int opennefia_gd::OpenNefiaWorld::get_hero_x() const {
    const auto* sp = em_.registry().try_get<opennefia::SpatialComponent>(hero_entity_);
    return sp ? sp->x : -1;
}

int opennefia_gd::OpenNefiaWorld::get_hero_y() const {
    const auto* sp = em_.registry().try_get<opennefia::SpatialComponent>(hero_entity_);
    return sp ? sp->y : -1;
}

int opennefia_gd::OpenNefiaWorld::get_turn_count() const {
    return turn_count_;
}

int opennefia_gd::OpenNefiaWorld::get_hero_hp() const {
    const auto* hp = em_.registry().try_get<opennefia::HealthComponent>(hero_entity_);
    return hp ? hp->hp : 0;
}

int opennefia_gd::OpenNefiaWorld::get_hero_max_hp() const {
    const auto* hp = em_.registry().try_get<opennefia::HealthComponent>(hero_entity_);
    return hp ? hp->max_hp : 0;
}
