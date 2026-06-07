#pragma once
#include <godot_cpp/classes/node.hpp>
#include <godot_cpp/classes/image.hpp>
#include <godot_cpp/core/class_db.hpp>

#include "core/ecs/entity_manager.h"
#include "core/ecs/system_ctx.h"
#include "core/turn/turn_scheduler.h"
#include "core/turn/turn_world.h"
#include "core/turn/zone_effects.h"
#include "core/turn/zone_event.h"
#include "core/turn/action_def.h"

#include <entt/entt.hpp>
#include <memory>
#include <random>
#include <vector>
#include <string>

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

    // ---- 動作介面（既有同步路徑）----
    bool move(int dx, int dy);
    void wait_turn();

    // ---- 排程器路徑（可切換 A/B/C；計時器驅動）----
    void set_scheduler_mode(int mode);   // 0=EnergyInstant 1=EnergyChannel 2=TickRemaining
    int  get_scheduler_mode() const;
    void submit_hero_move(int dx, int dy);
    void submit_hero_wait();
    void submit_hero_cast(int turns);                  // 多回合詠唱（channel，可被打斷）
    void submit_hero_skill(const godot::String& name); // 資料驅動技能（JSON 定義）
    bool step_scheduler();               // 推進一步；排出事件→signal；回傳「英雄正等指令」
    bool hero_is_waiting() const;        // 排程器目前卡在英雄

    // ---- UI 查詢 ----
    godot::String get_hero_status() const;   // 詠唱 N/M / 待命 / 行動中
    godot::String get_hero_effects() const;  // 持續效果摘要（燃燒/中毒/回復）
    godot::String get_debug_text() const;    // 詳細診斷 dump：世界 + 逐 actor 全狀態
    int get_world_clock() const;             // 已過 ticks（累計）

    // ---- debug 追蹤（逐步 print）----
    void set_trace_enabled(bool on);
    bool get_trace_enabled() const;
    godot::String get_debug_log() const;     // 最近數十行 trace（給螢幕用）
    void clear_debug_log();

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

    // ---- 排程器路徑內部 ----
    void           setup_scheduler();
    zone::TurnWorld make_turn_world();
    void           drain_events();
    void           bump_turn_count();
    void           on_trace(const std::string& line);
    zone::Action   npc_decide(entt::registry&, entt::entity);

    zone::EntityManager em_;
    zone::SystemCtx     ctx_;

    std::unique_ptr<zone::TurnScheduler> scheduler_;
    int                    scheduler_mode_{ 1 };  // 預設 EnergyChannel
    zone::EffectRegistry   effects_;
    zone::MoveEffects      move_fx_;
    zone::WaitEffects      wait_fx_;
    zone::CastEffects      cast_fx_;
    zone::LibraryEffects   lib_fx_;
    zone::ActionLibrary    action_lib_;
    std::vector<zone::ZoneEvent> events_;
    std::mt19937           turn_rng_{ 0xC0FFEE };
    long long              world_clock_{ 0 };   // 累計 ticks（跨 step）
    bool                   trace_enabled_{ true };  // 預設開（詳細 debug）
    std::vector<std::string> trace_log_;            // 最近 trace 行（ring）

    entt::entity map_entity_{ entt::null };
    entt::entity hero_entity_{ entt::null };
    int turn_count_{ 0 };
    bool game_over_{ false };
    int  current_floor_{ 1 };
    bool systems_ready_{ false };
};

} // namespace zone_gd
