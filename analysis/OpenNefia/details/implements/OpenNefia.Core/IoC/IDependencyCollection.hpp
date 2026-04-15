#pragma once

#include <typeindex>
#include <memory>
#include <functional>
#include <any>

namespace OpenNefia::Core::IoC {

template <typename T>
using DependencyFactoryDelegate = std::function<std::shared_ptr<T>()>;

/// <summary>
/// The IoCManager handles Dependency Injection in the project.
/// </summary>
class IDependencyCollection {
public:
    virtual ~IDependencyCollection() = default;

    /// <summary>
    /// Registers an interface to an implementation, to make it accessible to <see cref="Resolve{T}"/>
    /// <see cref="BuildGraph"/> MUST be called after this method to make the new interface available.
    /// </summary>
    template <typename TInterface, typename TImplementation>
    void Register(bool overwrite = false) {
        Register(typeid(TInterface), typeid(TImplementation), nullptr, overwrite);
    }

    /// <summary>
    /// Registers an interface to an implementation, to make it accessible to <see cref="Resolve{T}"/>
    /// <see cref="BuildGraph"/> MUST be called after this method to make the new interface available.
    /// </summary>
    template <typename TInterface, typename TImplementation>
    void Register(DependencyFactoryDelegate<TImplementation> factory, bool overwrite = false) {
        // We need to wrap the factory to return shared_ptr<void> or similar if needed by the implementation
        auto wrappedFactory = [factory]() -> std::shared_ptr<void> {
            return std::static_pointer_cast<void>(factory());
        };
        Register(typeid(TInterface), typeid(TImplementation), wrappedFactory, overwrite);
    }

    /// <summary>
    /// Registers a simple implementation without an interface.
    /// </summary>
    virtual void Register(std::type_index implementation, std::function<std::shared_ptr<void>()> factory = nullptr, bool overwrite = false) = 0;

    /// <summary>
    /// Registers a simple implementation without an interface.
    /// </summary>
    virtual void Register(std::type_index interfaceType, std::type_index implementation, std::function<std::shared_ptr<void>()> factory = nullptr, bool overwrite = false) = 0;

    /// <summary>
    ///     Registers an interface to an existing instance of an implementation.
    /// </summary>
    template <typename TInterface>
    void RegisterInstance(std::shared_ptr<TInterface> implementation, bool overwrite = false, bool deferInject = false) {
        RegisterInstance(typeid(TInterface), std::static_pointer_cast<void>(implementation), overwrite, deferInject);
    }

    /// <summary>
    ///     Registers an interface to an existing instance of an implementation.
    /// </summary>
    virtual void RegisterInstance(std::type_index type, std::shared_ptr<void> implementation, bool overwrite = false, bool deferInject = false) = 0;

    /// <summary>
    /// Clear all services and types.
    /// </summary>
    virtual void Clear() = 0;

    /// <summary>
    /// Resolve a dependency manually.
    /// </summary>
    template <typename T>
    std::shared_ptr<T> Resolve() {
        return std::static_pointer_cast<T>(ResolveType(typeid(T)));
    }

    /// <summary>
    /// Resolve a dependency manually.
    /// </summary>
    virtual std::shared_ptr<void> ResolveType(std::type_index type) = 0;

    /// <summary>
    /// Resolve a dependency manually.
    /// </summary>
    template <typename T>
    bool TryResolveType(std::shared_ptr<T>& instance) {
        std::shared_ptr<void> result;
        if (TryResolveType(typeid(T), result)) {
            instance = std::static_pointer_cast<T>(result);
            return true;
        }
        return false;
    }

    /// <summary>
    /// Resolve a dependency manually.
    /// </summary>
    virtual bool TryResolveType(std::type_index objectType, std::shared_ptr<void>& instance) = 0;

    /// <summary>
    /// Initializes the object graph by building every object and resolving all dependencies.
    /// </summary>
    virtual void BuildGraph() = 0;

    /// <summary>
    ///     Injects dependencies into all fields with [Dependency] on the provided object.
    /// </summary>
    virtual void InjectDependencies(void* obj, std::type_index type, bool oneOff = false) = 0;

    template <typename T>
    void InjectDependencies(T* obj, bool oneOff = false) {
        InjectDependencies(static_cast<void*>(obj), typeid(T), oneOff);
    }
};

} // namespace OpenNefia::Core::IoC
