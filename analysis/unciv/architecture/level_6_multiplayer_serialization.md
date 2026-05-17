# Level 6: 多人連線與數據同步機制 - Unciv

Unciv 的多人連線與存檔機制展現了其作為「跨平台且輕量化」遊戲的設計智慧。它放棄了複雜的即時 TCP/UDP 同步，轉而採用了一種基於 **非同步雲端同步 (PBEM style)** 的架構。

## 多人連線架構 (Online Multiplayer)
Unciv 的多人模式主要依賴於 **雲端儲存 (預設為 Dropbox)** 作為中繼伺服器：

1.  **非同步對戰 (Asynchronous Play)**:
    - 遊戲並非實時同步。當玩家 A 完成回合後，整個遊戲狀態會被序列化並上傳到雲端。
    - 玩家 B 會收到通知（在 Android 上透過 `MultiplayerTurnCheckWorker`），隨後下載最新的遊戲狀態。
    - **優點**: 極度節省流量，且玩家不需要同時在線，非常適合回合制 4X 遊戲。

2.  **同步機制 (`Multiplayer.kt`)**:
    - 透過 Kotlin 協程的 `flow` 與 `multiplayerGameUpdater` 定期輪詢伺服器。
    - 使用 `GameInfoPreview`（輕量級的 JSON 預覽）來檢查是否輪到該玩家，避免頻繁下載數 MB 的完整存檔。

3.  **身份驗證與安全**:
    - 每個玩家有一個唯一的 `playerId`。
    - 伺服器端透過簡單的 ID 匹配來決定誰有權限上傳覆蓋存檔。

## 序列化與數據持久化
Unciv 的所有存檔都是基於 **JSON** 格式的，並使用 Gzip 進行壓縮。

### 1. 數據模型 (`GameInfo`)
- `GameInfo` 是遊戲所有狀態的根節點。
- 透過標記介面 `IsPartOfGameInfoSerialization` 來識別所有需要序列化的類別。
- **反射驅動**: 利用 LibGDX 的 `Json` 類別，透過反射將物件樹轉換為 JSON 字串。

### 2. 序列化規則
為了確保跨版本、跨平台的穩定性，開發團隊設定了嚴格的規則：
- **禁止介面**: 欄位必須使用具體實體類（如 `ArrayList`），否則序列化器無法正確還原。
- **排除延遲加載**: 必須使用 `@delegate:Transient` 排除 `lazy` 屬性。
- **版本相容性**: `BackwardCompatibility` 模組負責將舊版的 JSON 數據遷移到新版格式（例如：單位 ID 的遷移、規則集引用修正）。

## 存檔流程範例
1.  **觸發**: 使用者點擊「結束回合」或自動存檔觸發。
2.  **序列化**: `Json().toJson(gameInfo)`。
3.  **壓縮**: 透過 `Gzip` 將 JSON 字串轉為位元組陣列。
4.  **存儲**: 寫入本地 `saves/` 目錄或透過 `MultiplayerServer` 上傳雲端。

## 總結
Unciv 的序列化設計非常直觀且易於調試（因為是人類可讀的 JSON）。雖然反射會帶來一定的性能開銷，但對於回合制遊戲來說，每回合幾百毫秒的序列化時間是可以接受的。這種設計也極大地方便了模組製作者，因為他們可以輕鬆地查看存檔內容來除錯。

## 最終結語
至此，我們完成了 Unciv 從入口點、核心規則引擎 (Unique DSL)、UI 渲染、AI 決策到數據同步的全方位剖析。該專案是 Kotlin 跨平台開發與 DSL 設計的典範。
