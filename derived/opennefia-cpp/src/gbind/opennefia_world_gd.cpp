#include "opennefia_world_gd.h"

#include "core/components/meta_data_component.h"
#include "core/components/spatial_component.h"
#include "core/components/npc_ai_component.h"
#include "core/components/health_component.h"
#include "core/components/item_component.h"
#include "core/components/combat_stats_component.h"
#include "core/components/hero_component.h"
#include "core/maps/map_data.h"
#include "core/maps/map_gen.h"
#include "core/systems/npc_ai_system.h"
#include "core/systems/fov_system.h"
#include "core/components/world_state_component.h"
#include "core/serialize/save_load.h"
#include <algorithm>
#include <cctype>
#include <random>
#include <filesystem>
#include <yaml-cpp/yaml.h>

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
    ClassDB::bind_method(D_METHOD("get_npc_count"),   &OpenNefiaWorld::get_npc_count);
    ClassDB::bind_method(D_METHOD("get_current_floor"), &OpenNefiaWorld::get_current_floor);
    ClassDB::bind_method(D_METHOD("restart"),           &OpenNefiaWorld::restart);

    ClassDB::bind_method(D_METHOD("save_game", "path"),     &OpenNefiaWorld::save_game);
    ClassDB::bind_method(D_METHOD("load_game", "path"),     &OpenNefiaWorld::load_game);
    ClassDB::bind_method(D_METHOD("has_save_game", "path"), &OpenNefiaWorld::has_save_game);

    ADD_SIGNAL(MethodInfo("world_changed"));
    ADD_SIGNAL(MethodInfo("floor_changed",
        PropertyInfo(Variant::INT, "floor_num")));
    ADD_SIGNAL(MethodInfo("hero_bumped_wall"));
    ADD_SIGNAL(MethodInfo("hero_bumped_npc",
        PropertyInfo(Variant::STRING, "npc_id")));
    ADD_SIGNAL(MethodInfo("npc_died",
        PropertyInfo(Variant::STRING, "npc_id")));
    ADD_SIGNAL(MethodInfo("item_picked_up",
        PropertyInfo(Variant::STRING, "item_name"),
        PropertyInfo(Variant::INT,    "heal_amount")));
    ADD_SIGNAL(MethodInfo("game_over"));
}

// ---- ctor / lifecycle -------------------------------------------------------

opennefia_gd::OpenNefiaWorld::OpenNefiaWorld() = default;

void opennefia_gd::OpenNefiaWorld::_ready() {
    setup_test_world();
    recompute_fov();  // 初始視野（英雄出生位置）
}

// ---- CVar 初始化（只跑一次）-----------------------------------------------

void opennefia_gd::OpenNefiaWorld::init_cvars() {
    if (svc_.cvars.has("game.map_width")) return;
    auto& c = svc_.cvars;
    c.reg<int>("game.map_width",          60,  "地圖寬度（格）");
    c.reg<int>("game.map_height",         40,  "地圖高度（格）");
    c.reg<int>("game.npc_cap_base",        4,  "NPC 上限基礎值（+ 樓層數）");
    c.reg<int>("game.npc_cap_max",         8,  "NPC 上限最大值");
    c.reg<int>("game.fov_radius",          8,  "FOV 半徑（格）");
    c.reg<int>("game.item_spawn_pct",     60,  "房間物品生成機率 0-100");
}

// ---- 原型系統初始化（只跑一次）--------------------------------------------

void opennefia_gd::OpenNefiaWorld::init_prototypes() {
    if (pm_ready_) return;

    pm_.register_loader("NpcAi",
        [](entt::registry& reg, entt::entity e, const YAML::Node&) {
            reg.emplace_or_replace<opennefia::NpcAiComponent>(e);
        });

    pm_.register_loader("CombatStats",
        [](entt::registry& reg, entt::entity e, const YAML::Node& n) {
            opennefia::CombatStatsComponent s;
            if (n["attack"])       s.attack       = n["attack"].as<int>();
            if (n["move_chance"])  s.move_chance  = n["move_chance"].as<int>();
            if (n["variant"])      s.variant      = static_cast<opennefia::NpcVariant>(
                                                        n["variant"].as<int>());
            if (n["base_hp"])      s.base_hp      = n["base_hp"].as<int>();
            if (n["hp_per_floor"]) s.hp_per_floor = n["hp_per_floor"].as<int>();
            reg.emplace_or_replace<opennefia::CombatStatsComponent>(e, s);
        });

    pm_.register_loader("Health",
        [](entt::registry& reg, entt::entity e, const YAML::Node& n) {
            int hp = n["hp"] ? n["hp"].as<int>() : 10;
            reg.emplace_or_replace<opennefia::HealthComponent>(e, hp, hp);
        });

    pm_.register_loader("Item",
        [](entt::registry& reg, entt::entity e, const YAML::Node& n) {
            opennefia::ItemComponent item;
            if (n["base_value"])     item.value          = n["base_value"].as<int>();
            if (n["value_per_floor"]) item.value_per_floor = n["value_per_floor"].as<int>();
            reg.emplace_or_replace<opennefia::ItemComponent>(e, item);
        });

    pm_.register_loader("Hero",
        [](entt::registry& reg, entt::entity e, const YAML::Node&) {
            reg.emplace_or_replace<opennefia::HeroComponent>(e);
        });

    pm_.load_file(std::string(OPENNEFIA_DATA_DIR) + "/game_prototypes.yaml");
    pm_.resolve_inheritance();
    pm_ready_ = true;
}

