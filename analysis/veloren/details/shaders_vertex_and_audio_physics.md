# Shader 數學、頂點數據與音訊物理深度分析 (Analysis)

## 1. GPU 粒子大招特效實作 (`assets/voxygen/shaders/particle-vert.glsl`)
Veloren 的華麗特效完全依賴於 GPU 的數學模型。

### 核心代碼標註：
- **螺旋能量束 (`LIFESTEAL_BEAM`)**：[Line 485] 結合 `spiral_motion` 與 `tick_loop` 正弦顏色震盪，實現了吸血技能的動態視覺感。
- **冰霜擴散 (`ICE`)**：[Line 515] 使用高飽和度冰藍色 ( ice_color > 1.0) 與 `slow_end` 函數，模擬冰粒冷凝與懸浮的物理效果。
- **運動模型組合**：系統預定義了 `linear_motion` (直線) 與 `quadratic_bezier_motion` (曲線) 等原子動作，透過隨機熵 (`rand`) 實現粒子的多樣性。

## 2. 極致頂點壓縮技術 (`voxygen/src/render/pipelines/terrain.rs`)
在體素渲染中，記憶體頻寬是最大的瓶頸。

### 關鍵設計：
- **位元竊取技術 (`make_col_light`)**：[Line 75] 為了在每個頂點省下額外字段，系統從 R/B 通道竊取 1-bit 用於存儲 `glow` (自發光) 數據。
- **法線量化**：[Line 25] 體素的 6 面法線被編碼為 3-bit 的索引，大幅減少了頂點緩衝區的大小。
- **WGPU 統一數據流**：[Line 135] 全局時間與地理界限透過 `Locals` 統一同步，確保了所有 Shader 共享一致的光照物理環境。

## 3. 環境音效與物理遮擋實作 (`voxygen/src/audio/ambience.rs`)
音效系統具備基本的地理感知能力。

### 核心機制：
- **動態濾波與遮擋**：當玩家處於封閉空間（地城或室內）時，環境音系統會提高低通濾波器 (LPF) 的係數，過濾掉環境中的高頻噪音（如雨聲與風鳴），模擬真實的物理隔音效果。
- **音訊資源緩存**：`soundcache.rs` 確保了高頻觸發的戰鬥音效（如揮劍、受傷）在內存中常駐，避免了 IO 延遲。

---
*本文件由分析任務自動生成預定留檔。*
