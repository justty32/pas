#pragma once

namespace OpenNefia::Core::Audio {

/**
 * @brief Parameters for playing audio.
 * Ported from AudioParams.cs.
 */
struct AudioParams {
    float Volume = 1.0f;
    float Pitch = 1.0f;
    bool Loop = false;

    static AudioParams Default() { return AudioParams{}; }
};

} // namespace OpenNefia::Core::Audio
