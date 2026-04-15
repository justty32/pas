# Scene 動畫系統分析 - Level 2 & 3

## 1. 核心基底：AnimationMixer (`scene/animation/animation_mixer.h`)
在 Godot 4 中，`AnimationMixer` 是動畫播放的核心基底類別，它取代了舊版本中部分分散的邏輯，為 `AnimationPlayer` 與 `AnimationTree` 提供統一的混音基礎。

### 關鍵功能：
- **動畫庫管理 (`AnimationLibrary`)**：支援多個動畫庫的載入與管理，方便資源共享。
- **播放資訊追蹤 (`PlaybackInfo`)**：管理時間、權重、增量 (Delta) 與循環狀態。
- **快取機制 (`TrackCache`)**：針對動畫軌道 (Tracks) 進行快取優化，提升混合效能。
- **處理模式**：支援 `PHYSICS` (物理同步), `IDLE` (幀同步), `MANUAL` (手動觸發)。

## 2. 動畫播放器：AnimationPlayer (`scene/animation/animation_player.h`)
繼承自 `AnimationMixer`，主要用於線性的動畫播放、排隊與簡單的過渡。

### 特性：
- **自動播放與前進**：支援設定 `animation_next` 實現自動序列播放。
- **混合過渡**：提供 `default_blend_time` 與 `Blend` 結構處理動畫間的平滑切換。
- **捕捉機制 (`auto_capture`)**：支援從當前狀態動態過渡到動畫起始狀態。

## 3. 動畫圖：AnimationTree (`scene/animation/animation_tree.h`)
繼承自 `AnimationMixer`，用於實作複雜的動畫邏輯、狀態機與多向混合。

### 核心組件：
- **`AnimationNode`**：資源類別，定義了動畫邏輯節點（如 `AnimationNodeBlendTree`, `AnimationNodeStateMachine`）。
- **`NodeTimeInfo`**：在節點間傳遞動畫進度資訊。
- **混合圖 (Blend Tree)**：允許透過圖形化介面組合多個動畫源，並根據參數動態調整權重。

## 4. 補間動畫：Tween (`scene/animation/tween.h`)
這是一個獨立於 `AnimationMixer` 的系統，繼承自 `RefCounted`，專門用於程式碼驅動的屬性動畫。

### 體系結構：
- **`Tweener`**：具體的補間執行者，包含 `PropertyTweener`, `IntervalTweener`, `CallbackTweener`, `MethodTweener` 等。
- **過渡與緩動**：定義了豐富的 `TransitionType` (如 `TRANS_SINE`, `TRANS_ELASTIC`) 與 `EaseType` (如 `EASE_IN_OUT`)。
- **鏈式調用**：支援並行 (`parallel`) 或順序執行動畫序列。
- **綁定機制**：可以綁定到特定 `Node`，當節點銷毀時自動停止 `Tween`。

---
*檔案位置：`scene/animation/animation_mixer.h`, `scene/animation/animation_player.h`, `scene/animation/animation_tree.h`, `scene/animation/tween.h`*
