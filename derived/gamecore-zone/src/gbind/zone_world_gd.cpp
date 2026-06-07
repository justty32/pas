#include "zone_world_gd.h"

#include "core/components/actor_component.h"
#include "core/components/spatial_component.h"
#include "core/components/npc_ai_component.h"
#include "core/components/health_component.h"
#include "core/components/item_component.h"
#include "core/components/combat_stats_component.h"
#include "core/components/hero_component.h"
#include "core/components/world_state_component.h"
#include "core/components/energy_component.h"
#include "core/components/player_controlled_component.h"
#include "core/turn/action.h"
#include "core/turn/move_dir.h"
#include "core/turn/npc_brain.h"
#include "core/turn/timed_effect.h"
#include "core/components/ongoing_action_component.h"
#include "core/components/energy_component.h"
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
#include <godot_cpp/variant/utility_functions.hpp>

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
    ClassDB::bind_method(D_METHOD("set_scheduler_mode", "mode"), &ZoneWorld::set_scheduler_mode);
    ClassDB::bind_method(D_METHOD("get_scheduler_mode"), &ZoneWorld::get_scheduler_mode);
    ClassDB::bind_method(D_METHOD("submit_hero_move", "dx", "dy"), &ZoneWorld::submit_hero_move);
    ClassDB::bind_method(D_METHOD("submit_hero_wait"), &ZoneWorld::submit_hero_wait);
    ClassDB::bind_method(D_METHOD("submit_hero_cast", "turns"), &ZoneWorld::submit_hero_cast);
    ClassDB::bind_method(D_METHOD("submit_hero_skill", "name"), &ZoneWorld::submit_hero_skill);
    ClassDB::bind_method(D_METHOD("step_scheduler"), &ZoneWorld::step_scheduler);
    ClassDB::bind_method(D_METHOD("hero_is_waiting"), &ZoneWorld::hero_is_waiting);
    ClassDB::bind_method(D_METHOD("get_hero_status"),  &ZoneWorld::get_hero_status);
    ClassDB::bind_method(D_METHOD("get_hero_effects"), &ZoneWorld::get_hero_effects);
    ClassDB::bind_method(D_METHOD("get_debug_text"),   &ZoneWorld::get_debug_text);
    ClassDB::bind_method(D_METHOD("get_world_clock"),  &ZoneWorld::get_world_clock);
    ClassDB::bind_method(D_METHOD("set_trace_enabled", "on"), &ZoneWorld::set_trace_enabled);
    ClassDB::bind_method(D_METHOD("get_trace_enabled"), &ZoneWorld::get_trace_enabled);
    ClassDB::bind_method(D_METHOD("get_debug_log"),    &ZoneWorld::get_debug_log);
    ClassDB::bind_method(D_METHOD("clear_debug_log"),  &ZoneWorld::clear_debug_log);
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
    setup_scheduler();
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
        reg.emplace<zone::CombatStatsComponent>(hero_entity_);   // 排程器路徑：英雄攻擊力
        reg.emplace<zone::PlayerControlledComponent>(hero_entity_);
        reg.emplace<zone::EnergyComponent>(hero_entity_);        // 行動值（排程器路徑用）
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
        const bool caster = (npc_count % 2 == 0);
        auto e = em_.create();
        reg.emplace<zone::NpcAiComponent>(e).is_caster = caster;  // 半數為施法者
        reg.emplace<zone::ActorComponent>(e);
        reg.emplace<zone::SpatialComponent>(e, rooms[r].cx(), rooms[r].cy());
        reg.emplace<zone::HealthComponent>(e, hp, hp);
        reg.emplace<zone::CombatStatsComponent>(e,
            zone::CombatStatsComponent{ atk, 50 });
        // 速度差：施法者慢(80)、近戰快(130)，方便在能量排程器面板觀察行動值差異
        reg.emplace<zone::EnergyComponent>(e).speed_mod = caster ? 80 : 130;
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
    if (hero_entity_ != entt::null && em_.registry().valid(hero_entity_)) {
        em_.registry().destroy(hero_entity_);
    }
    hero_entity_ = entt::null;
    game_over_     = false;
    turn_count_    = 0;
    current_floor_ = 1;
    world_clock_   = 0;
    scheduler_ = zone::make_scheduler(static_cast<zone::SchedulerMode>(scheduler_mode_));  // 清舊 pending/waiting
    trace_log_.clear();
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
            // NPC 反擊後的英雄死亡判定
            if (reg.valid(hero_entity_)) {
                if (const auto* hero_hp = reg.try_get<zone::HealthComponent>(hero_entity_)) {
                    if (hero_hp->hp <= 0 && !game_over_) {
                        game_over_ = true;
                        emit_signal("game_over");
                    }
                }
            }
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

