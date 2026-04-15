#pragma once

#include "ITaskManager.hpp"
#include <queue>
#include <mutex>

namespace OpenNefia::Core::Asynchronous {

/**
 * @brief Default implementation of ITaskManager.
 * Ported from TaskManager.cs.
 */
class TaskManager : public ITaskManager {
private:
    std::queue<std::function<void()>> _pendingTasks;
    std::mutex _mutex;

public:
    void Initialize() override {}

    void ProcessPendingTasks() override {
        std::vector<std::function<void()>> tasks;
        {
            std::lock_guard<std::mutex> lock(_mutex);
            while (!_pendingTasks.empty()) {
                tasks.push_back(std::move(_pendingTasks.front()));
                _pendingTasks.pop();
            }
        }

        for (auto& task : tasks) {
            if (task) task();
        }
    }

    void RunOnMainThread(std::function<void()> callback) override {
        std::lock_guard<std::mutex> lock(_mutex);
        _pendingTasks.push(std::move(callback));
    }
};

} // namespace OpenNefia::Core::Asynchronous
