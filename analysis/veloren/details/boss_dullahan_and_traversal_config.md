# Boss 機制、尋路配置與路徑拓撲深度分析 (Analysis)

## 1. 無頭騎士 (Dullahan) 戰鬥階段實作 (`server/agent/src/attack.rs`)
無頭騎士的 AI 是典型的「閾值驅動型」設計。

### 核心代碼標註：
- **血量步進計數器**：[Line 4540] 使用 `FCounters::ShockwaveThreshold` 動態計算下一個觸發點。每當血量降低一定比例（`SHOCKWAVE_THRESHOLD`），Boss 必定發動一次全屏或範圍技能。
- **動作恢復幀感知**：[Line 4549] 透過 `StageSection::Recover` 判定動作是否完成。這使得 Boss 能在技能結束後的下一幀立即更新觸發點，防止階段檢測卡死。
- **戰術距離矩陣**：[Line 4558-4564] 定義了三層防禦圈：追擊圈 (Chase)、遠程圈 (Shoot) 與近戰圈 (Melee)，這讓 Boss 能根據玩家的逃跑傾向動態切換戰術。

## 2. 尋路路徑與遍歷配置 (`common/src/path.rs`)
Veloren 的寻路不只是找最短路徑，而是尋找「代價最低路徑」。

### 關鍵設計：
- **遍歷配置 (`TraversalConfig`)**：[Line 85] 這是尋路系統的權重矩陣。它定義了 NPC 如何看待牆壁、斜坡與流體。
- **路徑狀態化 (`Route`)**：[Line 70] `Route` 封裝了生成的路徑與當前的索引 (`next_idx`)。這允許 NPC 在多個 Tick 之間平滑地沿著預定路徑移動，而無需每幀重算全路徑。
- **動態路徑修正**：[Line 4575] AI 在追擊時會調用 `path_toward_target` 並傳入 `Path::Partial` 標記，這在複雜地城環境下能保證 NPC 的移動不會因為路徑暫時阻塞而完全停止。

---
*本文件由分析任務自動生成預定留檔。*
