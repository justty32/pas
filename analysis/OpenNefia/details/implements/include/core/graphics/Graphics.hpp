#pragma once

#include <string>
#include <raylib.h>

namespace opennefia {
namespace core {

/**
 * @brief 圖形渲染介面。
 * 封裝了 raylib 的底層繪圖邏輯。
 */
class IGraphics {
public:
    virtual ~IGraphics() = default;

    virtual void Initialize(int width, int height, const std::string& title) = 0;
    virtual void Shutdown() = 0;

    virtual void BeginDraw() = 0;
    virtual void EndDraw() = 0;

    // 繪圖基本操作
    virtual void DrawTexture(const Texture2D& tex, float x, float y, Color tint = WHITE) = 0;
    virtual void DrawTextureRec(const Texture2D& tex, Rectangle source, Vector2 position, Color tint = WHITE) = 0;
    virtual void DrawRectangle(float x, float y, float w, float h, Color color) = 0;
    virtual void DrawText(const Font& font, const std::string& text, Vector2 pos, float fontSize, float spacing, Color tint) = 0;

    // 視窗狀態
    virtual bool WindowShouldClose() const = 0;
    virtual int GetWidth() const = 0;
    virtual int GetHeight() const = 0;
};

/**
 * @brief raylib 圖形實作。
 */
class RaylibGraphics : public IGraphics {
public:
    void Initialize(int width, int height, const std::string& title) override;
    void Shutdown() override;

    void BeginDraw() override;
    void EndDraw() override;

    void DrawTexture(const Texture2D& tex, float x, float y, Color tint = WHITE) override;
    void DrawTextureRec(const Texture2D& tex, Rectangle source, Vector2 position, Color tint = WHITE) override;
    void DrawRectangle(float x, float y, float w, float h, Color color) override;
    void DrawText(const Font& font, const std::string& text, Vector2 pos, float fontSize, float spacing, Color tint) override;

    bool WindowShouldClose() const override { return ::WindowShouldClose(); }
    int GetWidth() const override { return ::GetScreenWidth(); }
    int GetHeight() const override { return ::GetScreenHeight(); }
};

} // namespace core
} // namespace opennefia
