# 01 - 基礎建設實作細節 (Foundation Detail)

## 1.1 服務定位器 (Service Locator)

為了模擬 C# 的 IoC 容器，我們在 C++ 中實作一個強型別的 `ServiceLocator`。

```cpp
// src/core/ioc/ServiceLocator.hpp
#include <memory>
#include <unordered_map>
#include <typeindex>
#include <stdexcept>

class ServiceLocator {
public:
    // 注冊服務 (介面與實作)
    template<typename TInterface, typename TImplementation, typename... Args>
    static void Register(Args&&... args) {
        auto typeIdx = std::type_index(typeid(TInterface));
        services[typeIdx] = std::make_shared<TImplementation>(std::forward<Args>(args)...);
    }

    // 解析服務
    template<typename T>
    static T& Resolve() {
        auto typeIdx = std::type_index(typeid(T));
        auto it = services.find(typeIdx);
        if (it == services.end()) {
            throw std::runtime_error("Service not registered: " + std::string(typeid(T).name()));
        }
        return *static_cast<T*>(it->second.get());
    }

    static void Clear() { services.clear(); }

private:
    static inline std::unordered_map<std::type_index, std::shared_ptr<void>> services;
};
```

## 1.2 全域配置變數 (CVars)

對應 `OpenNefia.Core.Configuration`。使用 `tomlplusplus` 作為後端。

```cpp
// src/core/config/CVar.hpp
template<typename T>
class CVar {
public:
    CVar(std::string name, T defaultValue) 
        : _name(std::move(name)), _value(defaultValue) {}

    const T& Get() const { return _value; }
    void Set(T newValue) { 
        if (_value != newValue) {
            _value = newValue;
            for (auto& cb : _callbacks) cb(newValue);
        }
    }

    void OnChanged(std::function<void(T)> cb) { _callbacks.push_back(cb); }

private:
    std::string _name;
    T _value;
    std::vector<std::function<void(T)>> _callbacks;
};

// src/core/config/CVars.hpp
namespace CVars {
    inline CVar<int> DisplayWidth{"display.width", 1280};
    inline CVar<int> DisplayHeight{"display.height", 720};
    inline CVar<bool> DisplayFullscreen{"display.fullscreen", false);
}
```

## 1.3 虛擬檔案系統 (VFS)

處理如 `/Elona/Textures/chara.png` 的邏輯路徑。

```cpp
// src/core/resources/ResourceCache.hpp
class ResourceCache {
public:
    // 將 "/Elona/Textures/test.png" 轉換為實際磁碟路徑
    // 如 "assets/modules/Elona/Textures/test.png"
    std::filesystem::path ResolvePath(const std::string& logicalPath);
    
    // 掛載目錄
    void Mount(const std::string& prefix, const std::filesystem::path& physicalPath);
};
```

## 1.4 初始化流程 (Main.cpp)

```cpp
int main() {
    // 1. 初始化日誌 (spdlog)
    auto logger = spdlog::stdout_color_mt("console");
    spdlog::set_default_logger(logger);

    // 2. 注冊核心服務
    ServiceLocator::Register<IResourceCache, ResourceCache>();
    ServiceLocator::Register<IConfigManager, ConfigManager>();
    
    // 3. 載入設定檔
    auto& config = ServiceLocator::Resolve<IConfigManager>();
    config.Load("config.toml");

    // 4. 啟動遊戲控制器
    GameController controller;
    if (controller.Startup()) {
        controller.Run();
    }

    return 0;
}
```
