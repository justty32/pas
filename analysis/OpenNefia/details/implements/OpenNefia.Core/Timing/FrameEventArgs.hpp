#pragma once

namespace OpenNefia::Core::Timing {

struct FrameEventArgs {
    float Elapsed;

    constexpr FrameEventArgs(float elapsed = 0) : Elapsed(elapsed) {}
};

} // namespace OpenNefia::Core::Timing
