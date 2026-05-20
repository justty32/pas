#include "turnmap/game.hpp"

#include <iostream>
#include <string>
#include <utility>   // std::move
#include <vector>

#include "turnmap/pathfinding.hpp"

namespace turnmap {

Game::Game(TileMap map, std::vector<Entity> entities)
    : map_(std::move(map)), entities_(std::move(entities)) {}

Entity* Game::playerPtr() {
    for (auto& e : entities_) {
        if (e.team == Team::Player && e.alive) return &e;
    }
    return nullptr;
}

Entity* Game::entityAt(int x, int y) {
    for (auto& e : entities_) {
        if (e.alive && e.x == x && e.y == y) return &e;
    }
    return nullptr;
}

void Game::render() const {
    std::cout << "\n=== 回合 " << turn_ << " ===\n";

    // 分層渲染：先取地形字元，若該格上站著單位就用單位字元蓋過去。
    // 「地形層 + 單位層」是 tilemap 最基本的繪製模型。
    for (int y = 0; y < map_.height(); ++y) {
        std::string line;
        for (int x = 0; x < map_.width(); ++x) {
            char ch = tileGlyph(map_.at(x, y));
            for (const auto& e : entities_) {
                if (e.alive && e.x == x && e.y == y) {
                    ch = e.glyph;
                    break;
                }
            }
            line.push_back(ch);
        }
        std::cout << "  " << line << '\n';
    }

    // 狀態列：玩家 HP 與場上敵人數。
    int enemies = 0;
    for (const auto& e : entities_) {
        if (e.team == Team::Player && e.alive) {
            std::cout << "  HP: " << e.hp << "   ";
        }
        if (e.team == Team::Enemy && e.alive) {
            ++enemies;
        }
    }
    std::cout << "敵人: " << enemies << '\n';
    std::cout << "  圖例: @ 你   g 哥布林   # 牆   ~ 水   > 出口\n";
}

bool Game::handlePlayerTurn() {
    Entity* player = playerPtr();
    if (!player) return false;

    // 回合制的特性：遊戲在這裡「停下來」等玩家輸入，
    // 不像即時遊戲那樣靠時間持續推進。
    // 撞牆或按錯鍵都不耗回合，會留在這個迴圈重新輸入。
    while (true) {
        std::cout << "\n你的行動 [w/a/s/d 移動, q 離開] > " << std::flush;

        std::string input;
        if (!std::getline(std::cin, input) || (!input.empty() && (input[0] == 'q' || input[0] == 'Q'))) {
            running_  = false;
            message_  = "你選擇離開了地下城。";
            return false;
        }
        if (input.empty()) continue;

        int dx = 0, dy = 0;
        switch (input[0]) {
            case 'w': case 'W': dy = -1; break;
            case 's': case 'S': dy =  1; break;
            case 'a': case 'A': dx = -1; break;
            case 'd': case 'D': dx =  1; break;
            default:
                std::cout << "  ? 無效的按鍵，請用 w/a/s/d。\n";
                continue;
        }

        // tryAct 回傳 true = 用掉一次行動 → 換敵人行動。
        // 回傳 false（撞牆/被擋）→ 不耗回合，重新輸入。
        if (tryAct(*player, dx, dy)) return true;
    }
}

void Game::handleEnemyTurns() {
    Entity* player = playerPtr();
    if (!player || !running_) return;  // 玩家已獲勝或退出，敵人不再行動

    for (auto& e : entities_) {
        if (!e.alive || e.team != Team::Enemy) continue;

        // 回合制 AI：用 A* 規劃一條到玩家的最短路徑（會繞過牆與水），
        // 然後只踏出第一步。每回合都重新規劃，所以玩家移動後敵人會即時修正路線。
        const std::vector<Vec2> path = findPath(map_, { e.x, e.y }, { player->x, player->y });
        if (path.empty()) continue;  // 被牆完全隔開、無路可走 → 原地不動

        // path.front() 是下一步要踏上的相鄰格。走到玩家所在格時，
        // tryAct 會判定為敵對單位而自動發動攻擊（bump-to-attack）。
        const Vec2 next = path.front();
        tryAct(e, next.x - e.x, next.y - e.y);
    }
}

bool Game::tryAct(Entity& actor, int dx, int dy) {
    const int nx = actor.x + dx;
    const int ny = actor.y + dy;

    // 1. 邊界與地形：撞到牆、水或地圖外 → 行動無效。
    if (!map_.isWalkable(nx, ny)) {
        if (actor.team == Team::Player) {
            std::cout << "  ! 那個方向走不過去。\n";
        }
        return false;
    }

    // 2. 目標格若已有「另一個」活著的單位：
    Entity* target = entityAt(nx, ny);
    if (target && target != &actor) {
        if (target->team != actor.team) {
            // 不同陣營 → 攻擊（bump-to-attack，回合制最常見的近戰模型）。
            target->hp -= actor.attack;
            std::cout << "  * " << actor.name << " 攻擊 " << target->name
                      << "，造成 " << actor.attack << " 點傷害";
            if (target->hp <= 0) {
                target->alive = false;
                std::cout << "，" << target->name << " 倒下了！";
            }
            std::cout << " (剩餘 HP " << (target->hp > 0 ? target->hp : 0) << ")\n";
            return true;  // 攻擊也算用掉一次行動
        }
        return false;     // 同陣營擋路 → 無效
    }

    // 3. 沒有阻擋 → 移動。若玩家踩到出口即獲勝。
    actor.x = nx;
    actor.y = ny;
    if (actor.team == Team::Player && map_.at(nx, ny) == TileType::Exit) {
        message_  = "你找到了出口，成功逃脫！";
        running_  = false;
    }
    return true;
}

void Game::checkEndConditions() {
    Entity* player = playerPtr();
    if (!player) {  // playerPtr 只回傳「活著的」玩家，找不到代表已陣亡
        message_  = "你被擊倒了…… 遊戲結束。";
        running_  = false;
    }
}

void Game::run() {
    std::cout << "歡迎來到回合制 tilemap 示範！\n"
                 "目標：避開或擊敗哥布林 (g)，走到出口 (>) 即可逃脫。\n";

    while (running_) {
        render();
        if (!handlePlayerTurn()) break;  // 玩家退出
        handleEnemyTurns();              // 敵人可能在這裡擊倒玩家
        ++turn_;
        checkEndConditions();
    }

    render();  // 顯示最終盤面
    std::cout << "\n" << message_ << "\n";
}

} // namespace turnmap
