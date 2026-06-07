# Godot 專案 / 模板 / 範例分析

> [← 回總索引 index.md](../index.md)。本檔收錄 Godot 引擎相關的綁定庫、模板、RPG 範本與官方範例。

| 專案名稱 | 類型 | 分析深度 | 狀態 | 核心內容摘要 |
| :--- | :--- | :--- | :--- | :--- |
| **godot-cpp** | 遊戲引擎組件 | Level 1 (Initial) | 分析中 | Godot 引擎的 C++ 綁定庫，用於開發 GDExtension。 |
| **Godot-GameTemplate** | 遊戲範本 (Godot 4.6) | 極高 (Level 1-6) + HTML | 已完成 (源碼核對 2026-05-25) | 高度解耦的俯視角射擊框架，含資源驅動 AI 與 Shader 轉場。已對照源碼核對 L1-6 並修正過時引用（movement_stats→movement、prepare_exit_event、波次來自 EnemyManager.wave_queue、兩套不一致 DamageType 枚舉、STEAM 存檔仍 TODO 等）。 |
| **godot-open-rpg** | 遊戲示範 (JRPG, Godot 4.6) | Level 1-4 + HTML | 分析中 (源碼核對 2026-05-25) | GDQuest 回合制 RPG 教學示範，Signal Bus + Resource 驅動設計。深化：兩階段回合制戰鬥（階段一選 action、階段二依 speed 遞迴執行）、FieldEvents/CombatEvents 事件匯流排（combat_triggered 為探索→戰鬥唯一切換）、.tres 原型模式與跨節點共享污染陷阱。發現 ATB/readiness 為未實裝設計遺跡、傷害公式未納 defense/元素。各子系統附 GDExtension 遷移點。 |
| **Freedom-Hunter** | 動作 RPG (Godot 4.3) | Level 1-2 | 分析中 | 仿 Monster Hunter 風格，ENet 多人、Entity 狀態機、怪物 AI 導航、銳利度武器系統。 |
| **BreadbinEngine** | 動作 RPG 框架 (Godot 4.0) | Level 1-2 | 分析中 | 仿 Dark Souls/BB 風格，CSV AttackTable 資料驅動武器招式，Inspector 可調 AI 機率，Hitbox 雙層碰撞設計。 |
| **Cogito** | FPS Immersive Sim 模板 (Godot 4.4) | Level 1 | 分析中 | 第一人稱沉浸模擬框架，組件式互動、Resource 驅動物品欄（Grid-based）、NPC 狀態機、Wieldable 基類介面、存讀檔場景管理。 |
| **Godot-Game-Template** | Godot UI/選單框架模板 (Godot 4.6, GDScript) | Level 1-3 | 分析中 | Maaack's 模板：2D/3D 通用的選單/無障礙框架（主選單、選項、暫停、製作名單、場景載入器）。邏輯層(`base/`)與繼承場景呈現層分離；4 個 autoload 提供場景載入/設定持久化/音樂/UI 音效。設定持久化三層（OptionControl→AppSettings→PlayerConfig，新增選項零程式碼）、autoload 自動接管場景樹音效、輸入重綁定雙模式（List/Tree + 衝突偵測 + 手把品牌感知）、SceneLoader 執行緒化非阻塞轉場。注意與 Godot-GameTemplate 為不同 repo。 |
| **TakinGodotTemplate** | Godot 起手模板 (Godot 4.4, GDScript) | Level 1-3 | 分析中 | Takin 模板（靈感自 Maaack）：精選 plugins + 最佳實踐骨架。16 個 autoload 為骨幹，將第三方 plugin 全部 Wrapper 化成 enum/Resource 驅動的型別安全介面，SignalBus 觀察者解耦，UI 採 Component-Driven(Builder 注入)，設定走 INI、存檔走 JSON。亮點：約定式自動註冊設定（節點名=列舉名+型別後綴）、反射式存檔（get_script_property_list 自動序列化 + §§§ 簽章 + 可選加密）、HACKS 文件化（Web 剪貼簿 JS 注入）。整合 scene_manager/resonate/Log/debug_menu 等。 |
| **godot-demo-projects** | Godot 官方範例集合 (Godot 4.6, GDScript/C#) | 編目 (Level 1-2) + 代表深入 | 分析中 | 官方 demo 集合（非單一架構）：13 分類、137 個 project.godot（含 mono/ C# 版）。level2 為核心分類目錄（2d=26/3d=32/gui=14/audio/compute/loading/misc/mobile/networking/viewport/xr…）+「主題→demo」速查表。深入剖析 4 個：2d/platformer、2d/finite_state_machine、compute/texture（render thread + Texture2DRD + ping-pong 水波）、networking/websocket_chat（poll 驅動 WS）。 |
| **godot-tactical-rpg** | 戰棋 RPG 範本 (Godot 4.3, GDScript) | Level 1-3 | 分析中 | ramaureirac SRPG 範本（3D 場地 + 2D billboard 角色）。Model/Module/Service 三層(類 MVC)，整局由 TacticsParticipantResource.stage(0~7) 一個整數隱式狀態機驅動。亮點：「射線格子化」（執行期把 Blender 方塊 mesh 轉 StaticBody3D，鄰接靠 RayCast3D 偵測、移動範圍 BFS flood-fill、高度差即跳躍門檻）、陣營制回合、完整敵人 AI 決策鏈、成品級四層樞紐攝影機（鍵鼠/手把雙模）。已知遺留：重複 service 檔、舊 .tres 用廢欄位 mp。 |
| **WuXiaAndJiangHu_Godot** | 武俠 MUD → Godot RPG 移植 (Godot 4.0, GDScript) | Level 1-2 + HTML | 分析中 (2026-06-01) | LPC MUD 武俠遊戲移植至 Godot 4.0 的進行中專案。三大架構：inherit/ 類別繼承層級（GameObject/Char/Room）、adm/daemons/ Daemon 系統（COMBAT_D/CHINESE_D 等）、feature/ Mixin 系統。核心：dbase dict（持久屬性）+ tmp_dbase dict（揮發屬性）的 LPC 相容層；AP/DP/PP 三段式概率戰鬥；10維屬性（str/int/con/dex/sta/spi/kar/per/cps/cor）+ 精力/氣血/內力；kungfu/skill/ 武學技能。大量功能仍在 TODO/注釋狀態，COMBAT_D.gd 有語法錯誤。 |
