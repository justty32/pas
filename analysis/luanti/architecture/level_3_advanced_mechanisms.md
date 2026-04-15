# Level 3: 進階機制與模擬分析

## 1. 地圖生成系統 (Mapgen)
Luanti 的地圖生成是一個多階段的非同步過程：
- **核心架構**：`Mapgen` 類別 (`src/mapgen/mapgen.h`) 是所有生成器的基底類別。
- **生成器類型**：
    - `MapgenV7`: 目前最常用的通用生成器，支援複雜的山脈與生物群系。
    - `MapgenValleys`: 模擬河谷地形。
    - `MapgenFlat`: 用於測試或特殊遊戲模式的平坦地形。
- **組件系統**：
    - **生物群系 (Biomes)**：`BiomeManager` 根據溫度與濕度決定地表覆蓋。
    - **裝飾 (Decorations)**：用於生成樹木、草叢等。
    - **礦石 (Ores)**：處理地底資源的分布規律。
    - **結構 (Schematics)**：支援從外部檔案加載預製結構（如房屋）。

## 2. 網路通訊協定 (Network)
Luanti 實作了一套可靠的 UDP 傳輸層：
- **封包結構**：`NetworkPacket` (`src/network/networkpacket.h`) 封裝了指令碼 (Opcode) 與二進位數據。
- **處理器**：
    - **伺服器端**：`Server::ProcessPacket` 路由至 `ServerPacketHandler`。
    - **客戶端**：`Client::ProcessPacket` 路由至 `ClientPacketHandler`。
- **關鍵操作**：
    - `TOSERVER_PLAYERPOS`: 玩家位置同步。
    - `TOCLIENT_REMOVENODE` / `TOCLIENT_ADDNODE`: 地圖即時更新。
    - `TOSERVER_CHAT_MESSAGE`: 聊天訊息傳輸。

## 3. 模擬與同步
- **伺服器步進 (Server Step)**：`Server::step()` 控制全域模擬（如時間流逝、植物生長）。
- **實體同步**：`ServerEnvironment` 與 `ClientEnvironment` 之間透過物件 ID 同步實體狀態。
