# 教學 04：動畫器與狀態機控制

在 OpenStarbound 中，實體的視覺表現由 `animator` 命名空間管理。這與 `NetworkedAnimator` 綁定，確保動畫在網路間同步。

## 1. 動畫器結構
一個實體的動畫由數個「部分 (Part)」與「狀態組 (State Group)」組成：
- **Part：** 如身體、手臂、燈光。
- **State Group：** 如 `powerState` (開/關), `moveState` (走/跑)。

## 2. 常用 API
- `animator.setAnimationState(group, state)`：切換狀態。
- `animator.setPartTag(part, tag, value)`：動態修改某部分的圖像（如更換顏色）。
- `animator.burstParticleEmitter(name)`：觸發一次粒子發射。
- `animator.playSound(name)`：播放音效。

## 3. 實作練習：互動開關
以下是一個物件（Object）的 Lua 腳本，實現了點擊切換動畫與發射粒子的邏輯：

```lua
function init()
  -- 初始設為關閉狀態
  self.active = false
  animator.setAnimationState("switch", "off")
end

function onInteraction(args)
  -- 翻轉狀態
  self.active = not self.active

  if self.active then
    animator.setAnimationState("switch", "on")
    animator.playSound("onSound")
    animator.burstParticleEmitter("sparks")
  else
    animator.setAnimationState("switch", "off")
    animator.playSound("offSound")
  end
end
```

## 4. 數據驅動與腳本的聯繫
C++ 負責維護狀態機與網路包的廣播，Lua 則負責決策何時切換狀態。這種解耦使得開發者可以在不修改 C++ 代碼的情況下，透過簡單的 Lua 修改來實現複雜的視覺效果。
