#include <core/graphics/Graphics.hpp>

namespace opennefia {
namespace core {

void RaylibGraphics::Initialize(int width, int height, const std::string& title) {
    ::InitWindow(width, height, title.c_str());
}

void RaylibGraphics::Shutdown() {
    ::CloseWindow();
}

void RaylibGraphics::BeginDraw() {
    ::BeginDrawing();
    ::ClearBackground(BLACK);
}

void RaylibGraphics::EndDraw() {
    ::EndDrawing();
}

void RaylibGraphics::DrawTexture(const Texture2D& tex, float x, float y, Color tint) {
    ::DrawTexture(tex, (int)x, (int)y, tint);
}

void RaylibGraphics::DrawTextureRec(const Texture2D& tex, Rectangle source, Vector2 position, Color tint) {
    ::DrawTextureRec(tex, source, position, tint);
}

void RaylibGraphics::DrawRectangle(float x, float y, float w, float h, Color color) {
    ::DrawRectangle((int)x, (int)y, (int)w, (int)h, color);
}

void RaylibGraphics::DrawText(const Font& font, const std::string& text, Vector2 pos, float fontSize, float spacing, Color tint) {
    ::DrawTextEx(font, text.c_str(), pos, fontSize, spacing, tint);
}

} // namespace core
} // namespace opennefia
