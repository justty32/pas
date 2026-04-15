# 01 - 基礎建設 (Foundation)

在 C++ 中，我們首先需要建立編譯環境並實作最底層的工具類別。

## 1.1 專案結構 (CMake)

建議使用 CMake 作為建構系統，並透過 `FetchContent` 或 `vcpkg` 管理依賴。

```cmake
# CMakeLists.txt 範例
cmake_minimum_required(VERSION 3.20)
project(OpenNefiaCpp)

set(CMAKE_CXX_STANDARD 20)

# 引入 raylib, entt, yaml-cpp, spdlog, tomlplusplus
# ... (FetchContent 邏輯)

add_executable(OpenNefia
    src/main.cpp
    src/core/GameController.cpp
    # ... 其他檔案
)

target_link_libraries(OpenNefia 
    PRIVATE 
    raylib 
    EnTT::EnTT 
    yaml-cpp 
    spdlog::spdlog 
    tomlplusplus::tomlplusplus
)
```

## 1.2 服務定位器 (IoC 代替方案)

由於 C++ 缺乏反射功能，無法像 C# 使用 `[Dependency]` 屬性自動注入。我們改用一個全局或 Context-local 的 `ServiceLocator`。

**C++ 實作建議：**
```cpp
// core/ioc/ServiceLocator.hpp
class ServiceLocator {
public:
    template<typename T>
    static void Register(std::shared_ptr<T> service) {
        services[typeid(T).hash_code()] = service;
    }

    template<typename T>
    static T& Resolve() {
        return *std::static_pointer_cast<T>(services.at(typeid(T).hash_code()));
    }

private:
    static std::unordered_map<size_t, std::shared_ptr<void>> services;
};
```

## 1.3 基礎數學與工具 (Maths & Utility)

對應 `OpenNefia.Core.Maths` 與 `OpenNefia.Core.Utility`。

- **Vector2i / Vector2**: 直接對應 raylib 的 `Vector2` 或 自定義結構以支援序列化。
- **Color**: 對應 raylib 的 `Color`。
- **ResourcePath**: 實作一個類別處理 Unix 風格的路徑字串（如 `/Elona/Textures/chara.png`），內部轉換為實體路徑。

## 1.4 日誌系統 (Log)

對應 `OpenNefia.Core.Log`。

- 使用 `spdlog`。
- 封裝 `Logger` 類別，支援不同層級 (Info, Warning, Error, Fatal)。

## 1.5 配置系統 (Configuration)

對應 `OpenNefia.Core.Configuration` 與 `CVars.cs`。

- 使用 `tomlplusplus` 讀寫 `config.toml`。
- 實作 `CVar` 類別，支援觀察者模式（當設定值改變時觸發回呼）。

```cpp
// 範例：CVar 定義
namespace CVars {
    CVar<int> DisplayWidth("display.width", 1280);
    CVar<bool> LogEnabled("log.enabled", true);
}
```
