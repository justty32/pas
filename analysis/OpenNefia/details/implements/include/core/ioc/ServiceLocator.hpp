#pragma once

#include <memory>
#include <unordered_map>
#include <typeindex>
#include <string>
#include <stdexcept>

namespace opennefia {
namespace core {

/**
 * @brief 服務定位器，用於解耦各個子系統。
 * 替代 C# 版本中的 IoCManager。
 */
class ServiceLocator {
public:
    // 禁止實例化
    ServiceLocator() = delete;

    /**
     * @brief 注冊一個服務實例。
     * @tparam TInterface 服務的介面類型。
     * @tparam TImplementation 服務的實作類型。
     */
    template<typename TInterface, typename TImplementation, typename... Args>
    static void Register(Args&&... args) {
        auto typeIdx = std::type_index(typeid(TInterface));
        _services[typeIdx] = std::make_shared<TImplementation>(std::forward<Args>(args)...);
    }

    /**
     * @brief 注冊一個現有的服務實例。
     */
    template<typename TInterface>
    static void RegisterInstance(std::shared_ptr<TInterface> instance) {
        auto typeIdx = std::type_index(typeid(TInterface));
        _services[typeIdx] = instance;
    }

    /**
     * @brief 解析並取得服務實例。
     */
    template<typename T>
    static T& Resolve() {
        auto typeIdx = std::type_index(typeid(T));
        auto it = _services.find(typeIdx);
        if (it == _services.end()) {
            throw std::runtime_error("Service not registered: " + std::string(typeid(T).name()));
        }
        return *static_cast<T*>(it->second.get());
    }

    /**
     * @brief 檢查服務是否已注冊。
     */
    template<typename T>
    static bool IsRegistered() {
        return _services.find(std::type_index(typeid(T))) != _services.end();
    }

    /**
     * @brief 清除所有服務。
     */
    static void Clear() {
        _services.clear();
    }

private:
    static inline std::unordered_map<std::type_index, std::shared_ptr<void>> _services;
};

} // namespace core
} // namespace opennefia
