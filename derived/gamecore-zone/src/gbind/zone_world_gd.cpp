#include "zone_world_gd.h"

#include "core/components/actor_component.h"
#include "core/components/spatial_component.h"
#include "core/components/npc_ai_component.h"
#include "core/components/health_component.h"
#include "core/components/item_component.h"
#include "core/components/combat_stats_component.h"
#include "core/components/hero_component.h"
#include "core/components/world_state_component.h"
#include "core/maps/map_data.h"
#include "core/maps/map_gen.h"
#include "core/systems/npc_ai_system.h"
#include "core/systems/fov_system.h"
#include "core/serialize/save_load.h"

#include <algorithm>
#include <random>
#include <filesystem>
#include <godot_cpp/variant/rect2i.hpp>
#include <godot_cpp/variant/color.hpp>

using namespace godot;

// 遊戲常數（取代 CVar）
static constexpr int MAP_W         = 60;
static constexpr int MAP_H         = 40;
static constexpr int NPC_CAP_BASE  = 4;
static constexpr int NPC_CAP_MAX   = 8;
static constexpr int FOV_RADIUS    = 8;
static constexpr int ITEM_PCT      = 60;
static constexpr int HERO_HP       = 20;
static constexpr int NPC_BASE_HP   = 5;
static constexpr int NPC_HP_SCALE  = 2;
static constexpr int NPC_ATK_BASE  = 2;
static constexpr int NPC_ATK_SCALE = 1;

// ---- static binding --------------------------------------------------------

