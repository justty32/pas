#pragma once

#include "../Maths/Vector2.hpp"

namespace OpenNefia::Core::Maps {

using namespace OpenNefia::Core::Maths;

struct ScreenCoordinates {
    Vector2 Position;

    constexpr ScreenCoordinates(float x = 0, float y = 0) : Position(x, y) {}
    constexpr ScreenCoordinates(Vector2 pos) : Position(pos) {}
};

} // namespace OpenNefia::Core::Maps
