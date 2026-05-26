# Project Analysis Index

本索引追蹤 PAS 工作空間中所有 GitHub 專案的分析進度與內容摘要。

## 專案分析清單 (Projects List)

| 專案名稱 | 類型 | 分析深度 | 狀態 | 核心內容摘要 |
| :--- | :--- | :--- | :--- | :--- |
| **RimWorld** | 遊戲模組/引擎 | 高 (Architecture+Tutorial) | 已遷移 | 包含 AI、派系、地圖系統與豐富的 C# 開發教學。 |
| **Airships: CtS** | 飛行戰艦策略遊戲 (Java) | 高 (Level 1-3, C++重寫導向) | 分析中 | CFR 反編譯 game.jar→`projects/airships-cts/src/`（691 .java）；6 份子系統分析＋C++ 重寫路線圖。核心：確定性鎖步多人、Loadable 資料系統(71 型別)、雙層戰術 Combat/戰略 Campaign、評分式 AI、2D 法線光照渲染。 |
| **Skyrim Mod** | 遊戲模組 | 極高 (Classified) | 已遷移 | 深度分類分析 (NPC, Magic, 3D)，含 CommonLibSSE-NG。 |
| **Luanti (Minetest)**| 遊戲引擎 | 極高 (Level 1-12) | 已遷移 | 完整的引擎剖析、Lua API 綁定、渲染管線與 13 篇開發教學。 |
| **Godot** | 遊戲引擎 | 高 (GDExtension) | 已遷移 | 核心對象系統、物理、渲染分析，以及大量 GDExtension 教學。 |
| **Veloren** | 開源遊戲 (Rust)| 高 (Full System) | 已遷移 | 包含氣候、經濟、AI 行為與網絡同步的深度分析。 |
| **OpenNefia** | 遊戲實作 (C#) | 中 (ECS/IOC) | 已遷移 | 著重於 ECS 架構、依賴注入與 C++ 實作計畫。 |
| **MC Mod** | 遊戲模組 | 高 (Architecture) | 已遷移 | Millenaire-Reborn 的村莊邏輯、AI 目標系統與文化體系分析。 |
| **T-Engine** | 遊戲引擎 | 中 (ToME4) | 已遷移 | 引擎架構分析與 17 篇模組/插件開發教學。 |
| **OpenStartbound** | 遊戲引擎 | 中 (Universe) | 已遷移 | 宇宙生成、實體層級、渲染管線與 Lua 整合分析。 |
| **VCMI** | 遊戲引擎 | 中 (H3 Clone) | 已遷移 | 伺服器/客戶端架構、Lua 整合與 C++ 核心修改教學。 |
| **Taisei** | 遊戲引擎 | 中 (Bullet Hell) | 已遷移 | 渲染引擎、任務 DSL 與 C 語言開發範例。 |
| **ASC-HQ** | 遊戲引擎 | 基礎 (Core) | 已遷移 | 核心引擎、數據管理與子系統架構分析。 |
| **Slay-the-Robot** | 遊戲教學 | 基礎 (Tutorial) | 已遷移 | 提供新手與進階的開發引導指南。 |
| **Hy (Lisp-Python)** | 程式語言 | 教學導向 (對齊 Hy 1.3.0) | 已深化 (2026-05-26) | 教學 11 篇 + answers/。已 clone Hy 1.3.0 源碼並 venv 實測；發現舊教學基於 0.x（`&rest`/舊 import/2-arg if/`with-decorator`/`async-defn`/錯誤重整表/把 hyrule 當核心 等多項已壞），全部對齊 1.3 重寫。重點深化 macro：05 重寫＋新增 11 進階篇（編譯期模型、`require` 機制、reader macro、`hy.R`/`hy.I`、核心 vs hyrule 速查、0.x→1.x 遷移表）。answers 含「Hy 能否跑 c-mera」（不行，附 Hy-mera 自製骨架）。 |
| **LispC** | 編譯器 | 教學導向 | 已遷移 | Lisp-to-C 轉換邏輯、宏系統與 C 語言嵌入教學。 |
| **C-mera** | 代碼生成器 | 高 (Architecture) | 已遷移 | 基於 Lisp 的 C/C++/CUDA 生成器、AST 轉換與宏系統分析。 |
| **godot-cpp** | 遊戲引擎組件 | Level 1 (Initial) | 分析中 | Godot 引擎的 C++ 綁定庫，用於開發 GDExtension。 |
| **Godot-GameTemplate** | 遊戲範本 (Godot 4.6) | 極高 (Level 1-6) + HTML | 已完成 (源碼核對 2026-05-25) | 高度解耦的俯視角射擊框架，含資源驅動 AI 與 Shader 轉場。已對照源碼核對 L1-6 並修正過時引用（movement_stats→movement、prepare_exit_event、波次來自 EnemyManager.wave_queue、兩套不一致 DamageType 枚舉、STEAM 存檔仍 TODO 等）。 |
| **godot-open-rpg** | 遊戲示範 (JRPG, Godot 4.6) | Level 1-4 + HTML | 分析中 (源碼核對 2026-05-25) | GDQuest 回合制 RPG 教學示範，Signal Bus + Resource 驅動設計。深化：兩階段回合制戰鬥（階段一選 action、階段二依 speed 遞迴執行）、FieldEvents/CombatEvents 事件匯流排（combat_triggered 為探索→戰鬥唯一切換）、.tres 原型模式與跨節點共享污染陷阱。發現 ATB/readiness 為未實裝設計遺跡、傷害公式未納 defense/元素。各子系統附 GDExtension 遷移點。 |
| **Freedom-Hunter** | 動作 RPG (Godot 4.3) | Level 1-2 | 分析中 | 仿 Monster Hunter 風格，ENet 多人、Entity 狀態機、怪物 AI 導航、銳利度武器系統。 |
| **BreadbinEngine** | 動作 RPG 框架 (Godot 4.0) | Level 1-2 | 分析中 | 仿 Dark Souls/BB 風格，CSV AttackTable 資料驅動武器招式，Inspector 可調 AI 機率，Hitbox 雙層碰撞設計。 |
| **mh1j** | PS2 遊戲反組譯 (MIPS/C) | Level 1 | 分析中 | Monster Hunter 1 日版 (SLPM_654.95) 逐位元組匹配反組譯，MetroWerks 編譯器 + splat 拆分，主 ELF + 6 個 Overlay (含 DNAS 加密)。 |
| **Cogito** | FPS Immersive Sim 模板 (Godot 4.4) | Level 1 | 分析中 | 第一人稱沉浸模擬框架，組件式互動、Resource 驅動物品欄（Grid-based）、NPC 狀態機、Wieldable 基類介面、存讀檔場景管理。 |
| **pokeemerald** | GBA 遊戲反組譯 (C/ARM) | Level 1-2 | 分析中 | 寶可夢 Emerald pret 反組譯，雙Callback主迴圈、Task協程系統、Script bytecode直譯器、CB2狀態機戰鬥、多Controller架構、AI評分腳本、BoxPokemon XOR加密。 |
| **下一站江湖Ⅱ (jianghu-2)** | 武俠 RPG / Unity Mono Mod (BepInEx) | 中 (實戰 Mod 完成) | 分析中 | ilspycmd 反編譯 Assembly-CSharp（3004 cs，置於 `projects/jianghu-2/`）。BepInEx 注入環境踩坑全解：MonoBehaviour.Update 不 tick→Harmony patch `AppGame.Update`、plugin fake-null→`ReferenceEquals`、`PlayAnim` 回傳值說謊→`HaveAnim`。首個 mod「閒置 NPC 原地坐下(chusheng_sit)」已上線運作。含通用開發指南＋API 速查＋mod 原始碼（`analysis/jianghu-2/mod_src/`）。 |
| **hailo-media-library** | Hailo-15 AI 視覺 SoC SDK (C++) | Level 1-2 | 分析中 | Hailo-15 嵌入式視覺 SDK：hailo-media-library（Frontend Pipeline: LDC/DIS/EIS/Denoise/MultiResize/OSD/Encoder/PrivacyMask）+ hailo-postprocess（YOLO/NMS/Segmentation/OCR/Landmarks/CLIP）+ hailo-analytics（Stage-based 並行管線，30+ Stage 類型）。JSON Profile 配置系統、DMA Buffer Pool、GStreamer 1.20 整合、HailoRT 5.2。 |
| **Godot-Game-Template** | Godot UI/選單框架模板 (Godot 4.6, GDScript) | Level 1-3 | 分析中 | Maaack's 模板：2D/3D 通用的選單/無障礙框架（主選單、選項、暫停、製作名單、場景載入器）。邏輯層(`base/`)與繼承場景呈現層分離；4 個 autoload 提供場景載入/設定持久化/音樂/UI 音效。設定持久化三層（OptionControl→AppSettings→PlayerConfig，新增選項零程式碼）、autoload 自動接管場景樹音效、輸入重綁定雙模式（List/Tree + 衝突偵測 + 手把品牌感知）、SceneLoader 執行緒化非阻塞轉場。注意與 Godot-GameTemplate 為不同 repo。 |
| **TakinGodotTemplate** | Godot 起手模板 (Godot 4.4, GDScript) | Level 1-3 | 分析中 | Takin 模板（靈感自 Maaack）：精選 plugins + 最佳實踐骨架。16 個 autoload 為骨幹，將第三方 plugin 全部 Wrapper 化成 enum/Resource 驅動的型別安全介面，SignalBus 觀察者解耦，UI 採 Component-Driven(Builder 注入)，設定走 INI、存檔走 JSON。亮點：約定式自動註冊設定（節點名=列舉名+型別後綴）、反射式存檔（get_script_property_list 自動序列化 + §§§ 簽章 + 可選加密）、HACKS 文件化（Web 剪貼簿 JS 注入）。整合 scene_manager/resonate/Log/debug_menu 等。 |
| **godot-demo-projects** | Godot 官方範例集合 (Godot 4.6, GDScript/C#) | 編目 (Level 1-2) + 代表深入 | 分析中 | 官方 demo 集合（非單一架構）：13 分類、137 個 project.godot（含 mono/ C# 版）。level2 為核心分類目錄（2d=26/3d=32/gui=14/audio/compute/loading/misc/mobile/networking/viewport/xr…）+「主題→demo」速查表。深入剖析 4 個：2d/platformer、2d/finite_state_machine、compute/texture（render thread + Texture2DRD + ping-pong 水波）、networking/websocket_chat（poll 驅動 WS）。 |
| **godot-tactical-rpg** | 戰棋 RPG 範本 (Godot 4.3, GDScript) | Level 1-3 | 分析中 | ramaureirac SRPG 範本（3D 場地 + 2D billboard 角色）。Model/Module/Service 三層(類 MVC)，整局由 TacticsParticipantResource.stage(0~7) 一個整數隱式狀態機驅動。亮點：「射線格子化」（執行期把 Blender 方塊 mesh 轉 StaticBody3D，鄰接靠 RayCast3D 偵測、移動範圍 BFS flood-fill、高度差即跳躍門檻）、陣營制回合、完整敵人 AI 決策鏈、成品級四層樞紐攝影機（鍵鼠/手把雙模）。已知遺留：重複 service 檔、舊 .tres 用廢欄位 mp。 |

---
## 統計摘要
- **總計分析專案**：31 個
- **最近更新日期**: 2026-05-26
- **維護 Agent**: Gemini CLI / Claude Code

---
*註：此清單追蹤 Analysis 模式的分析專案。衍生小專案與 Patch 小專案分別存放於 `derived/` 與 `patches/`，尚無獨立索引。*
