#include "service_context.h"
#include <spdlog/spdlog.h>
#include <spdlog/logger.h>
#include <spdlog/sinks/stdout_color_sinks.h>

namespace opennefia {

ServiceContext::ServiceContext() {
    // 預設：建立沒有 sink 的靜默 logger（測試用，不輸出任何訊息）
    log_ = std::make_shared<spdlog::logger>("null");
}

ServiceContext::~ServiceContext() = default;

ServiceContext ServiceContext::make_default(const std::string& name) {
    ServiceContext ctx;
    ctx.log_ = spdlog::stdout_color_mt(name);
    return ctx;
}

spdlog::logger& ServiceContext::log() {
    return *log_;
}

} // namespace opennefia
