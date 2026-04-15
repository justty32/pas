#pragma once

#include "BoundKeyFunction.hpp"
#include "BoundKeyState.hpp"
#include "../Maps/ScreenCoordinates.hpp"

namespace OpenNefia::Core::Input {

using namespace OpenNefia::Core::Maps;

struct BoundKeyEventArgs {
    BoundKeyFunction Function;
    BoundKeyState State;
    ScreenCoordinates PointerLocation;
    bool CanFocus;
    bool Handled = false;

    BoundKeyEventArgs(BoundKeyFunction func, BoundKeyState state, ScreenCoordinates pos, bool canFocus)
        : Function(func), State(state), PointerLocation(pos), CanFocus(canFocus) {}

    void Handle() { Handled = true; }
};

} // namespace OpenNefia::Core::Input
