#include <utility>
#include <vector>

#include "turnmap/game.hpp"

using namespace turnmap;

int main() {
    // 用 ASCII 手繪一張小地圖（# 牆, . 地板, ~ 水, > 出口）。
    // 字元 '@' / 'g' 只是視覺標記實際出生位置，會被當成地板，
    // 真正的單位在下方的 entities 清單裡定義。
    TileMap map = TileMap::fromAscii({
        "############",
        "#@...#....>#",
        "#....#.###.#",
        "#.##...#...#",
        "#.#..g.#.#.#",
        "#.#.##.#.#.#",
        "#...~~...#.#",
        "############",
    });

    std::vector<Entity> entities = {
        // name,        glyph, x,  y, hp, atk, team
        { "你",          '@',  1,  1, 20,  5, Team::Player },
        { "哥布林",      'g',  5,  4,  8,  3, Team::Enemy  },
    };

    Game game(std::move(map), std::move(entities));
    game.run();
    return 0;
}
