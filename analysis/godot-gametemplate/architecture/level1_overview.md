# Level 1 Analysis: Godot Game Template 初始探索

> 核對於 2026-05-25（Claude Code, Opus 4.7）：對照當前源碼複查。Godot 版本、autoload、解析度、入口場景皆與源碼一致；本次補強了腳本路徑與專案結構說明。

## 1. 專案背景與技術棧
- **專案名稱**: Godot Game Template（`project.godot:17` → `config/name="Game Template"`）
- **作者**: nezvers
- **引擎版本**: Godot 4.6 (Forward Plus)（`project.godot:19` → `config/features=PackedStringArray("4.6", "Forward Plus")`）
- **核心目標**: 提供一個結構化的俯視角射擊遊戲框架。
- **解析度**: 480x270 (Viewport), 1280x720 (Window Override)（`project.godot:32-35`）。
- **主場景（入口）**: `res://addons/top_down/scenes/ui/screens/boot_load.tscn`（`project.godot:18`，即 BootPreloader）。
- **物理圖層**: Environment / Player / Enemy / Navigation Obstacle（`project.godot:98-101`）。

## 2. 核心架構模組
專案結構高度解耦，主要邏輯位於 `addons/` 中：
- `addons/top_down/`: 遊戲特定邏輯（GDScript 集中於 `addons/top_down/scripts/`，場景於 `addons/top_down/scenes/`，資源 `.tres` 於 `addons/top_down/resources/`，著色器於 `addons/top_down/scripts/shaders/`）。
- `addons/great_games_library/`: 通用工具庫（可重用節點 `nodes/`、資源 `resources/`、靜態工具 `static/`、autoload `autoload/`）。
- `addons/kanban_tasks/`、`addons/resource_manager/`: 編輯器外掛（看板任務、資源管理），非執行期遊戲邏輯（`project.godot:45`）。

### 2.1 全域單例 (Autoloads)
（核對於 `project.godot:24-28`，名稱與註冊路徑皆一致）
- `SteamInit`: Steam API 初始化（選用）。腳本 `addons/great_games_library/autoload/SteamInit.gd`（純腳本 autoload）。
- `SoundManager`: 負責 2D/3D 音效播放。場景 `addons/top_down/scenes/autoloads/sound_manager.tscn`。
- `Music`: 背景音樂管理。場景 `addons/top_down/scenes/autoloads/music.tscn`。
- `Transition`: 處理場景切換特效。場景 `addons/top_down/scenes/autoloads/transition.tscn`（腳本 `scripts/game/TransitionManager.gd`）。
- `PersistentData`: 儲存遊戲狀態與配置。場景 `addons/top_down/scenes/autoloads/persistent_data.tscn`（腳本 `scripts/game/PersistentData.gd`）。

## 3. 重要子系統
- **資源傳輸系統 (Data Transmission)**: 使用 `AreaTransmitter2D` / `AreaReceiver2D` / `ShapeCastTransmitter2D` 搭配 `TransmissionResource` 處理傷害、拾取物與障礙物觸發，避免硬編碼（`addons/great_games_library/nodes/AreaTransmitter/`）。
- **實例化與對象池**: `InstanceResource` 封裝了實體生成邏輯，搭配 `PoolNode` 做對象池優化（`addons/great_games_library/resources/InstanceResource/InstanceResource.gd`、`PoolNode.gd`）。
- **節點引用管理**: `ReferenceNodeResource` 用於在不同場景間動態獲取節點引用（`addons/great_games_library/resources/ReferenceNodeResource/ReferenceNodeResource.gd`）。
- **AI 導航**: 結合 Godot 的 `AStarGrid2D`（封裝於 `resources/ValueResource/AstarGridResource.gd`）與 `TileMapLayer`（透過 `nodes/utility/TileAstargridObstacle.gd` 與 `nodes/Navigation/` 系列）實作。

## 4. 快速入門導引
若要深入研究，建議優先查看以下路徑（皆已核對存在）：
- **選單系統**: `addons/top_down/scenes/ui/screens/title.tscn`
- **關卡與房間**: `addons/top_down/scenes/levels/room_0.tscn`（另有 `room_start.tscn`、`room_template.tscn`）
- **角色基類**: `addons/top_down/scenes/actors/actor.tscn`
- **武器系統**: `addons/top_down/scenes/weapons/weapon.tscn`（腳本 `scripts/weapon_system/Weapon.gd`）
- **彈幕系統**: `addons/top_down/scenes/projectiles/projectile.tscn`（腳本 `scripts/weapon_system/projectile/Projectile2D.gd`）
- **Boss 範例**: `addons/top_down/scenes/actors/boss_big_jelly.tscn`（腳本 `scripts/actor/boss/BigJellyAi.gd`）