// ---- 測試世界建構 -----------------------------------------------------------
//
// 委派給 setup_map()；NPC AI 系統只注冊一次。
void opennefia_gd::OpenNefiaWorld::setup_test_world() {
    init_cvars();
    init_prototypes();
    setup_map();
    if (!systems_ready_) {
        em_.add_system(opennefia::npc_ai_system);
        systems_ready_ = true;
    }
}

// ---- 地圖生成（可重複呼叫） ------------------------------------------------
//
// 地圖尺寸、NPC 上限、FOV 半徑、物品機率均由 CVar 控制。
void opennefia_gd::OpenNefiaWorld::setup_map() {
    const int W = svc_.cvars.get<int>("game.map_width");
    const int H = svc_.cvars.get<int>("game.map_height");

    // 銷毀舊 NPC（view 迭代前先收集，避免邊改邊迭代）
    {
        auto& reg = em_.registry();
        std::vector<entt::entity> npcs;
        for (auto e : reg.view<opennefia::NpcAiComponent>()) npcs.push_back(e);
        for (auto e : npcs) reg.destroy(e);
    }

    // 銷毀舊物品
    {
        auto& reg = em_.registry();
        std::vector<entt::entity> items;
        for (auto e : reg.view<opennefia::ItemComponent>()) items.push_back(e);
        for (auto e : items) reg.destroy(e);
    }

    // 銷毀舊地圖
    if (map_entity_ != entt::null) {
        em_.registry().destroy(map_entity_);
        map_entity_ = entt::null;
    }

    // 建立新地圖
    map_entity_ = em_.create();
    auto& map = em_.emplace<opennefia::MapData>(map_entity_, W, H);
    // WorldStateComponent 掛在 map_entity_ 上，隨 save/load 自動序列化
    em_.emplace<opennefia::WorldStateComponent>(map_entity_,
        opennefia::WorldStateComponent{ turn_count_, current_floor_ });

    std::mt19937 rng(std::random_device{}());
    auto rooms = opennefia::generate_bsp_dungeon(map, rng);

    // 英雄：第一次從原型生成；之後只更新位置（保留 HP）
    int hx = rooms.empty() ? W / 2 : rooms[0].cx();
    int hy = rooms.empty() ? H / 2 : rooms[0].cy();
    if (hero_entity_ == entt::null) {
        hero_entity_ = pm_.spawn(em_, "Hero");
        em_.emplace<opennefia::SpatialComponent>(hero_entity_, hx, hy);
    } else {
        auto* sp = em_.registry().try_get<opennefia::SpatialComponent>(hero_entity_);
        if (sp) { sp->x = hx; sp->y = hy; }
    }

    // 樓梯：放在最後一個房間中心（需至少 2 個房間）
    if (rooms.size() >= 2) {
        auto& stair_tile = map.at(rooms.back().cx(), rooms.back().cy());
        stair_tile.flags |= opennefia::TILE_STAIR_DOWN;
    }

    // NPC：依樓層機率選原型 id，生成後套用層數 HP 縮放
    auto pick_proto = [&](int /*idx*/) -> std::string {
        std::uniform_int_distribution<int> d(0, 9);
        int r = d(rng);
        if (current_floor_ <= 2)
            return (r < 7) ? "Putit" : "Bat";
        if (current_floor_ <= 4) {
            if (r < 3) return "Putit";
            if (r < 7) return "Warrior";
            return "Bat";
        }
        if (r < 2) return "Putit";
        if (r < 7) return "Warrior";
        return "Bat";
    };

    int  npc_cap   = std::min(svc_.cvars.get<int>("game.npc_cap_base") + current_floor_,
                              svc_.cvars.get<int>("game.npc_cap_max"));
    int  npc_count = 0;
    auto& reg = em_.registry();
    for (int r = 1; r < static_cast<int>(rooms.size()) && npc_count < npc_cap; ++r, ++npc_count) {
        std::string proto_id = pick_proto(npc_count);
        auto e = pm_.spawn(em_, proto_id);

        reg.emplace<opennefia::SpatialComponent>(e, rooms[r].cx(), rooms[r].cy());

        // 層數縮放：base_hp + (floor-1)*hp_per_floor → 套用至 HealthComponent
        if (const auto* stats = reg.try_get<opennefia::CombatStatsComponent>(e)) {
            int hp = stats->base_hp + (current_floor_ - 1) * stats->hp_per_floor;
            reg.emplace_or_replace<opennefia::HealthComponent>(e, hp, hp);
        }

        // 唯一實例 ID（小寫 proto_id + "_" + 序號）
        std::string lower_id = proto_id;
        std::transform(lower_id.begin(), lower_id.end(), lower_id.begin(),
                       [](unsigned char c){ return static_cast<char>(std::tolower(c)); });
        reg.get<opennefia::MetaDataComponent>(e).proto_id = lower_id + "_" + std::to_string(npc_count);
    }

    // 物品：中間房間（跳過英雄房 0 與樓梯房 back）各有 60% 機率出現回血藥
    {
        std::uniform_int_distribution<int> chance(0, 99);
        int n_rooms = static_cast<int>(rooms.size());
        for (int r = 1; r < n_rooms - 1; ++r) {
            if (chance(rng) >= svc_.cvars.get<int>("game.item_spawn_pct")) continue;
            auto e = pm_.spawn(em_, "HealthPotion");
            reg.emplace<opennefia::SpatialComponent>(e, rooms[r].x + 1, rooms[r].y + 1);
            // 層數縮放：base_value + (floor-1)*value_per_floor
            auto& item = reg.get<opennefia::ItemComponent>(e);
            item.value += (current_floor_ - 1) * item.value_per_floor;
        }
    }
}

