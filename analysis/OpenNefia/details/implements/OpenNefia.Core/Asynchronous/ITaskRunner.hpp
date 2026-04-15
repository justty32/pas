#pragma once

#include <future>

namespace OpenNefia::Core::Asynchronous {

/**
 * @brief Interface for running tasks.
 * Ported from ITaskRunner.cs.
 */
class ITaskRunner {
public:
    virtual ~ITaskRunner() = default;

    /**
     * @brief Run a task (corresponds to Task in C#).
     */
    virtual void Run(std::future<void> task) = 0;

    /**
     * @brief Run a task and wait for result (corresponds to Task<T> in C#).
     */
    // template <typename T>
    // virtual T Run(std::future<T> task) = 0;
};

} // namespace OpenNefia::Core::Asynchronous
