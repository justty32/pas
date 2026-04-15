#include <core/resources/AssetManager.hpp>
#include <iostream>

namespace opennefia {
namespace core {

void DefaultAssetManager::Shutdown() {
    for (auto& [path, tex] : _textures) ::UnloadTexture(tex);
    for (auto& [path, font] : _fonts) ::UnloadFont(font);
    for (auto& [path, sound] : _sounds) ::UnloadSound(sound);
    _textures.clear();
    _fonts.clear();
    _sounds.clear();
}

const Texture2D& DefaultAssetManager::GetTexture(const std::string& logicalPath) {
    if (_textures.find(logicalPath) != _textures.end()) {
        return _textures[logicalPath];
    }

    auto physical = _resourceCache->ResolvePath(logicalPath);
    if (!physical.empty() && std::filesystem::exists(physical)) {
        Texture2D tex = ::LoadTexture(physical.string().c_str());
        if (tex.id != 0) {
            _textures[logicalPath] = tex;
            return _textures[logicalPath];
        }
    }

    std::cerr << "Failed to load texture: " << logicalPath << " (Physical: " << physical << ")" << std::endl;
    return _fallbackTexture;
}

const Font& DefaultAssetManager::GetFont(const std::string& logicalPath) {
    if (_fonts.find(logicalPath) != _fonts.end()) {
        return _fonts[logicalPath];
    }

    auto physical = _resourceCache->ResolvePath(logicalPath);
    if (!physical.empty() && std::filesystem::exists(physical)) {
        Font font = ::LoadFont(physical.string().c_str());
        if (font.texture.id != 0) {
            _fonts[logicalPath] = font;
            return _fonts[logicalPath];
        }
    }

    return _fallbackFont;
}

const Sound& DefaultAssetManager::GetSound(const std::string& logicalPath) {
    // 類似的邏輯...
    static Sound nullSound = { 0 };
    return nullSound;
}

void DefaultAssetManager::UnloadTexture(const std::string& logicalPath) {
    auto it = _textures.find(logicalPath);
    if (it != _textures.end()) {
        ::UnloadTexture(it->second);
        _textures.erase(it);
    }
}

} // namespace core
} // namespace opennefia
