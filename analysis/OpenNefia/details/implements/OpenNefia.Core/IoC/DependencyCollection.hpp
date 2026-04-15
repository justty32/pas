#pragma once

#include "IDependencyCollection.hpp"
#include <unordered_map>
#include <vector>
#include <typeindex>

namespace OpenNefia::Core::IoC {

class DependencyCollection : public IDependencyCollection {
private:
    struct ServiceRegistration {
        std::type_index interfaceType;
        std::type_index implementationType;
        std::function<std::shared_ptr<void>()> factory;
        std::shared_ptr<void> instance;
        bool instantiated = false;
    };

    std::unordered_map<std::type_index, ServiceRegistration> _registrations;
    bool _built = false;

public:
    void Register(std::type_index implementation, std::function<std::shared_ptr<void>()> factory = nullptr, bool overwrite = false) override;
    void Register(std::type_index interfaceType, std::type_index implementation, std::function<std::shared_ptr<void>()> factory = nullptr, bool overwrite = false) override;
    void RegisterInstance(std::type_index type, std::shared_ptr<void> implementation, bool overwrite = false, bool deferInject = false) override;

    void Clear() override;
    std::shared_ptr<void> ResolveType(std::type_index type) override;
    bool TryResolveType(std::type_index objectType, std::shared_ptr<void>& instance) override;
    void BuildGraph() override;
    void InjectDependencies(void* obj, std::type_index type, bool oneOff = false) override;
};

} // namespace OpenNefia::Core::IoC
