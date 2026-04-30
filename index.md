# Project Analysis Index

本索引追蹤 PAS 工作空間中所有 GitHub 專案的分析進度與內容摘要。

## 專案分析清單 (Projects List)

| 專案名稱 | 類型 | 分析深度 | 狀態 | 核心內容摘要 |
| :--- | :--- | :--- | :--- | :--- |
| **RimWorld** | 遊戲模組/引擎 | 高 (Architecture+Tutorial) | 已遷移 | 包含 AI、派系、地圖系統與豐富的 C# 開發教學。 |
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
| **Hy (Lisp-Python)** | 程式語言 | 教學導向 | 已遷移 | Lisp 與 Python 互操作性、元編程與非同步教學。 |
| **LispC** | 編譯器 | 教學導向 | 已遷移 | Lisp-to-C 轉換邏輯、宏系統與 C 語言嵌入教學。 |
| **C-mera** | 代碼生成器 | 高 (Architecture) | 已遷移 | 基於 Lisp 的 C/C++/CUDA 生成器、AST 轉換與宏系統分析。 |
| **godot-cpp** | 遊戲引擎組件 | Level 1 (Initial) | 分析中 | Godot 引擎的 C++ 綁定庫，用於開發 GDExtension。 |
| **Godot-GameTemplate** | 遊戲範本 | 極高 (Level 1-6) | 已完成 | 高度解耦的俯視角射擊框架，含資源驅動 AI 與 Shader 轉場。 |
| **godot-open-rpg** | 遊戲示範 (JRPG) | Level 1-2 | 分析中 | GDQuest 出品 Godot 4.5 回合制 RPG 教學示範，Signal Bus + Resource 驅動設計。 |
| **Freedom-Hunter** | 動作 RPG (Godot 4.3) | Level 1-2 | 分析中 | 仿 Monster Hunter 風格，ENet 多人、Entity 狀態機、怪物 AI 導航、銳利度武器系統。 |
| **BreadbinEngine** | 動作 RPG 框架 (Godot 4.0) | Level 1-2 | 分析中 | 仿 Dark Souls/BB 風格，CSV AttackTable 資料驅動武器招式，Inspector 可調 AI 機率，Hitbox 雙層碰撞設計。 |
| **mh1j** | PS2 遊戲反組譯 (MIPS/C) | Level 1 | 分析中 | Monster Hunter 1 日版 (SLPM_654.95) 逐位元組匹配反組譯，MetroWerks 編譯器 + splat 拆分，主 ELF + 6 個 Overlay (含 DNAS 加密)。 |
| **Cogito** | FPS Immersive Sim 模板 (Godot 4.4) | Level 1 | 分析中 | 第一人稱沉浸模擬框架，組件式互動、Resource 驅動物品欄（Grid-based）、NPC 狀態機、Wieldable 基類介面、存讀檔場景管理。 |
| **pokeemerald** | GBA 遊戲反組譯 (C/ARM) | Level 1-2 | 分析中 | 寶可夢 Emerald pret 反組譯，雙Callback主迴圈、Task協程系統、Script bytecode直譯器、CB2狀態機戰鬥、多Controller架構、AI評分腳本、BoxPokemon XOR加密。 |

---
## 統計摘要
- **總計分析專案**：24 個
- **最近更新日期**: 2026-04-30
- **維護 Agent**: Gemini CLI

---
*註：此清單僅包含已遷移至 `analysis/` 目錄並符合 GitHub 專案分析規範的項目。*
