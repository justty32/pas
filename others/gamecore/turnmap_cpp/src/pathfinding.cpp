#include "turnmap/pathfinding.hpp"

#include <algorithm>  // std::reverse
#include <cstdlib>    // std::abs
#include <limits>
#include <queue>

// ───────────────────────────────────────────────────────────────────────────
// A* 尋路演算法總覽
// ───────────────────────────────────────────────────────────────────────────
// A* 是「在圖上找最短路」的演算法，可看成加了方向感的 Dijkstra。
// 它替每個格子估一個分數 f，每次都優先展開 f 最小的格子：
//
//     f(n) = g(n) + h(n)
//
//   g(n)：從起點走到 n「已知的實際成本」（這裡每走一步 = 1）。
//   h(n)：從 n 到終點的「估計成本」(heuristic)。只要 h 不高估真實成本
//         （稱為 admissible），A* 就保證找到最短路徑。
//
// 用到的三個對照表（都以格子的一維 index 當索引）：
//   gScore[i]   ── 起點到格子 i 目前找到的最短成本，初值無限大。
//   cameFrom[i] ── 在最佳路徑上，格子 i 的「前一格」index，用來最後回溯路徑。
//   closed[i]   ── 該格是否已「定案」（取出並展開過），定案後不再處理。
//
// open set（待展開的格子）用 std::priority_queue 當最小堆，依 f 由小到大取出。
// ───────────────────────────────────────────────────────────────────────────

namespace turnmap {

namespace {

// heuristic h(n)：到 goal 的 Manhattan 距離（|dx| + |dy|）。
// 在「四方向移動 + 每步成本 1」的方格上，這個值永遠 ≤ 真實步數，
// 不會高估，因此 admissible，A* 得到的路徑保證最短。
int manhattan(Vec2 a, Vec2 b) {
    return std::abs(a.x - b.x) + std::abs(a.y - b.y);
}

} // namespace

std::vector<Vec2> findPath(const TileMap& map, Vec2 start, Vec2 goal) {
    const int W = map.width();
    const int H = map.height();

    // 起點或終點落在地圖外就不可能有路，直接回空。
    if (!map.inBounds(start.x, start.y) || !map.inBounds(goal.x, goal.y)) {
        return {};
    }

    // 把二維座標 (x, y) 壓成一維 index（row-major），方便當陣列索引。
    auto index = [W](int x, int y) { return y * W + x; };

    // open set 的元素：記下格子座標與它的 f 值。
    // priority_queue 預設是「最大堆」，所以 Cmp 故意反過來比 (a.f > b.f)，
    // 讓它變成「最小堆」——每次 top() 取到的是 f 最小的格子。
    struct Node { int f; int x; int y; };
    struct Cmp { bool operator()(const Node& a, const Node& b) const { return a.f > b.f; } };
    std::priority_queue<Node, std::vector<Node>, Cmp> open;

    // 三個對照表，大小都是 W*H。gScore 初值設成「無限大」代表尚未抵達。
    constexpr int kInf = std::numeric_limits<int>::max();
    std::vector<int>  gScore(static_cast<size_t>(W) * H, kInf);  // 起點到該格的實際成本
    std::vector<int>  cameFrom(static_cast<size_t>(W) * H, -1);  // 前驅格 index，-1 = 無
    std::vector<char> closed(static_cast<size_t>(W) * H, 0);     // 已定案的格子

    // 起點：實際成本 0，估計成本 = h(start)，丟進 open set 當第一個展開對象。
    gScore[index(start.x, start.y)] = 0;
    open.push({ manhattan(start, goal), start.x, start.y });

    // 四個移動方向：上、下、左、右（正交移動，符合方格地圖）。
    constexpr int dirs[4][2] = { {0, -1}, {0, 1}, {-1, 0}, {1, 0} };

    // ── 主迴圈：不斷取出 f 最小的格子來展開，直到抵達終點或 open set 清空 ──
    while (!open.empty()) {
        const Node cur = open.top();  // 目前 f 最小的格子
        open.pop();
        const int ci = index(cur.x, cur.y);

        // 「惰性刪除」：同一格可能因為被多次鬆弛而在堆裡留下好幾份副本。
        // 我們不去堆裡刪舊的，而是在取出時檢查──若這格早已定案，這份就是
        // 過期副本，直接略過。這是用 priority_queue 實作 A* 的常見技巧。
        if (closed[ci]) continue;
        closed[ci] = 1;  // 標記定案：它的 gScore 已是最終最短值，不會再更短

        // 取出的就是終點 → 最短路已確定，結束搜尋。
        if (cur.x == goal.x && cur.y == goal.y) break;

        // 展開四個鄰格，嘗試「鬆弛」(relax) 經由 cur 抵達它們的成本。
        for (const auto& d : dirs) {
            const int nx = cur.x + d[0];
            const int ny = cur.y + d[1];
            if (!map.inBounds(nx, ny)) continue;  // 出界

            // 鄰格必須可走才能踏入；唯一例外是「終點」——
            // 即使終點被單位佔據（不可走），也允許當作路徑終點，
            // 這樣敵人才能把玩家所在的格子設成目標、走到旁邊就攻擊。
            const bool isGoal = (nx == goal.x && ny == goal.y);
            if (!isGoal && !map.isWalkable(nx, ny)) continue;

            const int ni = index(nx, ny);
            if (closed[ni]) continue;  // 已定案的鄰格不必再看

            // 經由 cur 走到這個鄰格的成本（cur 的成本 + 一步）。
            const int tentative = gScore[ci] + 1;

            // 若這條路比先前找到的更短，就更新它，並把新的 f 丟進 open set。
            if (tentative < gScore[ni]) {
                gScore[ni]   = tentative;            // 記下更短的實際成本
                cameFrom[ni] = ci;                   // 記下「從哪一格過來」
                open.push({ tentative + manhattan({nx, ny}, goal), nx, ny });
            }
        }
    }

    // 迴圈結束後若終點的 gScore 仍是無限大，代表被牆完全隔開、無路可達。
    const int goalIdx = index(goal.x, goal.y);
    if (gScore[goalIdx] == kInf) return {};

    // ── 回溯路徑 ──
    // 沿著 cameFrom 從「終點」一路往回跳到「起點」，會得到反向的路徑；
    // 收集途中每一格（不含起點），最後 reverse 成 start → goal 的正向順序。
    std::vector<Vec2> path;
    const int startIdx = index(start.x, start.y);
    for (int ci = goalIdx; ci != startIdx && ci != -1; ci = cameFrom[ci]) {
        path.push_back({ ci % W, ci / W });  // 一維 index 還原回 (x, y)
    }
    std::reverse(path.begin(), path.end());
    return path;
}

} // namespace turnmap
