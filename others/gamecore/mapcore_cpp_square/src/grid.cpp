#include "mapcore/grid.hpp"
#include <cmath>

namespace mapcore {

const std::array<Coord, 4> DIRECTIONS = {{
    { 1,  0},   // 0: E
    { 0, -1},   // 1: N
    {-1,  0},   // 2: W
    { 0,  1},   // 3: S
}};

Coord Coord::neighbor(int direction_index) const noexcept {
    int d = ((direction_index % 4) + 4) % 4;
    return *this + DIRECTIONS[d];
}

std::array<Coord, 4> Coord::neighbors() const noexcept {
    return {{
        *this + DIRECTIONS[0],
        *this + DIRECTIONS[1],
        *this + DIRECTIONS[2],
        *this + DIRECTIONS[3],
    }};
}

int grid_distance(const Coord& a, const Coord& b) noexcept {
    return std::abs(a.x - b.x) + std::abs(a.y - b.y);
}

std::vector<Coord> grid_line(const Coord& start, const Coord& end) {
    int dx = std::abs(end.x - start.x);
    int dy = std::abs(end.y - start.y);
    if (dx == 0 && dy == 0) return {start};
    int sx = (end.x > start.x) ? 1 : -1;
    int sy = (end.y > start.y) ? 1 : -1;
    std::vector<Coord> out;
    out.reserve(static_cast<size_t>(dx + dy + 1));
    int error = dx - dy;
    int x = start.x, y = start.y;
    out.push_back({x, y});
    for (int i = 0; i < dx + dy; ++i) {
        int e2 = 2 * error;
        if (e2 > -dy) { error -= dy; x += sx; }
        else          { error += dx; y += sy; }
        out.push_back({x, y});
    }
    return out;
}

std::vector<Coord> grid_ring(const Coord& center, int radius) {
    if (radius < 0) throw std::invalid_argument("radius must be >= 0");
    if (radius == 0) return {center};
    std::vector<Coord> out;
    out.reserve(static_cast<size_t>(4 * radius));
    int x = center.x - radius;
    int y = center.y;
    constexpr int sides[4][2] = {{1, -1}, {1, 1}, {-1, 1}, {-1, -1}};
    for (auto& s : sides) {
        for (int i = 0; i < radius; ++i) {
            out.push_back({x, y});
            x += s[0];
            y += s[1];
        }
    }
    return out;
}

std::vector<Coord> grid_spiral(const Coord& center, int max_radius) {
    if (max_radius < 0) throw std::invalid_argument("max_radius must be >= 0");
    std::vector<Coord> out;
    out.reserve(static_cast<size_t>(1 + 2 * max_radius * (max_radius + 1)));
    out.push_back(center);
    for (int r = 1; r <= max_radius; ++r) {
        auto ring = grid_ring(center, r);
        for (auto& c : ring) out.push_back(c);
    }
    return out;
}

} // namespace mapcore
