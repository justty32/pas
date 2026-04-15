# 基地生成與程序化內容 (BaseGen)

RimWorld 使用符號解析系統來構建複雜地圖。

## 1. 核心類別：`RimWorld.BaseGen.BaseGen`
這是一個管理生成過程的類別，它使用一個符號棧 (`symbolStack`) 來進行遞歸生成。

## 2. 符號解析器：`SymbolResolver`
*   **頂層符號**: `settlement` (基地整體)。
*   **中間層**: `basePart_outdoors`, `basePart_indoors` (戶外、室內分塊)。
*   **底層實體**: `edgeWalls` (畫牆)、`floor` (鋪地)、`pawnGroup` (刷人)。

## 3. 生成流程
1.  **世界定位**: `WorldGenStep_Settlements` 找到 Tile。
2.  **地圖初始化**: 玩家抵達時，呼叫 `SymbolResolver_Settlement.Resolve()`。
3.  **解析過程**: 將高層抽象符號 (`basePart`) 轉為低層實體 (`Thing`)，直到填滿指定的矩形區域。

---
*由 Gemini CLI 分析 RimWorld.BaseGen 命名空間生成。*
