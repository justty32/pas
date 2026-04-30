# 架構藍圖：使用 COGITO 復刻「上古卷軸：天際 (Skyrim)」

復刻 Skyrim 是一個極具野心的目標。COGITO 作為一個第一人稱沉浸模擬框架，已經為您打下了堅實的基礎（如：物品欄、基礎任務、物理互動、屬性系統）。然而，要達到 Skyrim 的深度，您必須對現有系統進行大規模的擴充。

以下是將 COGITO 升級為 Skyrim-like 引擎的**六大核心架構路線圖**：

---

## 1. 開放世界與地圖流式加載 (World Streaming)
*Skyrim 的世界是無縫探索的，只有進入地牢或城市才會讀取。*
- **現狀**：COGITO 依賴 `CogitoSceneManager` 進行單一場景的切換與全域存檔。
- **升級方向**：
  - 導入 **區塊化 (Chunking)** 架構。參考 `tutorial/open_world_architecture.md`。
  - 使用 **Terrain3D** 處理廣袤的地形。
  - **LOD 與距離剔除**：大量依賴 `VisibilityRange` 與自動 Mesh LOD 來管理滿地花草與遠處建築。

---

## 2. 輻射 AI 與排程系統 (Radiant AI & Scheduling)
*Skyrim 的 NPC 早上工作、晚上去酒館、半夜睡覺。*
- **現狀**：COGITO 的 `NPC_State_Machine` 只有簡單的巡邏 (`patrol`)、追擊 (`chase`) 與閒置 (`idle`)。
- **升級方向**：
  - 建立一個全域的 **時間與日夜循環系統 (Time System)**。
  - 為 NPC 實作 `ScheduleComponent`：根據遊戲內的時間，動態切換狀態機的目標（例如：8:00 切換至 `npc_state_work.gd`，20:00 切換至 `npc_state_relax.gd`）。
  - **虛擬模擬 (Virtual Simulation)**：當 NPC 在載入的 Chunk 之外時，他們不應進行真實物理移動，而是由排程系統計算他們「應該在哪裡」，等玩家靠近載入 Chunk 時，直接將 NPC 放置於目標座標。

---

## 3. RPG 角色成長與技能樹 (Character Progression)
*Skyrim 的特色是「做什麼就升級什麼」（如：一直被打就升級重甲）。*
- **現狀**：COGITO 有屬性系統 (`CogitoAttribute` - 血、耐、理智)，但沒有經驗值與技能樹。
- **升級方向**：
  - 建立 `SkillManager` (Autoload)。
  - 在各種動作的觸發點注入經驗值：
    - 在武器命中時 (`wieldable_sword.gd`) 呼叫 `SkillManager.add_xp("one_handed", 10)`。
    - 在受到傷害時 (`HitboxComponent`) 呼叫 `SkillManager.add_xp("light_armor", 5)`。
  - 實作技能樹 UI，並透過全域變數或 `CogitoGlobals` 中的 Modifier 來影響武器傷害倍率。

---

## 4. 紙娃娃裝備系統 (Paper Doll & Equipping)
*Skyrim 可以換頭盔、胸甲、手套、鞋子，且裝備會實際顯示在角色身上。*
- **現狀**：COGITO 的武器是 `Wieldable`，主要顯示在第一人稱視角（掛在相機下），沒有第三人稱的全身裝備槽。
- **升級方向**：
  - 改造玩家的節點結構，加入一個完整的 3D 骨架模型（即使在第一人稱下不可見，但能投射陰影，或用於第三人稱切換）。
  - 擴充 `CogitoInventory`，加入特定的「裝備槽」(Equipment Slots：頭、胸、手、腳、戒指)。
  - 撰寫 `EquipmentManager`：當玩家裝備一把鐵劍或穿上鐵甲時，讀取該物品的 Mesh，並將其附加 (Attach) 到玩家 3D 骨架對應的 `BoneAttachment3D` 上。

---

## 5. 魔法與呼喊系統 (Magic & Shouts)
*一手拿劍，一手放魔法，或是使用獨立冷卻的龍吼。*
- **現狀**：COGITO 允許雙持 (Dual Wielding) 但主要針對實體武器。
- **升級方向**：
  - 新增 `MagickaAttribute` (魔力屬性，繼承自 `CogitoAttribute`)。
  - 將「法術」實作為特殊的 `WieldableItemPD`。當使用 (`action_primary`) 時，消耗 Magicka，並實例化一個帶有 `HitboxComponent` 的投射物 (`CogitoProjectile`) 或施放一條射線 (RayCast) 作為持續性法術 (如：火舌術)。
  - 對於「龍吼 (Shout)」，實作一個獨立的輸入按鍵 (`Z` 鍵)，並配備獨立的冷卻計時器與全域變數管理當前裝備的龍吼。

---

## 6. 深度對話與任務分支 (Branching Dialogue)
*Skyrim 依賴對話來接任務、買賣、說服。*
- **現狀**：COGITO 已經整合了 Dialogic / Dialogue Nodes，任務系統也具備基礎的計數與狀態。
- **升級方向**：
  - 這是最容易達成的部分！Dialogic 已經完全具備處理複雜網狀對話的能力。
  - 您只需要在 Dialogic 的 Timeline 中，透過腳本呼叫來觸發 COGITO 的任務狀態更新：
    `[call node="CogitoQuestManager" method="start_quest" args={"quest_id": "main_quest_01"}]`
  - 實作「說服 (Persuasion)」：在 Dialogic 中讀取玩家的 `Speechcraft` 技能等級，決定選項是否成功。

---

## 總結：開發順序建議

如果您的終極目標是復刻 Skyrim，請**不要一開始就想做開放世界**。
建議的開發迭代順序：
1. **地牢核心 (Dungeon Core)**：先在一個封閉的室內場景（如一個遺跡），實作劍盾戰鬥、簡單魔法、血量/耐力/魔力消耗，以及搜刮箱子。這完全在 COGITO 現有能力範圍內。
2. **村莊核心 (Village Core)**：實作對話接任務、商店買賣，以及嘗試為一個 NPC 寫一個「白天打鐵、晚上睡覺」的排程狀態機。
3. **裝備升級 (RPG Core)**：實作紙娃娃系統，讓換上不同盔甲能改變外觀與防禦力屬性。
4. **世界縫合 (Open World)**：最後，當這些核心機制都穩定後，再著手研究 Chunking 與 Terrain3D，將地牢與村莊放置到無縫的廣大世界中。
