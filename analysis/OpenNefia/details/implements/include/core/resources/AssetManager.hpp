#pragma once

#include <string>
#include <unordered_map>
#include <raylib.h>
#include <core/resources/ResourceCache.hpp>

namespace opennefia {
namespace core {

/**
 * @brief 資源載入與快取管理。
 * 負責將邏輯路徑載入為 raylib 的原始資源。
 */
class AssetManager {
public:
    virtual ~AssetManager() = default;

    virtual void Initialize(IResourceCache& resourceCache) = 0;
    virtual void Shutdown() = 0;

    // 取得資源 (若不存在則載入)
    virtual const Texture2D& GetTexture(const std::string& logicalPath) = 0;
    virtual const Font& GetFont(const std::string& logicalPath) = 0;
    virtual const Sound& GetSound(const std::string& logicalPath) = 0;

    // 釋放單一資源
    virtual void UnloadTexture(const std::string& logicalPath) = 0;
};

/**
 * @brief 預設的資產管理器實作。
 */
class DefaultAssetManager : public AssetManager {
public:
    void Initialize(IResourceCache& resourceCache) override {
        _resourceCache = &resourceCache;
    }
    void Shutdown() override;

    const Texture2D& GetTexture(const std::string& logicalPath) override;
    const Font& GetFont(const std::string& logicalPath) override;
    const Sound& GetSound(const std::string& logicalPath) override;

    void UnloadTexture(const std::string& logicalPath) override;

private:
    IResourceCache* _resourceCache = nullptr;
    std::unordered_map<std::string, Texture2D> _textures;
    std::unordered_map<std::string, Font> _fonts;
    std::unordered_map<std::string, Sound> _sounds;

    // 備用資源 (當路徑解析失敗時返回，避免崩潰)
    Texture2D _fallbackTexture;
    Font _fallbackFont;
};

} // namespace core
} // namespace opennefia
