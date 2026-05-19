#include "mapcore/map.hpp"
#include <stdexcept>

namespace mapcore {

TileMap::TileMap(int width, int height, uint16_t default_terrain)
    : width_(width), height_(height), tiles_(static_cast<size_t>(width * height))
{
    if (width <= 0 || height <= 0)
        throw std::invalid_argument("width and height must be > 0");
    for (auto& t : tiles_) t.terrain = default_terrain;
}

Tile* TileMap::get(const Coord& c) noexcept {
    if (!in_bounds(c)) return nullptr;
    return &tiles_[c.y * width_ + c.x];
}

const Tile* TileMap::get(const Coord& c) const noexcept {
    if (!in_bounds(c)) return nullptr;
    return &tiles_[c.y * width_ + c.x];
}

void TileMap::set_terrain(const Coord& c, uint16_t terrain) {
    if (!in_bounds(c))
        throw std::out_of_range("Coord out of bounds");
    tiles_[c.y * width_ + c.x].terrain = terrain;
}

std::vector<Coord> TileMap::neighbors(const Coord& c) const {
    std::vector<Coord> out;
    out.reserve(4);
    for (const auto& d : DIRECTIONS) {
        Coord n = c + d;
        if (in_bounds(n)) out.push_back(n);
    }
    return out;
}

std::vector<Coord> TileMap::passable_neighbors(const Coord& c) const {
    std::vector<Coord> out;
    out.reserve(4);
    for (const auto& d : DIRECTIONS) {
        Coord n = c + d;
        if (in_bounds(n) && is_passable(tiles_[n.y * width_ + n.x].terrain))
            out.push_back(n);
    }
    return out;
}

void TileMap::fill(uint16_t terrain) {
    for (auto& t : tiles_) t.terrain = terrain;
}

void TileMap::for_each(std::function<void(const Coord&, Tile&)> fn) {
    for (int y = 0; y < height_; ++y)
        for (int x = 0; x < width_; ++x)
            fn(Coord{x, y}, tiles_[y * width_ + x]);
}

void TileMap::for_each(std::function<void(const Coord&, const Tile&)> fn) const {
    for (int y = 0; y < height_; ++y)
        for (int x = 0; x < width_; ++x)
            fn(Coord{x, y}, tiles_[y * width_ + x]);
}

float terrain_cost(uint16_t terrain_id) {
    return get_default_registry().move_cost(terrain_id);
}

bool is_passable(uint16_t terrain_id) {
    return get_default_registry().is_passable(terrain_id);
}

} // namespace mapcore
