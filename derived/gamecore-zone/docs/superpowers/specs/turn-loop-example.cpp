// =============================================================================
// 回合迴圈 example —— order 表模型（多角色操控版 / conceptual sketch）
//
// 與同目錄 2026-06-03-turn-loop-sketch.cpp（§7 單 hero + 時間 dt 模型）並列。
// 這份走「出手順序表 orders + 可中斷續推」路線，動機：
//   玩家會同時操控多個角色 → 沒有單一 hero → §7「先 tick hero 再 exclude」不適用，
//   且 player_instructions / need_to_wait 本來就是「依 actor index 的 vector」。
//
// 已定案：
//   - action 有 duration、可被打斷（覆寫進行中行動，duration 重設）
//   - 阻塞條件 = 某玩家角色「行動已結算(idle) 且 無新指令」→ 強行停整個迴圈；
//     行動進行中(remaining>0)即使 idle/無指令也不阻塞，只續推一回合
//   - 下令順序「可選」：Initiative（依先攻穿插）/ PlayerFirst（我方全排前段）
//       → core_loop 不變，只有 rebuild_orders() 隨模式不同
//   - 打斷「非即時」：指令只在迴圈掃到該角色的出手格時才讀取生效（最多延遲一輪）
//       → 不需要 §7 那條立即 step(cmd) 路徑
// =============================================================================

#include <algorithm>
#include <vector>
using namespace std;

struct Actor {
  // act(ic) 契約：
  //   ic != 0                        ：以該指令『開始/打斷』新行動（重設 remaining）、清 idle 旗標
  //   ic == 0 且 remaining > 0        ：續推進行中行動（remaining--）
  //   ic == 0 且 remaining == 0       ：NPC → AI 自挑下一個行動；玩家 → 不會走到（進 act 前已被阻塞攔下）
  //   行動於本次結算歸零時             ：把該角色的 need_to_wait_player_ic 設 true
  void act(int ic);
  bool is_player_controlling();
};

enum class OrderMode { Initiative, PlayerFirst };

// --- 世界狀態（示意用全域；實裝接 EntityManager / entt::registry）---
vector<int>   orders;                  // 出手順序（actor index 的排列）
vector<Actor> actors;
vector<int>   player_instructions;     // 每 actor 一格；NPC 恆 0
vector<bool>  need_to_wait_player_ic;  // 每 actor 一格 = 該角色「idle、待新指令」
int           last_actor_order_i = 0;  // 跨呼叫保存的續推游標
int           waiting_actor      = -1; // 迴圈目前卡在哪個 actor（-1 = 沒卡）；給前端聚焦 UI
OrderMode     order_mode = OrderMode::Initiative;  // ★ 可切換的旋鈕

// 每輪起點重建 orders（先攻/速度/生死可能變動）。排序政策唯一分歧處。
void rebuild_orders() {
  build_by_initiative(orders);  // 依先攻/速度填入 actor index（細節略）
  if (order_mode == OrderMode::PlayerFirst) {
    // 我方全部穩定移到前段，兩組內各自維持先攻序
    stable_partition(orders.begin(), orders.end(),
                     [](int a) { return actors[a].is_player_controlling(); });
  }
}

// 一次呼叫推進到「本輪結尾」或「卡在某玩家角色」為止。
// 線性走訪、不環繞 → 任意數量/位置的玩家角色都不會有人在一輪內多走。
void core_loop() {
  if (last_actor_order_i == 0) rebuild_orders();  // 只在輪次起點重建，續推時不動

  while (last_actor_order_i < (int)orders.size()) {
    int now = orders[last_actor_order_i];

    if (actors[now].is_player_controlling()) {
      int ic = player_instructions[now];
      if (ic == 0 && need_to_wait_player_ic[now]) {
        waiting_actor = now;          // 卡在這個角色，等它的指令
        return;                       // 強行阻塞整個迴圈（不前進游標、不歸零）
      }
      actors[now].act(ic);            // ic!=0 開始/打斷；ic==0 續推進行中行動
      if (ic != 0) player_instructions[now] = 0;  // ★ 消費指令，避免下一輪重複打斷
    } else {
      actors[now].act(0);            // NPC：自走
    }
    last_actor_order_i++;
  }

  waiting_actor = -1;
  last_actor_order_i = 0;            // 本輪每角色都動過一次 → 開新一輪（下次進來會 rebuild）
}

// =============================================================================
// 前端：推進與渲染『解耦』，各走各的時鐘
//   - 渲染：每幀畫最新 snapshot，純顯示、不碰 core_loop。
//   - 推進：由『獨立計時器』驅動（如每 1 秒一次），不綁渲染幀——
//           世界步調是玩法節奏（可慢/快/暫停），不該被 FPS 綁定。
//   阻塞由 core_loop 內部自理：卡在玩家時即刻 return，故計時器每次無腦呼叫都安全。
// =============================================================================

// 每渲染幀呼叫：純顯示
void render_frame() {
  // draw(last_snapshot);  // 只畫，不推進
}

// 玩家任意時刻輸入：寫進『正在等待的那個角色』的指令格，下次推進計時器會讀到
void on_input(/* event */) {
  if (waiting_actor >= 0) {
    // player_instructions[waiting_actor] = build_instruction_from_input();
    // highlight(actors[waiting_actor]);
  }
}

// 獨立推進計時器回呼（如每 1 秒）：間隔 = 多回合行動自動結算的速度旋鈕，
// 戰鬥放慢、趕路加快、玩家思考時可暫停此計時器。
void on_advance_timer() {
  core_loop();   // 等指令時自我阻塞（即刻 return）；否則推進到本輪結尾
  // 狀態已變 → 下一個 render_frame 會畫出新 snapshot
}

int main() { return 0; }