// ---- 樓層切換 ---------------------------------------------------------------

void opennefia_gd::OpenNefiaWorld::next_floor() {
    ++current_floor_;
    setup_map();
    recompute_fov();
    emit_signal("floor_changed", current_floor_);
    emit_signal("world_changed");
}

// ---- 完整重置 ---------------------------------------------------------------

void opennefia_gd::OpenNefiaWorld::restart() {
    // 銷毀英雄
    if (hero_entity_ != entt::null) {
        em_.registry().destroy(hero_entity_);
        hero_entity_ = entt::null;
    }
    // 重置狀態
    game_over_     = false;
    turn_count_    = 0;
    current_floor_ = 1;
    // 重新建立地圖（setup_map 裡會重建英雄，因為 hero_entity_ == entt::null）
    setup_map();
    recompute_fov();
    emit_signal("world_changed");
}

// ---- 視野計算 ---------------------------------------------------------------

void opennefia_gd::OpenNefiaWorld::recompute_fov() {
    if (hero_entity_ == entt::null || map_entity_ == entt::null) return;
    const auto* sp = em_.registry().try_get<opennefia::SpatialComponent>(hero_entity_);
    if (!sp) return;
    auto& map = em_.get<opennefia::MapData>(map_entity_);
    const int radius = svc_.cvars.has("game.fov_radius")
                       ? svc_.cvars.get<int>("game.fov_radius") : 8;
    opennefia::compute_fov(map, sp->x, sp->y, radius);
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
                if (map.at(x, y).is_stair_down()) {
                    c = Color(0.80f, 0.65f, 0.10f);  // 金黃色樓梯
                } else {
                    c = map.at(x, y).is_walkable() ? floor_color : wall_color;
                }
            } else if (map.is_explored(x, y)) {
                Color base = map.at(x, y).is_walkable() ? floor_color : wall_color;
                c = Color(base.r * 0.4f, base.g * 0.4f, base.b * 0.4f);
            } else {
                c = black;
            }
            img->fill_rect(Rect2i(x*cell_px, y*cell_px, cell_px, cell_px), c);
        }
    }

    // 物品（綠點，只在可見格顯示，層級低於 NPC）
    const Color item_color(0.20f, 0.85f, 0.40f);
    auto item_view = em_.registry().view<opennefia::ItemComponent,
                                         opennefia::SpatialComponent>();
    for (auto e : item_view) {
        const auto& sp = item_view.get<opennefia::SpatialComponent>(e);
        if (map.is_visible(sp.x, sp.y))
            img->fill_rect(Rect2i(sp.x*cell_px, sp.y*cell_px, cell_px, cell_px), item_color);
    }

    // NPC（依類型著色，只在可見格顯示）
    // putit=紫(0.6,0.2,0.7)  warrior=橙(0.9,0.5,0.1)  bat=青(0.2,0.8,0.9)
    auto npc_view = em_.registry().view<opennefia::NpcAiComponent,
                                        opennefia::SpatialComponent>();
    for (auto e : npc_view) {
        const auto& sp = npc_view.get<opennefia::SpatialComponent>(e);
        if (!map.is_visible(sp.x, sp.y)) continue;
        Color nc = npc_color;
        if (const auto* stats = em_.registry().try_get<opennefia::CombatStatsComponent>(e)) {
            switch (stats->variant) {
                case opennefia::NpcVariant::putit:   nc = Color(0.60f, 0.20f, 0.70f); break;
                case opennefia::NpcVariant::warrior: nc = Color(0.90f, 0.50f, 0.10f); break;
                case opennefia::NpcVariant::bat:     nc = Color(0.20f, 0.80f, 0.90f); break;
                default: break;
            }
        }
        img->fill_rect(Rect2i(sp.x*cell_px, sp.y*cell_px, cell_px, cell_px), nc);
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

    // 物品拾取（自動）
    {
        auto& reg = em_.registry();
        entt::entity pickup_ent = entt::null;
        auto iview = reg.view<opennefia::ItemComponent,
                              opennefia::SpatialComponent,
                              opennefia::MetaDataComponent>();
        for (auto e : iview) {
            const auto& isp = iview.get<opennefia::SpatialComponent>(e);
            if (isp.x == sp->x && isp.y == sp->y) { pickup_ent = e; break; }
        }
        if (pickup_ent != entt::null && reg.valid(pickup_ent)) {
            const auto& item = reg.get<opennefia::ItemComponent>(pickup_ent);
            const auto& meta = reg.get<opennefia::MetaDataComponent>(pickup_ent);
            if (item.type == opennefia::ItemType::health_potion) {
                auto* hp = reg.try_get<opennefia::HealthComponent>(hero_entity_);
                if (hp) hp->hp = std::min(hp->hp + item.value, hp->max_hp);
            }
            int heal_done = item.value;
            String iname(meta.proto_id.c_str());
            reg.destroy(pickup_ent);
            emit_signal("item_picked_up", iname, heal_done);
        }
    }

    // 踩到下樓梯
    if (map.at(sp->x, sp->y).is_stair_down()) {
        next_floor();
        return true;
    }

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

int opennefia_gd::OpenNefiaWorld::get_current_floor() const {
    return current_floor_;
}

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

int opennefia_gd::OpenNefiaWorld::get_npc_count() const {
    return static_cast<int>(em_.registry().view<opennefia::NpcAiComponent>().size());
}

// ---- 存讀檔 -----------------------------------------------------------------

bool opennefia_gd::OpenNefiaWorld::save_game(const godot::String& path_gd) {
    if (map_entity_ == entt::null || hero_entity_ == entt::null) return false;

    // 存檔前同步最新遊戲狀態至 WorldStateComponent
    auto* ws = em_.registry().try_get<opennefia::WorldStateComponent>(map_entity_);
    if (ws) {
        ws->turn_count    = turn_count_;
        ws->current_floor = current_floor_;
    }

    std::filesystem::path path{ std::string(path_gd.utf8().get_data()) };
    opennefia::serialize::save(em_.registry(), path);
    return true;
}

bool opennefia_gd::OpenNefiaWorld::load_game(const godot::String& path_gd) {
    std::filesystem::path path{ std::string(path_gd.utf8().get_data()) };
    if (!std::filesystem::exists(path)) return false;

    // 清空 registry（保留 systems_ vector，不重置 systems_ready_）
    em_.registry().clear();
    map_entity_  = entt::null;
    hero_entity_ = entt::null;
    game_over_   = false;

    // 反序列化（entt::snapshot_loader 填入所有 component）
    opennefia::serialize::load(em_.registry(), path);

    // 重建 C++ 指標：map_entity_ 為持有 MapData 的實體
    auto& reg = em_.registry();
    for (auto e : reg.view<opennefia::MapData>()) { map_entity_ = e; break; }

    // hero_entity_：正向標記 HeroComponent（已序列化，存讀檔後仍在）
    for (auto e : reg.view<opennefia::HeroComponent>()) {
        hero_entity_ = e;
        break;
    }

    // 從 WorldStateComponent 還原遊戲狀態
    if (map_entity_ != entt::null) {
        if (const auto* ws = reg.try_get<opennefia::WorldStateComponent>(map_entity_)) {
            turn_count_    = ws->turn_count;
            current_floor_ = ws->current_floor;
        }
    }

    // 系統只需注冊一次（systems_ vector 不序列化，但 systems_ready_ 跨呼叫保持 true）
    if (!systems_ready_) {
        em_.add_system(opennefia::npc_ai_system);
        systems_ready_ = true;
    }

    recompute_fov();
    emit_signal("world_changed");
    return true;
}

bool opennefia_gd::OpenNefiaWorld::has_save_game(const godot::String& path_gd) const {
    std::filesystem::path path{ std::string(path_gd.utf8().get_data()) };
    return std::filesystem::exists(path);
}
