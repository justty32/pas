#pragma once

#include <vector>
#include <memory>

namespace opennefia {
namespace core {

/**
 * @brief UI 層介面。
 */
class UiLayer {
public:
    virtual ~UiLayer() = default;

    virtual void OnOpen() {}
    virtual void OnClose() {}

    /**
     * @brief 每幀更新邏輯。
     * @param dt 幀間隔時間 (秒)。
     */
    virtual void Update(float dt) = 0;

    /**
     * @brief 渲染 UI。
     */
    virtual void Draw() = 0;

    /**
     * @brief 判斷此層是否遮擋下方的層（不渲染下方）。
     */
    virtual bool IsOpaque() const { return false; }
};

/**
 * @brief UI 管理器介面。
 * 管理 UI 層的堆疊。
 */
class IUIManager {
public:
    virtual ~IUIManager() = default;

    virtual void Initialize() = 0;
    virtual void Shutdown() = 0;

    virtual void PushLayer(std::unique_ptr<UiLayer> layer) = 0;
    virtual void PopLayer() = 0;

    virtual void Update(float dt) = 0;
    virtual void Draw() = 0;

    virtual bool HasLayers() const = 0;
};

/**
 * @brief 預設的 UI 管理器實作。
 */
class UIManager : public IUIManager {
public:
    void Initialize() override {}
    void Shutdown() override;

    void PushLayer(std::unique_ptr<UiLayer> layer) override;
    void PopLayer() override;

    void Update(float dt) override;
    void Draw() override;

    bool HasLayers() const override { return !_layers.empty(); }

private:
    std::vector<std::unique_ptr<UiLayer>> _layers;
};

} // namespace core
} // namespace opennefia
