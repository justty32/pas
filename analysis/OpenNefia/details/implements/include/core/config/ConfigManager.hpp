#pragma once

#include <string>
#include <vector>
#include <functional>
#include <variant>
#include <unordered_map>

namespace opennefia {
namespace core {

/**
 * @brief 配置變數的實體。
 * @tparam T 資料類型。
 */
template<typename T>
class CVar {
public:
    using Callback = std::function<void(const T&)>;

    CVar(std::string name, T defaultValue) 
        : _name(std::move(name)), _value(defaultValue) {}

    const std::string& GetName() const { return _name; }
    const T& Get() const { return _value; }

    void Set(const T& newValue) {
        if (_value != newValue) {
            _value = newValue;
            for (auto& cb : _callbacks) {
                cb(_value);
            }
        }
    }

    void OnChanged(Callback cb) {
        _callbacks.push_back(std::move(cb));
    }

private:
    std::string _name;
    T _value;
    std::vector<Callback> _callbacks;
};

/**
 * @brief 全局配置管理。
 * 封裝了對所有 CVar 的存取。
 */
class ConfigManager {
public:
    virtual ~ConfigManager() = default;
    
    // 初始化與載入
    virtual void Initialize() = 0;
    virtual void Load(const std::string& filePath) = 0;
    virtual void Save(const std::string& filePath) = 0;

    // 取得/設定值
    template<typename T>
    void SetCVar(CVar<T>& cvar, const T& value) {
        cvar.Set(value);
    }

    template<typename T>
    const T& GetCVar(const CVar<T>& cvar) const {
        return cvar.Get();
    }
};

/**
 * @brief 預定義的核心 CVars。
 */
namespace CVars {
    inline CVar<int> DisplayWidth{"display.width", 1280};
    inline CVar<int> DisplayHeight{"display.height", 720};
    inline CVar<bool> DisplayFullscreen{"display.fullscreen", false};
    inline CVar<bool> DisplayVSync{"display.vsync", true};
    
    inline CVar<float> AudioMasterVolume{"audio.master_volume", 1.0f};
    inline CVar<float> AudioSfxVolume{"audio.sfx_volume", 1.0f};
    inline CVar<float> AudioMusicVolume{"audio.music_volume", 1.0f};

    inline CVar<std::string> LogLevel{"log.level", "info"};
}

} // namespace core
} // namespace opennefia
