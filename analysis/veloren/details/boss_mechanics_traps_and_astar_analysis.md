# Boss 機制、地城陷阱與 A* 尋路優化深度分析 (Analysis)

## 1. 霜巨人 (FrostGigas) 戰鬥邏輯實作 (`server/agent/src/attack.rs`)
霜巨人的 AI 展示了 Veloren 複雜的戰鬥狀態管理。

### 核心代碼標註：
- **階段觸發閾值**：[Line 5324] `MINION_SUMMON_THRESHOLD = 1.0 / 8.0`。這定義了進入最後階段（召喚小怪）的血量百分比。
- **技能強制序列**：[Line 5336] `ActionStateICounters::CurrentAbility` 用於鎖定當前正在執行的連招，確保 Boss 的大招（如 Flashfreeze）具有完整且不可中斷的表現。
- **環境感知攻擊**：[Line 5344] `should_use_targeted_spikes` 檢查目標是否在深水中，展現了 AI 對地形介質（Fluid）的動態響應。

## 2. 地城陷阱的物理防護 (`common/src/terrain/block.rs`)
陷阱被設計為地城結構的一部分，具备極高的生存力。

### 核心代碼標註：
- **爆炸豁免**：[Line 565] `IronSpike` 與 `HaniwaTrap` 被列入 `explode_power -> None` 清單。這確保了地城的難度不會因為玩家攜帶大量炸藥而被「炸穿」。
- **固體碰撞判定**：[Line 708] 陷阱具備實體高度，這允許物理引擎計算玩家踩踏或撞擊陷阱時的位移與後續傷害。

## 3. A* 尋路系統的效能平衡 (`common/src/astar.rs`)
尋路算法針對大型伺服器環境進行了分散式優化。

### 核心技術：
- **非阻塞 Poll 模式**：[Line 135] `fn poll(&mut self, iters: usize, ...)`。尋路任務可以被拆解為每幀僅執行 `iters` 次迭代。這防止了 NPC 突然大規模尋路時導致的 CPU 尖峰。
- **最小堆優先隊列**：[Line 20] 透過實作 `Ord` 與 `PartialOrd` 的逆序比較，系統始終優先處理最有潛力的路徑，確保路徑的最優性與搜尋速度。

---
*本文件由分析任務自動生成預定留檔。*
