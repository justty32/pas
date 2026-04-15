#pragma once

#include "IDependencyCollection.hpp"
#include <stdexcept>

namespace OpenNefia::Core::IoC {

/// <summary>
/// The IoCManager handles Dependency Injection in the project.
/// </summary>
class IoCManager {
private:
    static inline thread_local IDependencyCollection* _container = nullptr;

public:
    /// <summary>
    /// Returns the singleton thread-local instance of the IoCManager's dependency collection.
    /// </summary>
    static IDependencyCollection* Instance() {
        return _container;
    }

    /// <summary>
    /// Ensures that the <see cref="IDependencyCollection"/> instance exists for this thread.
    /// </summary>
    static void InitThread();

    /// <summary>
    /// Sets an existing <see cref="IDependencyCollection"/> as the instance for this thread.
    /// </summary>
    static void InitThread(IDependencyCollection* collection, bool replaceExisting = false) {
        if (_container != nullptr && !replaceExisting) {
            throw std::runtime_error("This thread has already been initialized.");
        }
        _container = collection;
    }

    /// <summary>
    /// Registers an interface to an implementation, to make it accessible to <see cref="Resolve{T}"/>
    /// </summary>
    template <typename TInterface, typename TImplementation>
    static void Register(bool overwrite = false) {
        if (_container == nullptr) throw std::runtime_error("IoC not initialized on this thread.");
        _container->Register<TInterface, TImplementation>(overwrite);
    }

    /// <summary>
    /// Register an implementation, to make it accessible to <see cref="Resolve{T}"/>
    /// </summary>
    template <typename T>
    static void Register(bool overwrite = false) {
        Register<T, T>(overwrite);
    }

    /// <summary>
    /// Registers an interface to an implementation, to make it accessible to <see cref="Resolve{T}"/>
    /// </summary>
    template <typename TInterface, typename TImplementation>
    static void Register(DependencyFactoryDelegate<TImplementation> factory, bool overwrite = false) {
        if (_container == nullptr) throw std::runtime_error("IoC not initialized on this thread.");
        _container->Register<TInterface, TImplementation>(factory, overwrite);
    }

    /// <summary>
    ///     Registers an interface to an existing instance of an implementation.
    /// </summary>
    template <typename TInterface>
    static void RegisterInstance(std::shared_ptr<TInterface> implementation, bool overwrite = false, bool deferInject = false) {
        if (_container == nullptr) throw std::runtime_error("IoC not initialized on this thread.");
        _container->RegisterInstance<TInterface>(implementation, overwrite, deferInject);
    }

    /// <summary>
    /// Clear all services and types.
    /// </summary>
    static void Clear() {
        if (_container != nullptr)
            _container->Clear();
    }

    /// <summary>
    /// Resolve a dependency manually.
    /// </summary>
    template <typename T>
    static std::shared_ptr<T> Resolve() {
        if (_container == nullptr) throw std::runtime_error("IoC not initialized on this thread.");
        return _container->Resolve<T>();
    }

    /// <summary>
    /// Resolve a dependency manually.
    /// </summary>
    static std::shared_ptr<void> ResolveType(std::type_index type) {
        if (_container == nullptr) throw std::runtime_error("IoC not initialized on this thread.");
        return _container->ResolveType(type);
    }

    /// <summary>
    /// Initializes the object graph by building every object and resolving all dependencies.
    /// </summary>
    static void BuildGraph() {
        if (_container == nullptr) throw std::runtime_error("IoC not initialized on this thread.");
        _container->BuildGraph();
    }

    /// <summary>
    ///     Injects dependencies into all fields with [Dependency] on the provided object.
    /// </summary>
    template <typename T>
    static T* InjectDependencies(T* obj) {
        if (_container == nullptr) throw std::runtime_error("IoC not initialized on this thread.");
        _container->InjectDependencies(obj);
        return obj;
    }
};

} // namespace OpenNefia::Core::IoC
