# Session Log — analysis/opennefia-cpp

- **建立時間**: 2026-06-01
- **Agent**: Claude Code (Sonnet 4.6)

---

- 2026-06-01: 建立 analysis/opennefia-cpp/（Analysis 模式）。為 derived/opennefia-cpp/ Phase 0–4 完成後的事後分析：architecture/summary.md（架構總結 + 10 節：概覽/ECS/原型系統/序列化三件套/地圖邏輯/構建細節/目錄結構/三大反射難題解法/未來工作）+ html 導覽層（index.html + architecture.html + _shared.css）。
- 2026-06-02: 更新 analysis/opennefia-cpp/（F1–F3 完成後）。新增 §11 GDExtension 橋接層到 architecture/summary.md（技術棧補充/F1/F2/F3/gbind 目錄結構）。新建 tutorial/howto_extend_system.md（5 大擴充情境教學：Component/系統/地形/橋接到 Godot/新增 GDExtension 類別）。更新 html/index.html（F1–F3 完成橫幅 + 延伸 pipeline + nav-cards + 前端進度卡）、html/architecture.html（F1–F3 section + pitfall/solution + nav 連結）。新建 html/tutorial.html、html/frontend.html。

- 2026-06-02: 更新 analysis/opennefia-cpp（NPC AI + FOV + chase + 碰撞信號 + F4 完成後）。architecture/summary.md 更新 §1 完成表（F1–F4 全✅）、§5 AllComponents（加 NpcAiComponent）、§6 MapData（visible/explored + split save/load）、§8 目錄結構（加 systems/），新增 §12（NpcAiComponent 空型別坑/decltype(auto) fix/fov_system Bresenham LOS/npc 追蹤行為/碰撞信號/三層 FOV 渲染/F4 音效框架）。html/index.html 更新完成橫幅 + pipeline（加 NPC AI + FOV + F4）+ F4 卡片。html/architecture.html 加新 pitfall（EnTT 空型別 C2440）+ NPC AI/FOV/碰撞/F4 section。html/frontend.html 更新標題至 F1–F4。
- 2026-06-02: 更新 analysis/opennefia-cpp（NPC 警覺 + 戰鬥 + 物品 + 多樓層 + BSP 地城 + 存讀檔完成後）。architecture/summary.md：§1 加 6 新功能行、§5 AllComponents 補全 8 型別、§8 components/ 補全 7 個標頭、新增 §13（7 小節：NpcAiComponent 警覺升級/戰鬥系統/CombatStatsComponent/ItemComponent/多樓層/BSP/WorldStateComponent+存讀檔）。html/index.html：更新完成橫幅、pipeline 加 5 步驟、前端進度卡加 2 張。html/architecture.html：新增「G」section（警覺/戰鬥/物品/樓層/BSP/存讀檔）含 pitfall+solution。html/frontend.html：標題改 F1–F5、API 表擴充至 20 行（含 7 個 Signals）、迴路說明更新。
- 2026-06-02: 新增 tutorial/ 四篇教學（howto_add_npc_type / howto_add_item_type / howto_add_signal / howto_save_load_pattern），涵蓋新功能的實戰擴充方法；更新 html/tutorial.html（速查表加 4 欄、4 個新 section §6–§9）及 html/index.html（nav-card 描述更新為「九個實戰步驟」）。
- 2026-06-02: 更新 analysis/opennefia-cpp（F6 — GUI 實機 + 戰鬥 bug 修復 + 英雄辨識正規化完成後）。architecture/summary.md：§1 完成表加 F5/F6 兩行、測試數更新 40 cases/146 assertions、修 §13.7 步驟 3 的 hero 找回作法（proto_id→view<HeroComponent>）、新增 §14（雙重缺陷分析：exclude 排除法誤中物品＋EnTT view 反向迭代/行動機率閘門/HeroComponent 正向標記正規化/GUI 工具鏈/test_npc_combat 四案例）。html/index.html：完成橫幅改 F1–F6、pipeline 加 F5/F6 兩步、測試 badge 改 40/146、前端進度卡標題 F1–F6＋新增 F6 卡。html/architecture.html：修 load 後指標 pitfall 的 hero 找回敘述、新增 F6 section（三 pitfall＋二 solution＋二卡）。html/frontend.html：標題/nav/h1 改 F1–F6、修正 godot-cpp 版本box（4.4 Windows→4.6 Linux/godot-mono 4.6.3）、新增 F6 GUI section。
