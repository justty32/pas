// =============================================================================
// 回合迴圈設計草稿 (conceptual sketch — 非可編譯實作)
//
// 目的：把 §7 討論出的模型寫成 code，給使用者對照「是否與設想對得上」。
// 故意省略 include / 命名空間 / 錯誤處理；型別如 Snapshot、Action 只給骨架。
//
// 五條已定案決策（對照設計文件 §7「決策定案」）：
//   1. 玩家恆先手
//   2. 顯示分塊 display_chunk 動態可調
//   3. dt 由 C++ 算，Godot 不傳
//   4. 狀態全在 C++（OngoingActionComponent）
//   5. 阻塞 = snapshot.hero.idle（C++ 不 spin）
// =============================================================================

using PassTime = double;   // TBD：浮點秒 / 整數毫秒 / 分數回合，先用 double 示意


// ---------------------------------------------------------------------------
// 行動 (Action)
// ---------------------------------------------------------------------------
enum class ActionKind {
    Idle,      // 待命：玩家行動結算後的狀態 = 世界阻塞訊號
    Attack,    // 0.5t 基本動作
    Defend,    // 0.5t 基本動作（常用於打斷）
    Cast,      // 多回合（如火球 3t）
    Move,      // 移動
};
// 注意：沒有「繼續」這個 Action。「繼續」= step() 不帶 cmd、不覆寫進行中行動，
//       純粹是「沒有新指令」這件事本身，不是一個會被塞進 OngoingAction 的行動。

struct Action {
    ActionKind kind     = ActionKind::Idle;
    PassTime   duration = 0;   // 此行動總時長（攻擊 0.5 / 詠唱 3 ...）
    int        param    = 0;   // 目標 entity / 法術 id 等，骨架先用一個 int 佔位

    static Action idle() { return Action{ ActionKind::Idle, 0, 0 }; }
};


// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------
struct ActorComponent {};   // 空 tag：有行動資格（玩家 + NPC 都掛）
struct HeroComponent  {};   // 空 tag：此 actor 的「下一個行動」由外部(Godot)供給，而非 AI

// 進行中行動：玩家與 NPC 共用同一個 component（對稱的關鍵）
struct OngoingActionComponent {
    Action   action    = Action::idle();
    PassTime remaining = 0;   // 剩餘時間；tick 遞減，歸零 = 結算
};


// ---------------------------------------------------------------------------
// 「下一個行動從哪來」—— 這是玩家 vs NPC 唯一的差別
// ---------------------------------------------------------------------------
std::optional<Action> provide_next_action(entt::registry& reg, entt::entity e) {
    if (reg.all_of<HeroComponent>(e))
        return std::nullopt;            // ★ 玩家：不自挑，進入 idle，等 Godot 下個 step 餵指令
    return npc_ai_decide(reg, e);       // ★ NPC：AI 自己挑下一個（自走）
}


// ---------------------------------------------------------------------------
// 共用 tick：推進「單一 actor」消化 dt
//   玩家與 NPC 跑的是同一份程式碼，沒有任何「玩家特判」。
//   差別只在迴圈尾端呼叫的 provide_next_action()。
// ---------------------------------------------------------------------------
void tick_actor(entt::registry& reg, entt::entity e, PassTime dt) {
    auto& og = reg.get<OngoingActionComponent>(e);
    PassTime left = dt;

    while (left > 0) {
        if (og.action.kind == ActionKind::Idle)
            break;                              // 待命中，沒東西好消耗（玩家 idle / NPC 無事）

        PassTime spend = std::min(left, og.remaining);
        apply_channel_effect(reg, e, og.action, spend);  // 逐 tick 效果（如持續詠唱動畫/讀條），選用
        og.remaining -= spend;
        left          -= spend;

        if (og.remaining <= 0) {
            resolve_action_effect(reg, e, og.action);     // 結算效果（攻擊命中 / 火球爆炸 / 防禦成立）

            // 行動結算 → 取下一個行動
            auto next = provide_next_action(reg, e);
            if (next) {
                og.action    = *next;                      // NPC：接著做，可能在同一個 dt 內繼續消耗
                og.remaining = next->duration;
            } else {
                og.action    = Action::idle();             // 玩家：轉 idle，停止消耗
                og.remaining = 0;
                break;
            }
        }
    }
}
// 註：因為 step() 算 dt 時用 min(hero 行動剩餘, chunk)，dt 永遠 ≤ hero 行動剩餘，
//     所以 hero 不會「dt 沒用完就 idle 還剩一截 dt」。NPC 才需要 while 迴圈把 dt 跑滿
//     （NPC 行動較短時，單次 step 內可能結算 A → 自挑 B → 繼續消耗剩下的 dt）。


