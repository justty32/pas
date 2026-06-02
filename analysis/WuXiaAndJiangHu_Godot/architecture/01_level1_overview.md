# Level 1：初始探索 — WuXiaAndJiangHu_Godot

> 核對於 2026-06-01，Claude Code (Sonnet 4.6)

## 專案基本資訊

| 項目 | 內容 |
|---|---|
| **名稱** | WuXiaAndJiangHu（武俠和江湖） |
| **引擎** | Godot 4.0 (config_version=5, features=4.0) |
| **語言** | GDScript（`.gd`）+ LPC 遺留碼（`.c`） |
| **主場景** | `res://objs/StageRoom.tscn` |
| **視窗解析度** | 1280×720，2D stretch 模式 |
| **類型** | 武俠 MUD 風 RPG（從 LPC MUD 移植至 Godot 的進行中專案） |

## README 概述

作者從 love2d 轉到 Godot 的開發筆記，主要記錄各種 Godot 開發技巧：
- RPGMaker 行走圖素材處理
- 自動地圖 TileSet 設定
- 存讀檔（File API）
- JSON 資料讀取
- 中國風時間顯示系統（干支紀年）
- 仿《放置江湖》/《太吾繪卷》UI 元件
- 武俠 MUD 的 Room 系統

## 目錄結構

```
WuXiaAndJiangHu_Godot/
├── addons/gdutils/     # GDScript 工具插件
├── adm/                # 管理模組（LPC MUD daemon 架構）
│   ├── daemons/        # 全域服務 daemon（COMBAT_D、CHINESE_D 等）
│   ├── etc/            # 設定
│   ├── log/            # 日誌
│   ├── obj/            # 物件工廠
│   ├── simul_efun/     # 模擬 LPC efun
│   └── single/         # 單例
├── assets/             # 美術資源（字型、圖片）
├── characters/         # 角色場景
├── clone/              # 物件克隆（工廠模式）
├── controls/           # UI 控制元件
├── d/                  # MUD 地圖區域
├── data/               # 持久化資料（玩家存檔、商店、掌門）
├── doc/                # 開發文件與截圖
├── feature/            # Feature Mixin 系統（F_ACTION, F_ATTACK 等）
├── inherit/            # 類別繼承層級（Base/GameObject/Char/Room）
├── inventory/          # 背包系統
├── kungfu/             # 武學系統
│   └── skill/          # 各技能定義（blade/claw/force 等）
├── lang/               # 多語系翻譯（zh_CN/en）
├── objs/               # Godot 場景物件（StageRoom/Character）
├── Stages/             # Stage 場景
├── uis/                # UI 場景
├── Global.gd           # Autoload：全域工具函式
├── Main.gd/Main.tscn   # 主場景（非啟動場景）
├── project.godot       # 專案設定
└── uml.drawio          # UML 設計圖
```

## 技術棧

| 技術 | 用途 |
|---|---|
| Godot 4.0 / GDScript | 主引擎與主要開發語言 |
| LPC 武俠 MUD 遺留碼 | 原始業務邏輯（大量以 `.c` 保存，`.gd` 為翻譯版） |
| gdutils plugin | GDScript 擴充工具 |
| 思源宋體 (siyuansong) | 中文字型 |
| TileMap | 地圖系統（設定 2D cell_size=32） |

## 入口點

- **主場景**：`project.godot:run/main_scene = "res://objs/StageRoom.tscn"`
- **Autoload**：
  - `Global` (`Global.gd`) — 全域工具（存讀檔、目錄掃描、數字轉中文等）
  - `CHINESE_D` (`adm/daemons/CHINESE_D.gd`) — 中文處理 daemon
  - `gdutils` (`addons/gdutils/__init__.gd`) — 工具插件入口

## 建構與執行

- 以 Godot 4.0 開啟 `project.godot` 即可執行
- 主場景：`objs/StageRoom.tscn`
- 無測試框架，無 CI 配置

## 重要備註

此專案屬於 **LPC MUD → Godot 移植的進行中工作**：
- `.c` 文件 = 原始 LPC MUD 程式碼（保留為參考/設計文件）
- `.gd` 文件 = GDScript 翻譯（許多核心邏輯仍在 `# TODO` 或被 `#` 注釋掉）
- 大量 LPC 慣用語（`query()`、`dbase`、`living()`）已移植至 GDScript 等價物
- 地圖資料 `data/` 含有帶 `.o` 或 `.json` 的 LPC 序列化存檔（真實武俠 MUD 資料）
