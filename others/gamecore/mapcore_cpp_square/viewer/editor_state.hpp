#pragma once
// 編輯器狀態：對應 mapcore_cpp/viewer/editor_state.hpp 的方格版本。
// 不含 ocean_mask/temperature/rainfall overlay。

#include "grid_layout.hpp"

#include <cstddef>
#include <string>
#include <vector>

namespace viewer {

enum class Tool {
    Raise,
    Lower,
    Ridge,
    Rift,
    WaterSource,
};

class EditorState {
public:
    EditorState(int width, int height);

    [[nodiscard]] int width()  const noexcept { return width_; }
    [[nodiscard]] int height() const noexcept { return height_; }
    [[nodiscard]] std::size_t size() const noexcept { return heightmap_.size(); }

    [[nodiscard]] bool in_bounds(int x, int y) const noexcept {
        return x >= 0 && x < width_ && y >= 0 && y < height_;
    }

    [[nodiscard]] float get_h(int x, int y) const noexcept {
        return heightmap_[static_cast<std::size_t>(y) * static_cast<std::size_t>(width_) + static_cast<std::size_t>(x)];
    }
    void set_h(int x, int y, float h) noexcept {
        heightmap_[static_cast<std::size_t>(y) * static_cast<std::size_t>(width_) + static_cast<std::size_t>(x)] = h;
    }
    void add_h(int x, int y, float delta) noexcept {
        auto& v = heightmap_[static_cast<std::size_t>(y) * static_cast<std::size_t>(width_) + static_cast<std::size_t>(x)];
        v += delta;
        if (v < 0.0f) v = 0.0f;
        if (v > 1.0f) v = 1.0f;
    }

    [[nodiscard]] std::vector<float>&       heightmap()       noexcept { return heightmap_; }
    [[nodiscard]] const std::vector<float>& heightmap() const noexcept { return heightmap_; }

    void resize(int width, int height);
    void reset_heights(float h = 0.5f);

    // ── 場景參數 ──
    float cell_size = 16.0f;
    float sea_level = 0.35f;

    // ── 工具狀態 ──
    Tool  current_tool   = Tool::Raise;
    int   brush_size     = 3;
    float brush_strength = 0.05f;
    float brush_rate     = 30.0f;

    // ── Ridge/Rift 徑向 stamp 參數 ──
    float brush_falloff       = 2.0f;
    float brush_chaos         = 0.0f;
    int   brush_spokes        = 0;
    bool  brush_spokes_rand   = false;
    int   brush_spokes_min    = 0;
    int   brush_spokes_max    = 0;
    bool  brush_spokes_invert = false;

    // ── 平滑隨機 rate ──
    bool  brush_rate_rand     = false;
    float brush_rate_min      = 5.0f;
    float brush_rate_max      = 40.0f;

    // ── Noise 生成參數 ──
    int   noise_seed             = 42;
    int   noise_shape            = 0;
    float noise_shape_strength   = 0.85f;
    float noise_ridge_weight     = 0.0f;
    int   noise_ridge_mode       = 0;
    int   noise_num_plates       = 20;
    int   noise_octaves          = 4;
    float noise_persistence      = 0.5f;
    int   noise_base_freq        = 4;
    float noise_blend            = 0.0f;

    // ── 水源 marker ──
    std::vector<GridCoord> water_sources;

private:
    int width_;
    int height_;
    std::vector<float> heightmap_;
};

} // namespace viewer
