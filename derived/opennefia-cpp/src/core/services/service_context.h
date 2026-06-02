#pragma once
#include <memory>
#include <string>

namespace spdlog { class logger; }

namespace opennefia {

// 全域單例服務容器（縮小 DI 範圍到「真·全域」）。
// 仿 medps 的 ServiceLocator 概念，但不用反射——強型別存取器。
//
// Phase 1：只有 Log。
// Phase 2 會補：IRandom, Locale（資料層）, VFS（唯讀）
// Phase 3 會補：CVar（設定）
class ServiceContext {
public:
    // 預設建構 = null logger（測試用，不輸出任何訊息）
    ServiceContext();
    ~ServiceContext();

    // 建立有 stdout 輸出的標準 logger
    static ServiceContext make_default(const std::string& name = "opennefia");

    spdlog::logger& log();

private:
    std::shared_ptr<spdlog::logger> log_;
};

} // namespace opennefia
