# Godot Sprite 家族架構分析 - Level 2 & 3

Godot 提供了多種方式來顯示 2D 圖像，每種方式針對不同的效能與開發需求。

## 1. Sprite2D (`scene/2d/sprite_2d.h`)
這是顯示圖像最直接的方式。
- **核心資料**：`Ref<Texture2D>`。
- **動畫機制**：支援 `hframes` 與 `vframes`。您可以透過修改 `frame` 屬性來手動切換顯示區域。
- **優點**：記憶體佔用極低，適合配合 `AnimationPlayer` 進行高度精確的動畫控制。
- **適用場景**：靜態背景、由 AnimationPlayer 驅動的角色動畫。

## 2. AnimatedSprite2D (`scene/2d/animated_sprite_2d.h`)
這是一個高階封裝的動畫節點。
- **核心資料**：`Ref<SpriteFrames>`。這是一個包含多個動畫序列（如 "walk", "idle"）的資源。
- **動畫機制**：自帶播放引擎，支援 `play()`, `stop()`, `speed_scale` 等。
- **優點**：配置簡單，不需要建立額外的 AnimationPlayer 即可運作。
- **適用場景**：簡單的 NPC 動作、粒子效果的序列幀。

## 3. Sprite3D 系列 (`scene/3d/sprite_3d.h`)
在 3D 空間中顯示 2D 貼圖。
- **核心機制**：在 3D 世界中建立一個平面並貼上 Texture。
- **關鍵特性**：**Billboard (看板) 模式**。可以設定精靈始終面向攝像機。
- **適用場景**：3D 遊戲中的 2D 樹木、草叢或懷舊風格的 3D 角色。

## 4. NinePatchRect (`scene/gui/nine_patch_rect.h`)
專為 UI 設計的精靈。
- **核心機制**：將貼圖切分為 9 塊。四個角保持原始大小，邊緣拉伸，中間填充。
- **適用場景**：各種大小不一的對話框、按鈕背景。

## 5. TextureRect (`scene/gui/texture_rect.h`)
屬於 GUI 系統的貼圖顯示節點。
- **核心機制**：繼承自 `Control`，支援錨點與容器佈局。
- **適用場景**：遊戲介面 (HUD)、圖示顯示。

---
*檔案位置：`scene/2d/sprite_2d.h`, `scene/2d/animated_sprite_2d.h`, `scene/3d/sprite_3d.h`*