// ---------------------------------------------------------------------------
// ZoneWorld：GDExtension 主類別（Node）
// ---------------------------------------------------------------------------
class ZoneWorld /* : public godot::Node */ {
public:
    // === Godot 端唯一會呼叫的兩個入口 ===
    Snapshot step()                    { return advance(std::nullopt); }  // 繼續（玩家無新輸入）
    Snapshot step(PlayerCommand cmd)   { return advance(cmd);          }  // 換行動 / 打斷

    // 顯示分塊：Godot 隨時可調的旋鈕（步調 / UI 訴求）
    void set_display_chunk(PassTime dt) { display_chunk_ = dt; }

private:
    Snapshot advance(std::optional<PlayerCommand> cmd) {
        auto& reg = em_.registry();

        // (1) 有新指令就覆寫 hero 的進行中行動 = 換行動 / 打斷（詠唱剩餘自然被丟棄）
        if (cmd) {
            auto& og   = reg.get<OngoingActionComponent>(hero_);
            og.action    = to_action(*cmd);
            og.remaining = og.action.duration;
        }

        // (2) C++ 自己算 dt：行動剩餘 與 顯示分塊 取小
        PassTime dt = compute_dt();

        // (3) 玩家恆先手：先結算 hero，再迭代「排除 hero」的 view
        tick_actor(reg, hero_, dt);
        for (auto e : reg.view<ActorComponent>(entt::exclude<HeroComponent>))
            tick_actor(reg, e, dt);

        // (4) 推進世界時鐘，回傳快照
        clock_ += dt;
        return snapshot();
    }

    PassTime compute_dt() {
        auto& og = em_.registry().get<OngoingActionComponent>(hero_);
        if (og.action.kind == ActionKind::Idle)
            return 0;                                   // 防禦性：hero idle 時不該被呼叫 step()
        return std::min(og.remaining, display_chunk_);  // ★ dt = min(行動剩餘, 顯示分塊)
    }

    Snapshot snapshot() {
        Snapshot s;
        auto& og = em_.registry().get<OngoingActionComponent>(hero_);
        s.hero.idle               = (og.action.kind == ActionKind::Idle);  // ★ 阻塞訊號
        s.hero.ongoing_remaining  = og.remaining;
        // ... 填入地圖、各 actor 位置 / 血量等供 Godot 渲染
        return s;
    }

    zone::EntityManager em_;
    entt::entity        hero_         = entt::null;
    PassTime            clock_        = 0;
    PassTime            display_chunk_ = 1.0;   // 預設一回合；戰鬥調小、趕路調大(甚至 ∞)
};


// =============================================================================
// Godot 端（GDScript 偽碼）：顯示 + 輸入，由 hero.idle 決定要不要自動續推
// =============================================================================
//
//   var last_snapshot: Snapshot
//
//   func _process(_delta):
//       render(last_snapshot)                       # 純顯示，不碰 C++
//
//   func _input(event):
//       var cmd = build_cmd(event)                  # 玩家任意時刻輸入
//       if cmd:
//           last_snapshot = zone_world.step(cmd)    # 換行動 / 打斷，立即觸發
//           render(last_snapshot)
//
//   func _on_tick():                                # 計時器或每幀檢查
//       if not last_snapshot.hero.idle:             # ★ 多回合行動進行中才自動續推
//           last_snapshot = zone_world.step()       # 「繼續」
//           render(last_snapshot)
//       # idle 時什麼都不做 = 世界阻塞，等玩家輸入
//
// =============================================================================
