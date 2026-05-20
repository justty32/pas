# Editor 待辦功能

## 已完成

### A. 隨機 Rate/s（平滑插值）— 完成

`state.py` 加 `brush_rate_rand` / `brush_rate_min` / `brush_rate_max`；`app.py` 在 `_tick()` 透過 `_effective_rate(now)` 做 cos 過渡，每 1–2 秒（隨機）切下一段，UI 加 `Random Rate` 勾選框與 Min/Max 兩條滑條。
