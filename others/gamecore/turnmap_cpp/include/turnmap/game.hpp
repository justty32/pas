#ifndef TURNMAP_GAME_HPP
#define TURNMAP_GAME_HPP

#include <vector>

#include "turnmap/entity.hpp"
#include "turnmap/tilemap.hpp"

namespace turnmap {

// 主控整局遊戲：持有地圖與所有單位，並驅動回合迴圈。
class Game {
public:
    Game(TileMap map, std::vector<Entity> entities);

    // 主迴圈：一直執行直到玩家獲勝、被擊倒或主動退出。
    void run();

private:
    // ── 一個完整回合 (round) 的三個階段 —— 這就是「回合制」的骨架 ──
    void render() const;       // 1. 畫出目前狀態
    bool handlePlayerTurn();   // 2. 等待玩家輸入並結算（回傳 false 代表退出）
    void handleEnemyTurns();   // 3. 所有敵人依序各行動一次

    // 嘗試讓某單位往 (dx,dy) 行動：可能是移動、攻擊，或無效（撞牆/擋路）。
    // 回傳 true 表示這個單位「確實用掉了一次行動」。
    bool tryAct(Entity& actor, int dx, int dy);

    // ── 工具函式 ──
    Entity* playerPtr();              // 取得活著的玩家（無則 nullptr）
    Entity* entityAt(int x, int y);   // 找出站在某格的「活著的」單位
    void checkEndConditions();        // 檢查玩家是否陣亡

    TileMap             map_;
    std::vector<Entity> entities_;
    int                 turn_ = 1;
    bool                running_ = true;
    const char*         message_ = "";  // 結束時顯示給玩家的提示
};

} // namespace turnmap

#endif // TURNMAP_GAME_HPP