void zone_gd::ZoneWorld::_bind_methods() {
    ClassDB::bind_method(D_METHOD("get_map_width"),  &ZoneWorld::get_map_width);
    ClassDB::bind_method(D_METHOD("get_map_height"), &ZoneWorld::get_map_height);
    ClassDB::bind_method(D_METHOD("is_walkable", "x", "y"), &ZoneWorld::is_walkable);
    ClassDB::bind_method(D_METHOD("generate_map_image", "cell_px"), &ZoneWorld::generate_map_image);
    ClassDB::bind_method(D_METHOD("move", "dx", "dy"), &ZoneWorld::move);
    ClassDB::bind_method(D_METHOD("wait_turn"), &ZoneWorld::wait_turn);
    ClassDB::bind_method(D_METHOD("get_hero_x"),      &ZoneWorld::get_hero_x);
    ClassDB::bind_method(D_METHOD("get_hero_y"),      &ZoneWorld::get_hero_y);
    ClassDB::bind_method(D_METHOD("get_turn_count"),  &ZoneWorld::get_turn_count);
    ClassDB::bind_method(D_METHOD("get_hero_hp"),     &ZoneWorld::get_hero_hp);
    ClassDB::bind_method(D_METHOD("get_hero_max_hp"), &ZoneWorld::get_hero_max_hp);
    ClassDB::bind_method(D_METHOD("get_npc_count"),   &ZoneWorld::get_npc_count);
    ClassDB::bind_method(D_METHOD("get_current_floor"), &ZoneWorld::get_current_floor);
    ClassDB::bind_method(D_METHOD("restart"),           &ZoneWorld::restart);
    ClassDB::bind_method(D_METHOD("save_game", "path"),     &ZoneWorld::save_game);
    ClassDB::bind_method(D_METHOD("load_game", "path"),     &ZoneWorld::load_game);
    ClassDB::bind_method(D_METHOD("has_save_game", "path"), &ZoneWorld::has_save_game);

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

zone_gd::ZoneWorld::ZoneWorld() = default;

void zone_gd::ZoneWorld::_ready() {
    setup_world();
    recompute_fov();
}

// ---- world / map setup ------------------------------------------------------

void zone_gd::ZoneWorld::setup_world() {
    setup_map();
    if (!systems_ready_) {
        em_.add_system(zone::npc_ai_system);
        systems_ready_ = true;
    }
}

void zone_gd::ZoneWorld::setup_map() {
    auto& reg = em_.registry();

    // 銷毀舊 NPC
    {
        std::vector<entt::entity> v;
        for (auto e : reg.view<zone::NpcAiComponent>()) v.push_back(e);
        for (auto e : v) reg.destroy(e);
    }
    // 銷毀舊物品
    {
        std::vector<entt::entity> v;
        for (auto e : reg.view<zone::ItemComponent>()) v.push_back(e);
        for (auto e : v) reg.destroy(e);
    }
    // 銷毀舊地圖
    if (map_entity_ != entt::null) {
        reg.destroy(map_entity_);
        map_entity_ = entt::null;
    }

    // 建立新地圖
    map_entity_ = em_.create();
    auto& map = em_.emplace<zone::MapData>(map_entity_, MAP_W, MAP_H);
    em_.emplace<zone::WorldStateComponent>(map_entity_,
        zone::WorldStateComponent{ turn_count_, current_floor_ });

    std::mt19937 rng(std::random_device{}());
    auto rooms = zone::generate_bsp_dungeon(map, rng);

    // 英雄：第一次建立，之後只更新位置（保留 HP）
    int hx = rooms.empty() ? MAP_W / 2 : rooms[0].cx();
    int hy = rooms.empty() ? MAP_H / 2 : rooms[0].cy();
    if (hero_entity_ == entt::null) {
        hero_entity_ = em_.create();
        reg.emplace<zone::HeroComponent>(hero_entity_);
        reg.emplace<zone::ActorComponent>(hero_entity_);
        reg.emplace<zone::SpatialComponent>(hero_entity_, hx, hy);
        reg.emplace<zone::HealthComponent>(hero_entity_, HERO_HP, HERO_HP);
    } else {
        if (auto* sp = reg.try_get<zone::SpatialComponent>(hero_entity_))
            { sp->x = hx; sp->y = hy; }
    }

    // 樓梯
    if (rooms.size() >= 2) {
        auto& tile = map.at(rooms.back().cx(), rooms.back().cy());
        tile.flags |= zone::TILE_STAIR_DOWN;
    }

    // NPC
    int npc_cap = std::min(NPC_CAP_BASE + current_floor_, NPC_CAP_MAX);
    int npc_count = 0;
    for (int r = 1; r < (int)rooms.size() && npc_count < npc_cap; ++r, ++npc_count) {
        int hp  = NPC_BASE_HP + (current_floor_ - 1) * NPC_HP_SCALE;
        int atk = NPC_ATK_BASE + (current_floor_ - 1) * NPC_ATK_SCALE;
        auto e = em_.create();
        reg.emplace<zone::NpcAiComponent>(e);
        reg.emplace<zone::ActorComponent>(e);
        reg.emplace<zone::SpatialComponent>(e, rooms[r].cx(), rooms[r].cy());
        reg.emplace<zone::HealthComponent>(e, hp, hp);
        reg.emplace<zone::CombatStatsComponent>(e,
            zone::CombatStatsComponent{ atk, 50 });
    }

    // 物品
    {
        std::uniform_int_distribution<int> pct(0, 99);
        for (int r = 1; r < (int)rooms.size() - 1; ++r) {
            if (pct(rng) >= ITEM_PCT) continue;
            int val = 5 + (current_floor_ - 1) * 2;
            auto e = em_.create();
            reg.emplace<zone::ItemComponent>(e,
                zone::ItemComponent{ zone::ItemType::health_potion, val });
            reg.emplace<zone::SpatialComponent>(e, rooms[r].x + 1, rooms[r].y + 1);
        }
    }
}

// ---- floor / restart --------------------------------------------------------

void zone_gd::ZoneWorld::next_floor() {
    ++current_floor_;
    setup_map();
    recompute_fov();
    emit_signal("floor_changed", current_floor_);
    emit_signal("world_changed");
}

void zone_gd::ZoneWorld::restart() {
    if (hero_entity_ != entt::null) {
        em_.registry().destroy(hero_entity_);
        hero_entity_ = entt::null;
    }
    game_over_     = false;
    turn_count_    = 0;
    current_floor_ = 1;
    setup_map();
    recompute_fov();
    emit_signal("world_changed");
}

// ---- FOV -------------------------------------------------------------------

void zone_gd::ZoneWorld::recompute_fov() {
    if (hero_entity_ == entt::null || map_entity_ == entt::null) return;
    const auto* sp = em_.registry().try_get<zone::SpatialComponent>(hero_entity_);
    if (!sp) return;
    auto& map = em_.get<zone::MapData>(map_entity_);
    zone::compute_fov(map, sp->x, sp->y, FOV_RADIUS);
}

// ---- advance_turn（actor poll entry point）---------------------------------

void zone_gd::ZoneWorld::advance_turn() {
    auto& reg = em_.registry();
    // Actor poll: 輪詢所有 ActorComponent 實體，對 NPC 執行 AI 系統。
    // 英雄行動由前端（玩家輸入）在呼叫 advance_turn() 之前完成，此處跳過。
    zone::npc_ai_system(reg, ctx_);
    recompute_fov();
    ++turn_count_;
    if (map_entity_ != entt::null)
        reg.get<zone::WorldStateComponent>(map_entity_).turn_count = turn_count_;
    emit_signal("world_changed");
}

// ---- 地圖查詢 ---------------------------------------------------------------

int zone_gd::ZoneWorld::get_map_width() const {
    if (map_entity_ == entt::null) return 0;
    return em_.get<zone::MapData>(map_entity_).width;
}
int zone_gd::ZoneWorld::get_map_height() const {
    if (map_entity_ == entt::null) return 0;
    return em_.get<zone::MapData>(map_entity_).height;
}
bool zone_gd::ZoneWorld::is_walkable(int x, int y) const {
    if (map_entity_ == entt::null) return false;
    const auto& map = em_.get<zone::MapData>(map_entity_);
    return map.in_bounds(x, y) && map.at(x, y).is_walkable();
}

// ---- 狀態查詢 ---------------------------------------------------------------

int zone_gd::ZoneWorld::get_hero_x() const {
    if (!em_.registry().valid(hero_entity_)) return 0;
    if (const auto* sp = em_.registry().try_get<zone::SpatialComponent>(hero_entity_)) return sp->x;
    return 0;
}
int zone_gd::ZoneWorld::get_hero_y() const {
    if (!em_.registry().valid(hero_entity_)) return 0;
    if (const auto* sp = em_.registry().try_get<zone::SpatialComponent>(hero_entity_)) return sp->y;
    return 0;
}
int zone_gd::ZoneWorld::get_turn_count()  const { return turn_count_; }
int zone_gd::ZoneWorld::get_hero_hp()     const {
    if (!em_.registry().valid(hero_entity_)) return 0;
    if (const auto* hp = em_.registry().try_get<zone::HealthComponent>(hero_entity_)) return hp->hp;
    return 0;
}
int zone_gd::ZoneWorld::get_hero_max_hp() const {
    if (!em_.registry().valid(hero_entity_)) return 0;
    if (const auto* hp = em_.registry().try_get<zone::HealthComponent>(hero_entity_)) return hp->max_hp;
    return 0;
}
int zone_gd::ZoneWorld::get_npc_count() const {
    return (int)em_.registry().view<zone::NpcAiComponent>().size();
}
int zone_gd::ZoneWorld::get_current_floor() const { return current_floor_; }

// ---- generate_map_image ----------------------------------------------------

godot::Ref<godot::Image> zone_gd::ZoneWorld::generate_map_image(int cell_px) const {
    if (map_entity_ == entt::null) return {};
    const auto& map = em_.get<zone::MapData>(map_entity_);
    auto& reg = em_.registry();
    Ref<Image> img = Image::create(map.width * cell_px, map.height * cell_px,
                                   false, Image::FORMAT_RGB8);

    const Color floor_c(0.40f, 0.35f, 0.25f), wall_c(0.12f, 0.10f, 0.08f);
    const Color hero_c (1.00f, 0.90f, 0.20f), npc_c (0.90f, 0.20f, 0.20f);
    const Color item_c (0.20f, 0.85f, 0.40f), black (0.00f, 0.00f, 0.00f);

    for (int x = 0; x < map.width; ++x)
        for (int y = 0; y < map.height; ++y) {
            Color c;
            if (map.is_visible(x, y))
                c = map.at(x, y).is_stair_down()
                    ? Color(0.80f, 0.65f, 0.10f)
                    : (map.at(x, y).is_walkable() ? floor_c : wall_c);
            else if (map.is_explored(x, y)) {
                Color b = map.at(x, y).is_walkable() ? floor_c : wall_c;
                c = Color(b.r * 0.4f, b.g * 0.4f, b.b * 0.4f);
            } else {
                c = black;
            }
            img->fill_rect(Rect2i(x*cell_px, y*cell_px, cell_px, cell_px), c);
        }

    for (auto e : reg.view<zone::ItemComponent, zone::SpatialComponent>()) {
        const auto& sp = reg.get<zone::SpatialComponent>(e);
        if (map.is_visible(sp.x, sp.y))
            img->fill_rect(Rect2i(sp.x*cell_px, sp.y*cell_px, cell_px, cell_px), item_c);
    }
    for (auto e : reg.view<zone::NpcAiComponent, zone::SpatialComponent>()) {
        const auto& sp = reg.get<zone::SpatialComponent>(e);
        if (map.is_visible(sp.x, sp.y))
            img->fill_rect(Rect2i(sp.x*cell_px, sp.y*cell_px, cell_px, cell_px), npc_c);
    }
    if (reg.valid(hero_entity_)) {
        if (const auto* sp = reg.try_get<zone::SpatialComponent>(hero_entity_))
            if (map.in_bounds(sp->x, sp->y))
                img->fill_rect(Rect2i(sp->x*cell_px, sp->y*cell_px, cell_px, cell_px), hero_c);
    }
    return img;
}

// ---- 動作介面 ---------------------------------------------------------------

bool zone_gd::ZoneWorld::move(int dx, int dy) {
    if (game_over_) return false;
    if (hero_entity_ == entt::null || map_entity_ == entt::null) return false;
    auto* sp = em_.registry().try_get<zone::SpatialComponent>(hero_entity_);
    if (!sp) return false;

    int nx = sp->x + dx, ny = sp->y + dy;
    const auto& map = em_.get<zone::MapData>(map_entity_);

    if (!map.in_bounds(nx, ny) || !map.at(nx, ny).is_walkable()) {
        emit_signal("hero_bumped_wall");
        return false;
    }

    auto& reg = em_.registry();

    // NPC 碰撞（英雄攻擊 NPC）
    for (auto e : reg.view<zone::NpcAiComponent, zone::SpatialComponent>()) {
        const auto& nsp = reg.get<zone::SpatialComponent>(e);
        if (nsp.x == nx && nsp.y == ny) {
            if (auto* hp = reg.try_get<zone::HealthComponent>(e)) {
                hp->hp -= 3;
                if (hp->hp <= 0) {
                    reg.destroy(e);
                    emit_signal("npc_died", String("npc"));
                } else {
                    emit_signal("hero_bumped_npc", String("npc"));
                }
            }
            advance_turn();
            return true;
        }
    }

    sp->x = nx;
    sp->y = ny;

    // 物品拾取（自動）
    for (auto e : reg.view<zone::ItemComponent, zone::SpatialComponent>()) {
        const auto& isp = reg.get<zone::SpatialComponent>(e);
        if (isp.x == sp->x && isp.y == sp->y) {
            const auto& item = reg.get<zone::ItemComponent>(e);
            int heal_done = 0;
            if (item.type == zone::ItemType::health_potion) {
                if (auto* hp = reg.try_get<zone::HealthComponent>(hero_entity_)) {
                    int healed = std::min(item.value, hp->max_hp - hp->hp);
                    hp->hp += healed;
                    heal_done = healed;
                }
            }
            reg.destroy(e);
            emit_signal("item_picked_up", String("health_potion"), heal_done);
            break;
        }
    }

    // 樓梯
    if (map.at(nx, ny).is_stair_down()) {
        next_floor();
        return true;
    }

    // 英雄死亡判定
    if (const auto* hp = reg.try_get<zone::HealthComponent>(hero_entity_)) {
        if (hp->hp <= 0) {
            game_over_ = true;
            emit_signal("game_over");
        }
    }

    advance_turn();
    return true;
}

void zone_gd::ZoneWorld::wait_turn() {
    if (!game_over_) advance_turn();
}

// ---- 存讀檔 ----------------------------------------------------------------

bool zone_gd::ZoneWorld::save_game(const godot::String& path) {
    try {
        // 存檔前同步最新遊戲狀態至 WorldStateComponent
        if (map_entity_ != entt::null) {
            if (auto* ws = em_.registry().try_get<zone::WorldStateComponent>(map_entity_)) {
                ws->turn_count    = turn_count_;
                ws->current_floor = current_floor_;
            }
        }
        std::filesystem::path fpath{ std::string(path.utf8().get_data()) };
        zone::serialize::save(em_.registry(), fpath);
        return true;
    } catch (...) { return false; }
}

bool zone_gd::ZoneWorld::load_game(const godot::String& path) {
    try {
        std::filesystem::path fpath{ std::string(path.utf8().get_data()) };
        if (!std::filesystem::exists(fpath)) return false;

        // 清空 registry 後重新載入
        em_.registry().clear();
        hero_entity_ = entt::null;
        map_entity_  = entt::null;

        zone::serialize::load(em_.registry(), fpath);

        for (auto e : em_.registry().view<zone::HeroComponent>())
            { hero_entity_ = e; break; }
        for (auto e : em_.registry().view<zone::MapData>())
            { map_entity_ = e; break; }
        if (map_entity_ != entt::null) {
            if (const auto* ws = em_.registry().try_get<zone::WorldStateComponent>(map_entity_)) {
                turn_count_    = ws->turn_count;
                current_floor_ = ws->current_floor;
            }
        }
        recompute_fov();
        return true;
    } catch (...) { return false; }
}

bool zone_gd::ZoneWorld::has_save_game(const godot::String& path) const {
    return std::filesystem::exists(std::string(path.utf8().get_data()));
}
