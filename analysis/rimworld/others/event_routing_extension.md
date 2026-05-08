# 進階哨站：事件重定向與轉運站設計 (Event Routing & Hubs)

將哨站功能擴展為「全球事件攔截器」，玩家可以決定特定的對外交互事件發生在哪個地點。這不僅增加了策略深度，也讓玩家能更好地保護主基地的隱私與安全。

## 1. 事件攔截機制 (Event Interception)

當一個全球性或針對玩家的良性/中性事件觸發時，系統會檢查玩家是否設置了「轉運站」。

*   **可重定向事件類型**:
    *   **訪客 (Visitors)**: 其他派系的旅行者。
    *   **貿易商隊 (Caravans)**: 友好的貿易隊伍。
    *   **求救/流浪者加入 (Wanderer Joins / Refugee Pods)**: 隨機加入的人員。
    *   **特殊請求 (Quests/Requests)**: 某些需要面對面交談的任務。

## 2. 轉運站類型與功能

玩家可以透過採樣期的建設，將哨站定義為不同類型的「外交窗口」。

### A. 邊境貿易站 (Frontier Trading Hub)
*   **機制**: 封存一個擁有豪華客房和大型倉庫的地圖。
*   **效果**: 所有貿易商隊優先抵達此處。
*   **優點**: 主基地不需要預留大量的物資囤積區，也不用擔心商隊的小人在家裡亂晃（或死在家裡引發外交危機）。

### B. 移民接收中心 (Recruitment & Immigration Center)
*   **機制**: 封存一個擁有基礎生活設施和審查室的地圖。
*   **效果**: 隨機加入的流浪者或求救者會首先出現在這裡。
*   **優點**: 玩家可以在這裡對新成員進行「背景調查」（技能檢查、特質篩選），合格後再調往主基地，不合格的則直接留在哨站勞動。

### C. 外交大使館 (Diplomatic Embassy)
*   **機制**: 封存一個具備極高「美觀度」與「娛樂價值」的地圖。
*   **效果**: 重要的訪客或派系領袖會選擇在此停留。
*   **優點**: 提供更高的外交加成，並能更容易觸發「結盟」或「特殊交易」。

## 3. 技術實作邏輯 (C# Implementation)

使用 Harmony Patch 攔截 `IncidentWorker` 的目標選擇。

```csharp
// 偽代碼：事件目標分流
[HarmonyPatch(typeof(IncidentWorker), "TryExecute")]
public static class RedirectEventPatch {
    static void Prefix(ref IncidentParms parms) {
        if (parms.target is Map mainMap) {
            var hub = Find.WorldObjects.AllWorldObjects
                        .OfType<OutpostWorldObject>()
                        .FirstOrDefault(x => x.IsActiveHubFor(parms.def));
            
            if (hub != null) {
                parms.target = hub; // 將事件目標改為哨站
            }
        }
    }
}
```

## 4. 封存狀態下的交互處理

由於哨站是封存的（沒有 Map），事件發生時有兩種處理方式：

1.  **自動結算 (Abstract Interaction)**:
    *   貿易商抵達後，玩家直接透過「遠程通訊」與其交易（物資直接進入哨站庫存）。
    *   訪客離開後，根據哨站的款待等級自動結算友好度。
2.  **臨時展開 (Temporary Unfold)**:
    *   若玩家想親自管理（如：手動招募某個訪客），可以點擊「進入轉運站」，系統暫時生成地圖供玩家操作。

## 5. 戰略意義

1.  **安全隔離**: 避免帶病毒的流浪者或懷有惡意的訪客直接進入主基地核心區。
2.  **效能管理**: 大量商隊和訪客會消耗大量 CPU 計算路徑與社交，將他們導向哨站可以顯著提升主基地的順暢度。
3.  **地緣佈局**: 玩家可以根據地理位置設置貿易站，吸引特定區域的派系前來。

---
*文件路徑: analysis/rimworld/others/event_routing_extension.md*
