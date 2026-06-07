# World Tech Level 分析 session log

- 辨識：m00nl1ght.WorldTechLevel（3414187030），透過 LunarFramework 載入（LunarLoader+Lunar/Components/*），無硬相依、DLC 全選用。
- 反編譯 WorldTechLevel.dll → projects/.../decompiled/（4741 行）；LunarFramework/HarmonyLib 不反編譯。
- 核心：開局選科技等級上限→過濾所有超標內容＋低科技替代。等級存 GameComponent_TechLevel，預設由 ScenPart_WorldTechLevel。
- 核心資料 def＝TechLevelConfigDef（defType+entries[{defName,techLevel,priority,ifModPresent...}]+alternatives+storyFilters），22 份 TechLevels_*.xml。
- ~40 個 Harmony patch 在各生成環節（BaseGen/Faction/Pawn/Map/Research/Memes/Ideo/Quest）查資料庫剔除超標。
- 結論：純 XML 擴充性極高——寫 TechLevelConfigDef 即可給任意 mod 內容標等級/替代（相容補丁零 C#）；改過濾演算法/攔截點才需 C#（且須懂 LunarFramework）。
- 產出 architecture/00_overview.md、details/extension_points.md、projects/.../SOURCE_POINTER.md。
