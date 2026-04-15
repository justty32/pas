#pragma once

#include <string>
#include <filesystem>
#include <unordered_map>

namespace opennefia {
namespace core {

/**
 * @brief 虛擬檔案系統介面。
 */
class IResourceCache {
public:
    virtual ~IResourceCache() = default;

    /**
     * @brief 初始化資源系統。
     * @param userDataPath 使用者存檔/設定目錄路徑。
     */
    virtual void Initialize(const std::filesystem::path& userDataPath) = 0;

    /**
     * @brief 掛載一個邏輯目錄到實體目錄。
     * @param prefix 邏輯路徑前綴 (例如 "/Elona")。
     * @param physicalPath 實體磁碟路徑。
     */
    virtual void Mount(const std::string& prefix, const std::filesystem::path& physicalPath) = 0;

    /**
     * @brief 解析邏輯路徑為實體路徑。
     * @param logicalPath 邏輯路徑 (例如 "/Elona/Textures/chara.png")。
     * @return 實體路徑。若不存在則返回空路徑。
     */
    virtual std::filesystem::path ResolvePath(const std::string& logicalPath) const = 0;
};

/**
 * @brief 預設的資源管理實作。
 */
class ResourceCache : public IResourceCache {
public:
    void Initialize(const std::filesystem::path& userDataPath) override;
    void Mount(const std::string& prefix, const std::filesystem::path& physicalPath) override;
    std::filesystem::path ResolvePath(const std::string& logicalPath) const override;

private:
    std::filesystem::path _userDataPath;
    std::unordered_map<std::string, std::filesystem::path> _mounts;
};

} // namespace core
} // namespace opennefia
