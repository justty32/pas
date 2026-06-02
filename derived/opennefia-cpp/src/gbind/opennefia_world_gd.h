#pragma once
#include <godot_cpp/classes/node.hpp>
#include <godot_cpp/classes/image.hpp>
#include <godot_cpp/core/class_db.hpp>

#include "core/ecs/entity_manager.h"
#include "core/ecs/event_bus.h"
#include "core/ecs/system_ctx.h"
#include "core/services/service_context.h"

#include <entt/entt.hpp>

namespace opennefia_gd {

// OpenNefiaWorld — 持有核心模擬狀態的 Node。
//
// F1/F2：地圖查詢 + Image 渲染。
// F3：move/wait_turn + world_changed signal。
// NPC AI：EntityManager 帶 npc_ai_system；每次玩家動作後推進一個 tick。
class OpenNefiaWorld : public godot::Node {
    GDCLASS(OpenNefiaWorld, godot::Node)

protected:
    static void _bind_methods();

public:
    OpenNefiaWorld();
    ~OpenNefiaWorld() override = default;

    void _ready() override;

    // ---- 地圖查詢 ----
    int  get_map_width()  const;
    int  get_map_height() const;
    bool is_walkable(int x, int y) const;

    // 生成色彩地圖圖片（floor / wall / hero=黃 / NPC=紅）
    godot::Ref<godot::Image> generate_map_image(int cell_px) const;

    // ---- 動作介面 ----
    bool move(int dx, int dy);    // 移動 hero → tick NPC AI → emit world_changed
    void wait_turn();             // 等待 → tick NPC AI → emit world_changed

    // ---- 狀態查詢 ----
    int get_hero_x()     const;
    int get_hero_y()     const;
    int get_turn_count() const;

private:
    void setup_test_world();
    void advance_turn();          // tick EntityManager（NPC AI 等系統）

    opennefia::EntityManager  em_;
    opennefia::EventBus       bus_;
    opennefia::ServiceContext svc_;

    entt::entity map_entity_{ entt::null };
    entt::entity hero_entity_{ entt::null };
    int turn_count_{ 0 };
};

} // namespace opennefia_gd
