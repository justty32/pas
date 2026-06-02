#pragma once
#include <godot_cpp/classes/node.hpp>
#include <godot_cpp/classes/image.hpp>
#include <godot_cpp/core/class_db.hpp>

#include "core/ecs/entity_manager.h"
#include "core/services/service_context.h"

#include <entt/entt.hpp>

namespace opennefia_gd {

// OpenNefiaWorld — 持有核心模擬狀態的 Node（仿 core_data_layer_design.md §4 慣例二）。
//
// 設計原則：
// - 繼承 Node（有場景樹生命週期）；GDScript 把它加入場景樹，_ready 時建好測試世界。
// - EntityManager + ServiceContext 是成員，跟隨 Node 生命週期。
// - GDScript 透過 move/wait_turn 提交動作，核心處理後 emit world_changed 通知刷新。
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

    // 生成色彩地圖圖片（floor / wall / hero 三色；給 Sprite2D 用）
    // cell_px：每格像素大小（建議 8–16）
    godot::Ref<godot::Image> generate_map_image(int cell_px) const;

    // ---- 動作介面（F3）----
    // 嘗試移動 hero (dx, dy)；成功回傳 true，並 emit world_changed。
    bool move(int dx, int dy);
    // 原地等待一回合；永遠成功，emit world_changed。
    void wait_turn();

    // ---- 狀態查詢（供 UI Label 顯示）----
    int get_hero_x()     const;
    int get_hero_y()     const;
    int get_turn_count() const;

private:
    void setup_test_world();

    opennefia::EntityManager em_;
    opennefia::ServiceContext svc_;

    entt::entity map_entity_{ entt::null };
    entt::entity hero_entity_{ entt::null };
    int turn_count_{ 0 };
};

} // namespace opennefia_gd
