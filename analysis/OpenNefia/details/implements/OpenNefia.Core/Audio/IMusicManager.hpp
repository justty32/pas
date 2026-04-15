#pragma once

#include <string>

namespace OpenNefia::Core::Audio {

/**
 * @brief Interface for music management.
 * Ported from IMusicManager.cs.
 */
class IMusicManager {
public:
    virtual ~IMusicManager() = default;

    virtual bool IsPlaying() const = 0;

    virtual void Initialize() = 0;
    virtual void Shutdown() = 0;

    /**
     * @brief Plays a music file.
     */
    virtual void Play(const std::string& musicId) = 0;

    /**
     * @brief Restarts playing the current music.
     */
    virtual void Restart() = 0;

    /**
     * @brief Stops playing music.
     */
    virtual void Stop() = 0;
};

} // namespace OpenNefia::Core::Audio