// ---- 排程器路徑（可切換 A/B/C）---------------------------------------------

void zone_gd::ZoneWorld::setup_scheduler() {
    effects_.register_kind(zone::ActionKind::Move,   &move_fx_);
    effects_.register_kind(zone::ActionKind::Attack, &move_fx_);  // 撞擊攻擊也走 Move 效果
    effects_.register_kind(zone::ActionKind::Wait,   &wait_fx_);
    effects_.register_kind(zone::ActionKind::Cast,   &cast_fx_);

    // 資料驅動技能庫：先試讀 JSON，失敗用硬編後備
    bool loaded = false;
#ifdef ZONE_DATA_DIR
    loaded = action_lib_.load_json(std::string(ZONE_DATA_DIR) + "/actions.json");
#endif
    if (!loaded) action_lib_.load_defaults();
    lib_fx_.lib = &action_lib_;
    effects_.register_kind(zone::ActionKind::Skill, &lib_fx_);
    if (!scheduler_)
        scheduler_ = zone::make_scheduler(static_cast<zone::SchedulerMode>(scheduler_mode_));
}

zone::TurnWorld zone_gd::ZoneWorld::make_turn_world() {
    zone::TurnWorld w{
        em_.registry(),
        effects_,
        [this](entt::registry& r, entt::entity e) { return npc_decide(r, e); }
    };
    if (map_entity_ != entt::null)
        w.map = &em_.get<zone::MapData>(map_entity_);
    w.events = &events_;
    w.on_actor_turn = [](zone::TurnWorld& tw, entt::entity e) {
        zone::tick_timed_effects(tw, e);   // 每個 actor 回合開始 tick DoT
    };
    if (trace_enabled_)
        w.trace = [this](const std::string& s) { on_trace(s); };
    return w;
}

zone::Action zone_gd::ZoneWorld::npc_decide(entt::registry& reg, entt::entity e) {
    return zone::decide_chase(reg, e, hero_entity_, action_lib_);
}

void zone_gd::ZoneWorld::set_scheduler_mode(int mode) {
    scheduler_mode_ = mode;
    scheduler_ = zone::make_scheduler(static_cast<zone::SchedulerMode>(mode));
}

int zone_gd::ZoneWorld::get_scheduler_mode() const { return scheduler_mode_; }

void zone_gd::ZoneWorld::submit_hero_move(int dx, int dy) {
    if (!scheduler_) setup_scheduler();
    scheduler_->submit(hero_entity_,
        zone::Action{ zone::ActionKind::Move, zone::encode_dir(dx, dy), 1 });
    bump_turn_count();
}

void zone_gd::ZoneWorld::submit_hero_wait() {
    if (!scheduler_) setup_scheduler();
    scheduler_->submit(hero_entity_, zone::Action{ zone::ActionKind::Wait, 0, 1 });
    bump_turn_count();
}

void zone_gd::ZoneWorld::submit_hero_cast(int turns) {
    if (!scheduler_) setup_scheduler();
    if (turns < 1) turns = 1;
    scheduler_->submit(hero_entity_, zone::Action{ zone::ActionKind::Cast, 0, turns });
    bump_turn_count();
}

void zone_gd::ZoneWorld::submit_hero_skill(const godot::String& name) {
    if (!scheduler_) setup_scheduler();
    int idx = action_lib_.find(std::string(name.utf8().get_data()));
    if (idx < 0) return;
    const int weight = action_lib_.at(idx).weight;
    scheduler_->submit(hero_entity_,
        zone::Action{ zone::ActionKind::Skill, 0, weight, idx });
    bump_turn_count();
}

void zone_gd::ZoneWorld::bump_turn_count() {
    ++turn_count_;
    if (map_entity_ != entt::null)
        em_.registry().get<zone::WorldStateComponent>(map_entity_).turn_count = turn_count_;
}

bool zone_gd::ZoneWorld::step_scheduler() {
    if (game_over_) return true;
    if (!scheduler_) setup_scheduler();
    events_.clear();
    auto w = make_turn_world();
    if (trace_enabled_)
        on_trace("── step (clock=" + std::to_string(world_clock_)
            + ", turn=" + std::to_string(turn_count_) + ") ──");
    scheduler_->advance(w);
    world_clock_ += w.clock;   // 累計世界時鐘（make_turn_world 每次從 0 起算）
    drain_events();
    return hero_is_waiting();
}

