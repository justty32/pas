# 大地圖 Tick 系統：全球模擬 (World Tick)

大地圖 (World Map) 是 RimWorld 的宏觀模擬層。

## 1. 執行順序與頻率
與本地地圖不同，大地圖 Tick 專注於高層數據：
1.  **`WorldComponent`**: 全局邏輯（如：任務到期、氣候變遷）。
2.  **`FactionManager`**: 勢力外交與領袖更新。
3.  **`WorldObjects`**: 處理商隊 (Caravan) 與定居點 (Settlement) 的行為。
4.  **`WorldPawns`**: 處理世界級虛擬人口（如：流亡者、囚犯）的生理狀態。

## 2. 虛擬人口系統 (`WorldPawns`)
*   **非實體化**: 存在於 `WorldPawns` 中的小人沒有 2D 座標。
*   **慢速 Tick**: 傷口癒合、免疫力等數值依然會更新，但頻率極低（通常為 TickRare 級別）。
*   **目的**: 為了在未來某個時刻（如：發出贖金信號）讓該小人重新「Spawn」回地圖。

## 3. 效能優化 (Optimization)
*   **數據導向**: 大地圖不執行複雜的物理碰撞與視覺渲染。
*   **時間分片**: 許多全局事件（如：海盜據點擴散）被安排在固定的 Tick 區間（如：整點、午夜），而不是分散在每一幀。

## 4. Mod 開發建議
*   **全局邏輯載體**: 使用 `WorldComponent` 來處理不依賴特定地圖的背景邏輯。
*   **世界物體監聽**: 透過遍歷 `Find.WorldObjects.AllWorldObjects` 來尋找玩家感興趣的地點或單位。

---
*由 Gemini CLI 分析 RimWorld.Planet.World 生成。*
