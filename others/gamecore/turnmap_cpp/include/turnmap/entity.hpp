#ifndef TURNMAP_ENTITY_HPP
#define TURNMAP_ENTITY_HPP

#include <string>

namespace turnmap {

// 陣營：用來區分玩家與敵人，決定行動方式與互動（攻擊/擋路）。
enum class Team { Player, Enemy };

// 地圖上的一個單位 (unit / actor)。
// 注意：單位的「位置」與「地形」是分開的兩層資料 ——
// 地形存在 TileMap 裡，單位另外用一個清單管理，渲染時再疊在地形之上。
struct Entity {
    std::string name;
    char  glyph;        // 顯示字元，例如 '@'(玩家) 或 'g'(哥布林)
    int   x, y;         // 所在格座標
    int   hp;           // 生命值，<= 0 視為死亡
    int   attack;       // 每次攻擊造成的傷害
    Team  team;
    bool  alive = true;
};

} // namespace turnmap

#endif // TURNMAP_ENTITY_HPP