bool zone_gd::ZoneWorld::hero_is_waiting() const {
    return scheduler_ && scheduler_->waiting_actor() == hero_entity_;
}

godot::String zone_gd::ZoneWorld::get_hero_status() const {
    using godot::String;
    if (hero_entity_ == entt::null) return String::utf8("—");
    const auto& reg = em_.registry();
    if (const auto* og = reg.try_get<zone::OngoingActionComponent>(hero_entity_)) {
        const zone::Action& a = og->action;
        String name;
        if (a.kind == zone::ActionKind::Skill && a.def >= 0 && a.def < action_lib_.size())
            name = String::utf8(action_lib_.at(a.def).name.c_str());
        else if (a.kind == zone::ActionKind::Cast) name = String::utf8("詠唱");
        else name = String::utf8("動作");
        return String::utf8("詠唱 ") + name + " "
             + String::num_int64(og->progress) + "/" + String::num_int64(a.weight);
    }
    if (scheduler_ && scheduler_->waiting_actor() == hero_entity_) return String::utf8("待命");
    return String::utf8("行動中");
}

int zone_gd::ZoneWorld::get_world_clock() const { return static_cast<int>(world_clock_); }

void zone_gd::ZoneWorld::set_trace_enabled(bool on) { trace_enabled_ = on; }
bool zone_gd::ZoneWorld::get_trace_enabled() const { return trace_enabled_; }
void zone_gd::ZoneWorld::clear_debug_log() { trace_log_.clear(); }

void zone_gd::ZoneWorld::on_trace(const std::string& line) {
    trace_log_.push_back(line);
    if (trace_log_.size() > 300)
        trace_log_.erase(trace_log_.begin(),
                         trace_log_.begin() + (trace_log_.size() - 300));
    godot::UtilityFunctions::print(godot::String::utf8(line.c_str()));  // 即時主控台 print
}

godot::String zone_gd::ZoneWorld::get_debug_log() const {
    using godot::String;
    String s;
    const std::size_t n = trace_log_.size();
    const std::size_t start = n > 24 ? n - 24 : 0;  // 最近 24 行
    for (std::size_t i = start; i < n; ++i)
        s += String::utf8(trace_log_[i].c_str()) + "\n";
    return s;
}

namespace {
// 動作標籤（含 Skill 名稱查庫）
godot::String fmt_action(const zone::Action& a, const zone::ActionLibrary& lib) {
    using godot::String;
    String name;
    if (a.kind == zone::ActionKind::Skill && a.def >= 0 && a.def < lib.size())
        name = String::utf8(lib.at(a.def).name.c_str());
    else if (a.kind == zone::ActionKind::Cast) name = String::utf8("詠唱");
    else if (a.kind == zone::ActionKind::Move) name = String::utf8("移動");
    else if (a.kind == zone::ActionKind::Wait) name = String::utf8("等待");
    else if (a.kind == zone::ActionKind::Idle) name = String::utf8("待命");
    else name = String::utf8("動作");
    return name;
}
godot::String fmt_effects_of(const entt::registry& reg, entt::entity e) {
    using godot::String;
    const auto* te = reg.try_get<zone::TimedEffectsComponent>(e);
    if (!te || te->effects.empty()) return String("-");
    String s;
    for (const auto& ef : te->effects) {
        String n = ef.kind == zone::TimedEffectKind::Burning ? String::utf8("燃燒")
                 : ef.kind == zone::TimedEffectKind::Poison  ? String::utf8("中毒")
                 :                                             String::utf8("回復");
        s += n + String::num_int64(ef.power) + String::utf8("(剩")
           + String::num_int64(ef.turns_left) + String::utf8(") ");
    }
    return s;
}
const char* mode_label(int m) {
    switch (m) {
        case 0: return "A:能量瞬發";
        case 1: return "B:能量+channel";
        case 2: return "C:純tick";
        default: return "?";
    }
}
} // namespace

