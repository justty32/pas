# 深度模組分析：軌跡過渡 (Trajectory Transition)

## 1. 模組定位
`libs/transition/transition.cpp` 是一個插值器 (Interpolator)。它將一段連續的運動拆解成隨時間（0.0 到 1.0 的 progress）變化的離散坐標點。

## 2. 核心演算法

### A. 線性插值 (`linear`)
用於平滑身體位姿的轉變（如從前傾平滑過渡到水平）。直接使用進度比例分配差距：
```cpp
f.position.x = progress * dPx + _param.initialValue.position.x;
// ...包含位移與 Roll/Pitch/Yaw 角度
```

### B. 擺動相軌跡 (`swing`)
這是腿部在空氣中移動的路徑。與常見的拋物線不同，它採用了**三段式線性插值 (Piecewise Linear)**：
1.  **上升段 (`progress <= TRANSITION_PROGRESS_STEP1`)**：
    *   $X, Y$ 軸：根據總進度比例平滑移動。
    *   $Z$ 軸：快速從地面 `z1` 抬升至最高點 `z1 + offTheGround`。
2.  **平移段 (`progress <= TRANSITION_PROGRESS_STEP2`)**：
    *   $X, Y$ 軸：繼續平滑移動。
    *   $Z$ 軸：如果在平整地面，高度保持不變；若目標點與起點存在高度差，則在此段進行緩慢的 $Z$ 軸過渡。
3.  **下降段 (`progress > TRANSITION_PROGRESS_STEP2`)**：
    *   $X, Y$ 軸：最後的抵達。
    *   $Z$ 軸：從高點快速降落至目標點 `z2`。

## 3. 缺陷與改進建議
1.  **無窮大加速度衝擊**：由於採用分段折線，速度（一階導數）在轉折點是不連續的，這意味著加速度（二階導數）在這些點是無限大。這會轉化為對舵機齒輪的巨大機械衝擊力。
2.  **遷移建議**：在 ESP-IDF 重構時，強烈建議將 `swing` 函數重寫為**貝茲曲線 (Bézier curve)** 或 **三次樣條插值 (Cubic Spline)**，這能提供連續的速度與加速度曲線，讓機器狗動作更加絲滑，減少硬體磨損。
