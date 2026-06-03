#pragma once
#include <godot_cpp/classes/node.hpp>
#include <godot_cpp/classes/image.hpp>
#include <godot_cpp/core/class_db.hpp>

#include "core/ecs/entity_manager.h"
#include "core/ecs/system_ctx.h"

#include <entt/entt.hpp>

namespace zone_gd {

// ZoneWorld — gamecore 區域層（Area Layer）的核心 Node。
// 回合制 Actor poll 模式：advance_turn() 輪詢所有 ActorComponent 實體。
class ZoneWorld : public godot::Node {
    GDCLASS(ZoneWorld, godot::Node)

protected:
    static void _bind_methods();

public:
    ZoneWorld();
    ~ZoneWorld() override = default;

    void _ready() override;

    // ---- 地圖查詢 ----
    int  get_map_width()  const;
    int  get_map_height() const;
    bool is_walkable(int x, int y) const;
    godot::Ref<godot::Image> generate_map_image(int cell_px) const;

    // ---- 動作介面 ----
    bool move(int dx, int dy);
    void wait_turn();

    // ---- 狀態查詢 ----
    int get_hero_x()      const;
    int get_hero_y()      const;
    int get_turn_count()  const;
    int get_hero_hp()     const;
    int get_hero_max_hp() const;
    int get_npc_count()   const;
    int get_current_floor() const;
    void restart();

    // ---- 存讀檔 ----
    bool save_game(const godot::String& path);
    bool load_game(const godot::String& path);
    bool has_save_game(const godot::String& path) const;

private:
    void setup_world();
    void setup_map();
    void next_floor();
    void advance_turn();   // actor poll entry point
    void recompute_fov();

    zone::EntityManager em_;
    zone::SystemCtx     ctx_;

    entt::entity map_entity_{ entt::null };
    entt::entity hero_entity_{ entt::null };
    int turn_count_{ 0 };
    bool game_over_{ false };
    int  current_floor_{ 1 };
    bool systems_ready_{ false };
};

} // namespace zone_gd
