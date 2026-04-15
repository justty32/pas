#pragma once

#include "AudioParams.hpp"
#include <string>
#include <optional>

namespace OpenNefia::Core::Audio {

/**
 * @brief Interface for audio management.
 * Ported from IAudioManager.cs.
 */
class IAudioManager {
public:
    virtual ~IAudioManager() = default;

    virtual void Initialize() = 0;
    virtual void Shutdown() = 0;

    /**
     * @brief Plays an audio file globally.
     */
    virtual void Play(const std::string& soundId, std::optional<AudioParams> audioParams = std::nullopt) = 0;

    /**
     * @brief Plays an audio file following an entity.
     */
    // virtual void Play(const std::string& soundId, EntityUid entityUid, std::optional<AudioParams> audioParams = std::nullopt) = 0;

    /**
     * @brief Plays an audio file at a static position.
     */
    // virtual void Play(const std::string& soundId, MapCoordinates coordinates, std::optional<AudioParams> audioParams = std::nullopt) = 0;

    /**
     * @brief Sets the listener position.
     */
    // virtual void SetListenerPosition(Vector2 listenerPos) = 0;
};

} // namespace OpenNefia::Core::Audio
