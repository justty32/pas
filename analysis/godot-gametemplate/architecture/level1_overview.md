# Level 1 Analysis: Godot Game Template 初始探索

## 1. 專案背景與技術棧
- **專案名稱**: Godot Game Template
- **作者**: nezvers
- **引擎版本**: Godot 4.6 (Forward Plus)
- **核心目標**: 提供一個結構化的俯視角射擊遊戲框架。
- **解析度**: 480x270 (Viewport), 1280x720 (Window Override)。

## 2. 核心架構模組
專案結構高度解耦，主要邏輯位於 `addons/` 中：
- `addons/top_down/`: 遊戲特定邏輯。
- `addons/great_games_library/`: 通用工具庫。

### 2.1 全域單例 (Autoloads)
- `SteamInit`: Steam API 初始化（選用）。
- `SoundManager`: 負責 2D/3D 音效播放。
- `Music`: 背景音樂管理。
- `Transition`: 處理場景切換特效。
- `PersistentData`: 儲存遊戲狀態與配置。

## 3. 重要子系統
- **資源傳輸系統 (Data Transmission)**: 使用 `AreaTransmitter` 與 `TransmissionResource` 處理傷害、拾取物與障礙物觸發，避免硬編碼。
- **實例化與對象池**: `InstanceResource` 封裝了實體生成邏輯，支援對象池優化性能。
- **節點引用管理**: `ReferenceNodeResource` 用於在不同場景間動態獲取節點引用。
- **AI 導航**: 結合 Godot 的 `AStarGrid2D` 與 `TileMap` 實作。

## 4. 快速入門導引
若要深入研究，建議優先查看以下路徑：
- **選單系統**: `addons/top_down/scenes/ui/screens/title.tscn`
- **關卡與房間**: `addons/top_down/scenes/levels/room_0.tscn`
- **角色基類**: `addons/top_down/scenes/actors/actor.tscn`
- **武器系統**: `addons/top_down/scenes/weapons/weapon.tscn`
- **彈幕系統**: `addons/top_down/scenes/projectiles/projectile.tscn`
