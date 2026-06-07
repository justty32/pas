#pragma once

namespace zone {

// Move/Attack 的 param 方向編碼：dx,dy ∈ {-1,0,1} → 0..8。
// 之後若 param 改作目標 entity / 法術 id，這層只在 Move 類效果內使用。
inline int encode_dir(int dx, int dy) { return (dy + 1) * 3 + (dx + 1); }

inline void decode_dir(int p, int& dx, int& dy) {
    dx = (p % 3) - 1;
    dy = (p / 3) - 1;
}

} // namespace zone
