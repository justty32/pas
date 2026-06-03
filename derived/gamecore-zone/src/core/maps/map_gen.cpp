#include "map_gen.h"
#include "tile.h"
#include <algorithm>
#include <memory>
#include <optional>
#include <random>
#include <vector>

namespace zone {
namespace {

constexpr int MIN_SIZE  = 7;
constexpr int ROOM_MIN  = 4;
constexpr int ROOM_PAD  = 2;

struct BspNode {
    int x, y, w, h;
    std::unique_ptr<BspNode> left;
    std::unique_ptr<BspNode> right;
    std::optional<Room> room;
};

// 前向宣告
void split(BspNode& node, std::mt19937& rng);
void carve_rooms(BspNode& node, MapData& map, std::mt19937& rng, std::vector<Room>& rooms);
void connect_rooms(BspNode& node, MapData& map);
const Room* get_room_from(const BspNode& node);

// ── 工具函式 ──────────────────────────────────────────────────

void set_floor(MapData& map, int x, int y) {
    if (!map.in_bounds(x, y)) return;
    auto& t = map.at(x, y);
    t.terrain = 0;
    t.flags   = TILE_WALKABLE;
}

// ── BSP 分割 ─────────────────────────────────────────────────

void split(BspNode& node, std::mt19937& rng) {
    const bool can_h = node.h >= MIN_SIZE * 2;  // 水平切（分上下）
    const bool can_v = node.w >= MIN_SIZE * 2;  // 垂直切（分左右）

    if (!can_h && !can_v) return;  // 葉節點，停止

    // 決定切割方向
    bool split_vertical;
    if (can_h && can_v) {
        split_vertical = std::uniform_int_distribution<int>(0, 1)(rng) == 0;
    } else {
        split_vertical = can_v;
    }

    if (split_vertical) {
        // 垂直切：分左右，切在 x 軸上
        std::uniform_int_distribution<int> dist(MIN_SIZE, node.w - MIN_SIZE);
        const int cut = dist(rng);
        node.left  = std::make_unique<BspNode>(BspNode{node.x,       node.y, cut,          node.h});
        node.right = std::make_unique<BspNode>(BspNode{node.x + cut, node.y, node.w - cut, node.h});
    } else {
        // 水平切：分上下，切在 y 軸上
        std::uniform_int_distribution<int> dist(MIN_SIZE, node.h - MIN_SIZE);
        const int cut = dist(rng);
        node.left  = std::make_unique<BspNode>(BspNode{node.x, node.y,       node.w, cut});
        node.right = std::make_unique<BspNode>(BspNode{node.x, node.y + cut, node.w, node.h - cut});
    }

    split(*node.left,  rng);
    split(*node.right, rng);
}

// ── 挖房間 ───────────────────────────────────────────────────

void carve_rooms(BspNode& node, MapData& map, std::mt19937& rng, std::vector<Room>& rooms) {
    if (node.left || node.right) {
        // 非葉節點：遞迴處理子節點
        if (node.left)  carve_rooms(*node.left,  map, rng, rooms);
        if (node.right) carve_rooms(*node.right, map, rng, rooms);
        return;
    }

    // 葉節點：嘗試挖房間
    const int max_w = node.w - ROOM_PAD * 2;
    const int max_h = node.h - ROOM_PAD * 2;
    if (max_w < ROOM_MIN || max_h < ROOM_MIN) return;

    std::uniform_int_distribution<int> w_dist(ROOM_MIN, max_w);
    std::uniform_int_distribution<int> h_dist(ROOM_MIN, max_h);
    const int rw = w_dist(rng);
    const int rh = h_dist(rng);

    std::uniform_int_distribution<int> rx_dist(node.x + ROOM_PAD, node.x + node.w - ROOM_PAD - rw);
    std::uniform_int_distribution<int> ry_dist(node.y + ROOM_PAD, node.y + node.h - ROOM_PAD - rh);
    const int rx = rx_dist(rng);
    const int ry = ry_dist(rng);

    Room room{rx, ry, rw, rh};

    // 將房間內所有格設為地板
    for (int tx = rx; tx < rx + rw; ++tx)
        for (int ty = ry; ty < ry + rh; ++ty)
            set_floor(map, tx, ty);

    node.room = room;
    rooms.push_back(room);
}

// ── 取得子樹中的代表房間 ─────────────────────────────────────

const Room* get_room_from(const BspNode& node) {
    if (node.room.has_value()) return &node.room.value();
    const Room* r = nullptr;
    if (node.left)  r = get_room_from(*node.left);
    if (!r && node.right) r = get_room_from(*node.right);
    return r;
}

// ── 連接走廊 ─────────────────────────────────────────────────

void connect_rooms(BspNode& node, MapData& map) {
    if (!node.left || !node.right) return;

    // 先遞迴連接子節點
    connect_rooms(*node.left,  map);
    connect_rooms(*node.right, map);

    // 取兩個子樹各自的代表房間
    const Room* a = get_room_from(*node.left);
    const Room* b = get_room_from(*node.right);
    if (!a || !b) return;

    const int ax = a->cx(), ay = a->cy();
    const int bx = b->cx(), by = b->cy();

    // L 形走廊：先水平（ax → bx 在 y=ay），再垂直（ay → by 在 x=bx）
    const int x0 = std::min(ax, bx);
    const int x1 = std::max(ax, bx);
    for (int tx = x0; tx <= x1; ++tx) {
        if (map.in_bounds(tx, ay) && !map.at(tx, ay).is_walkable())
            set_floor(map, tx, ay);
    }

    const int y0 = std::min(ay, by);
    const int y1 = std::max(ay, by);
    for (int ty = y0; ty <= y1; ++ty) {
        if (map.in_bounds(bx, ty) && !map.at(bx, ty).is_walkable())
            set_floor(map, bx, ty);
    }
}

} // anonymous namespace

// ── 公開介面 ─────────────────────────────────────────────────

std::vector<Room> generate_bsp_dungeon(MapData& map, std::mt19937& rng) {
    // Step 1：初始化全圖為牆壁
    for (int x = 0; x < map.width; ++x) {
        for (int y = 0; y < map.height; ++y) {
            auto& t = map.at(x, y);
            t.terrain = 1;
            t.flags   = TILE_BLOCKS_SIGHT;
        }
    }

    // Step 2：建立根 BSP 節點（留 1 格牆壁邊框）
    BspNode root{1, 1, map.width - 2, map.height - 2, nullptr, nullptr, std::nullopt};

    // Step 3：遞迴分割
    split(root, rng);

    // Step 4：葉節點挖房間，收集 rooms 列表
    std::vector<Room> rooms;
    carve_rooms(root, map, rng, rooms);

    // Step 5：連接相鄰兄弟節點房間（L 形走廊）
    connect_rooms(root, map);

    // rooms[0] 為英雄起始房（第一個被挖出的葉節點房間）
    return rooms;
}

} // namespace zone