godot::String zone_gd::ZoneWorld::get_debug_text() const {
    using godot::String;
    const auto& reg = em_.registry();

    // 標頭：排程器 / 時鐘 / 回合 / 樓層 / waiting
    String waiting = String::utf8("無");
    if (scheduler_) {
        entt::entity wa = scheduler_->waiting_actor();
        if (wa != entt::null)
            waiting = String("#") + String::num_int64(static_cast<int>(entt::to_integral(wa) & 0xFFFFFu))
                    + (wa == hero_entity_ ? String::utf8("(英雄)") : String());
    }
    String out = String::utf8("排程器 ") + String::utf8(mode_label(scheduler_mode_))
        + String::utf8("  時鐘 ") + String::num_int64(world_clock_) + String::utf8(" ticks")
        + String::utf8("  回合 ") + String::num_int64(turn_count_)
        + String::utf8("  樓層 ") + String::num_int64(current_floor_)
        + String::utf8("  等待 ") + waiting
        + (game_over_ ? String::utf8("  [GAME OVER]") : String()) + "\n";

    // 逐 actor（英雄優先列出）
    auto dump_actor = [&](entt::entity e) {
        const bool is_hero = (e == hero_entity_);
        const auto* sp = reg.try_get<zone::SpatialComponent>(e);
        String line = (is_hero ? String::utf8("◆英雄 #") : String::utf8("·NPC  #"))
            + String::num_int64(static_cast<int>(entt::to_integral(e) & 0xFFFFFu));
        if (sp) line += String::utf8(" (") + String::num_int64(sp->x) + ","
                      + String::num_int64(sp->y) + ")";
        if (const auto* hp = reg.try_get<zone::HealthComponent>(e))
            line += String::utf8("  HP ") + String::num_int64(hp->hp) + "/" + String::num_int64(hp->max_hp);
        if (const auto* en = reg.try_get<zone::EnergyComponent>(e))
            line += String::utf8("  能量 ") + String::num_int64(en->value) + "/1000 spd"
                  + String::num_int64(en->speed_mod);
        if (const auto* og = reg.try_get<zone::OngoingActionComponent>(e))
            line += String::utf8("  進行: ") + fmt_action(og->action, action_lib_)
                  + " " + String::num_int64(og->progress) + "/" + String::num_int64(og->action.weight)
                  + String::utf8(" (rem ") + String::num_int64(og->remaining_ticks) + ")";
        line += String::utf8("  效果: ") + fmt_effects_of(reg, e);
        return line;
    };

    if (hero_entity_ != entt::null && reg.valid(hero_entity_))
        out += dump_actor(hero_entity_) + "\n";
    for (auto e : reg.view<zone::ActorComponent>()) {
        if (e == hero_entity_) continue;
        out += dump_actor(e) + "\n";
    }
    return out;
}

godot::String zone_gd::ZoneWorld::get_hero_effects() const {
    using godot::String;
    if (hero_entity_ == entt::null) return String("");
    const auto& reg = em_.registry();
    const auto* te = reg.try_get<zone::TimedEffectsComponent>(hero_entity_);
    if (!te || te->effects.empty()) return String("");
    String s;
    for (const auto& ef : te->effects) {
        String n = ef.kind == zone::TimedEffectKind::Burning ? String::utf8("燃燒")
                 : ef.kind == zone::TimedEffectKind::Poison  ? String::utf8("中毒")
                 :                                             String::utf8("回復");
        s += n + String::num_int64(ef.power) + String::utf8("(剩")
           + String::num_int64(ef.turns_left) + String::utf8(") ");
    }
    return s;
}

void zone_gd::ZoneWorld::drain_events() {
    using EK = zone::EventKind;
    bool reached_stair = false;
    for (auto& ev : events_) {
        switch (ev.kind) {
            case EK::BumpedWall:
                if (ev.a == hero_entity_) emit_signal("hero_bumped_wall");
                break;
            case EK::BumpedActor:
                if (ev.a == hero_entity_) emit_signal("hero_bumped_npc", String("npc"));
                break;
            case EK::ActorDied:
                emit_signal("npc_died", String("npc"));
                break;
            case EK::ItemPickedUp:
                if (ev.a == hero_entity_)
                    emit_signal("item_picked_up", String("health_potion"), ev.amount);
                break;
            case EK::ReachedStairDown:
                if (ev.a == hero_entity_) reached_stair = true;
                break;
        }
    }
    events_.clear();
    recompute_fov();

    if (hero_entity_ != entt::null) {
        if (const auto* hp = em_.registry().try_get<zone::HealthComponent>(hero_entity_))
            if (hp->hp <= 0 && !game_over_) { game_over_ = true; emit_signal("game_over"); }
    }

    if (reached_stair) { next_floor(); return; }

    emit_signal("world_changed");  // turn_count 由 submit_* 計（每個玩家指令一回合）
}
