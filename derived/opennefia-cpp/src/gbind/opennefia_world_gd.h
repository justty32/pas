#pragma once
#include <godot_cpp/classes/node.hpp>
#include <godot_cpp/classes/image.hpp>
#include <godot_cpp/core/class_db.hpp>

#include "core/ecs/entity_manager.h"
#include "core/ecs/event_bus.h"
#include "core/ecs/system_ctx.h"
#include "core/services/service_context.h"
#include "core/prototypes/prototype_manager.h"

#include <entt/entt.hpp>

namespace opennefia_gd {

// OpenNefiaWorld — 持有核心模擬狀態的 Node。
//
// F1/F2：地圖查詢 + Image 渲染（FOV 版：三層霧中戰爭）。
// F3：move/wait_turn + world_changed signal。
// NPC AI：EntityManager 帶 npc_ai_system；每次玩家動作後推進一個 tick。
// 碰撞信號：hero_bumped_wall / hero_bumped_npc(npc_id)。
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

    // 生成 FOV 色彩地圖圖片（未探索=黑、探索未見=暗、可見=原色）
    godot::Ref<godot::Image> generate_map_image(int cell_px) const;

    // ---- 動作介面 ----
    // move：若碰牆→emit hero_bumped_wall 回傳 false；碰 NPC→emit hero_bumped_npc 並推進回合；否則正常移動
    bool move(int dx, int dy);
    void wait_turn();

    // ---- 狀態查詢 ----
    int get_hero_x()      const;
    int get_hero_y()      const;
    int get_turn_count()  const;
    int get_hero_hp()     const;
    int get_hero_max_hp() const;
    int get_npc_count()   const;

    int  get_current_floor() const;
    void restart();        // 完整重置（英雄重建，回到 1 層）

    // ---- 存讀檔 ----
    bool save_game(const godot::String& path);         // 序列化 registry → 二進位檔
    bool load_game(const godot::String& path);         // 反序列化並重建 C++ 指標
    bool has_save_game(const godot::String& path) const; // 存檔是否存在

private:
    void init_cvars();       // 登錄遊戲設計參數 CVar（只跑一次）
    void init_prototypes();  // 登錄 ComponentLoader + 載入 game_prototypes.yaml（只跑一次）
    void setup_test_world();
    void setup_map();        // 生成新地圖 + 放置英雄/NPC/樓梯（可重複呼叫）
    void next_floor();       // 下一層：銷毀舊地圖+NPC，重新生成，英雄保留 HP
    void advance_turn();     // tick EntityManager（NPC AI 等系統）並 emit world_changed
    void recompute_fov();    // 從英雄位置重算視野

    opennefia::EntityManager    em_;
    opennefia::EventBus         bus_;
    opennefia::ServiceContext   svc_;
    opennefia::PrototypeManager pm_;
    bool pm_ready_{ false };

    entt::entity map_entity_{ entt::null };
    entt::entity hero_entity_{ entt::null };
    int turn_count_{ 0 };
    bool game_over_{ false };
    int  current_floor_{ 1 };
    bool systems_ready_{ false };  // 防止 add_system 重複呼叫
};

} // namespace opennefia_gd
