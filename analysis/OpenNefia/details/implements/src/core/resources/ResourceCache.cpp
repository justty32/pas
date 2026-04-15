#include <core/resources/ResourceCache.hpp>
#include <iostream>

namespace opennefia {
namespace core {

void ResourceCache::Initialize(const std::filesystem::path& userDataPath) {
    _userDataPath = userDataPath;
    if (!std::filesystem::exists(_userDataPath)) {
        std::filesystem::create_directories(_userDataPath);
    }
}

void ResourceCache::Mount(const std::string& prefix, const std::filesystem::path& physicalPath) {
    if (!std::filesystem::exists(physicalPath)) {
        std::cerr << "Warning: Physical path does not exist for mount: " << physicalPath << std::endl;
        return;
    }
    _mounts[prefix] = physicalPath;
}

std::filesystem::path ResourceCache::ResolvePath(const std::string& logicalPath) const {
    // 檢查是否以掛載的前綴開頭
    for (const auto& [prefix, physicalPath] : _mounts) {
        if (logicalPath.compare(0, prefix.length(), prefix) == 0) {
            std::string relative = logicalPath.substr(prefix.length());
            // 移除路徑開頭的反斜線或斜線，避免與絕對路徑混淆
            if (!relative.empty() && (relative[0] == '/' || relative[0] == '\\')) {
                relative = relative.substr(1);
            }
            return physicalPath / relative;
        }
    }
    return "";
}

} // namespace core
} // namespace opennefia
