#pragma once

#include <functional>

namespace OpenNefia::Core::Asynchronous {

/**
 * @brief Interface for task management.
 * Ported from ITaskManager.cs.
 */
class ITaskManager {
public:
    virtual ~ITaskManager() = default;

    virtual void Initialize() = 0;
    virtual void ProcessPendingTasks() = 0;

    /**
     * @brief Run a delegate on the main thread sometime later.
     * Thread safe.
     */
    virtual void RunOnMainThread(std::function<void()> callback) = 0;
};

} // namespace OpenNefia::Core::Asynchronous
