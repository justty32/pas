# TE4 模組開發教學系列 — 總覽

> 本系列教學以 T-Engine 4（版本 1.7.6）為基礎，帶你從零開始製作一個完整的 Roguelike 遊戲，或為 Tales of Maj'Eyal 製作 Addon。
>
> 建議按照編號順序閱讀。每個教學都會在上一個的基礎上繼續延伸。

---

## 三種開發路線

```
你想做什麼？
│
├─ 獨立遊戲（全新模組）────────────────── 教學 01 → 02 → 03 → 04 → 05
│
├─ ToME Addon（擴充內容）──────────────── 教學 01 → 06 → 07
│
└─ 引擎底層修改（C 層）──────────────── 先讀 architecture/engine_detail.md
```

---

## 教學清單

### 基礎：製作獨立遊戲

| 編號 | 狀態 | 標題 | 說明 |
|------|------|------|------|
| 01 | ✅ 完成 | [製作最簡單的地城遊戲（Hello Dungeon）](./01-hello-dungeon.md) | 最小可執行模組：地城探索 + NPC + 技能 + 角色創建 |
| 02 | 📝 TODO | 加入物品系統 | 揹包、裝備欄、消耗品、物品掉落 |
| 03 | 📝 TODO | 加入多個地區與世界地圖 | Zone 切換、WorldNPC、Wilderness |
| 04 | 📝 TODO | 加入任務系統 | Quest 定義、任務狀態追蹤、NPC 對話 |
| 05 | 📝 TODO | 加入進階 AI（戰術評分） | `improved_tactical`、`ai_tactic` 權重表 |

### 進階：ToME Addon 開發

| 編號 | 狀態 | 標題 | 說明 |
|------|------|------|------|
| 06 | ✅ 完成 | [製作第一個 Addon](./06-addon-dev.md) | Addon 結構、hooks、superload、overload |
| 07 | 📝 TODO | 為 ToME 新增職業與技能樹 | `newTalentType`、`newTalent`、Birth 描述符整合 |

---

## 前置知識

閱讀教學前，建議先了解以下背景：

- **Lua 基礎**：變數、函式、table、模組（`require`）
- **TE4 架構概覽**：閱讀 [`architecture/overview.md`](../overview.md)
- **引擎 Lua 層**：閱讀 [`architecture/lua_engine_detail.md`](../lua_engine_detail.md)（OOP 系統、Entity 生命週期）

---

## 開發環境設定

```bash
# 1. 生成 Makefile（Linux）
premake4 gmake

# 2. 編譯
make -C build

# 3. 執行（Debug 版，可看到 console 輸出）
./bin/Debug/t-engine

# 4. 你的模組放這裡
game/modules/<你的模組名稱>/
```

**推薦輔助工具**：
- `tome-addon-dev` addon：內建 `FSHelper` 與 Lua console（見 `architecture/game_detail.md` § 9）
- `LUA_CONSOLE` 按鍵（F1）：遊戲內執行任意 Lua 程式碼

---

## 快速參考：重要路徑

| 路徑 | 說明 |
|------|------|
| `game/engines/te4-1.7.6/engine/` | 引擎核心 Lua（不要直接修改）|
| `game/modules/<mod>/` | 你的模組根目錄 |
| `game/modules/<mod>/init.lua` | 模組元資料（必須）|
| `game/modules/<mod>/load.lua` | 系統初始化（必須）|
| `game/modules/<mod>/class/Game.lua` | 遊戲主控制器 |
| `game/modules/<mod>/data/zones/<name>/zone.lua` | 地區生成規則 |
| `game/addons/<addon>/` | Addon 根目錄（教學 06+）|

---

## 相關架構文件

| 文件 | 說明 |
|------|------|
| [`overview.md`](../overview.md) | 整體架構（C 層 + Lua 層 + 模組層）|
| [`lua_engine_detail.md`](../lua_engine_detail.md) | 引擎 Lua 詳細（OOP / Entity / Game Loop）|
| [`engine_detail.md`](../engine_detail.md) | C 子系統（SDL2 / OpenGL / PhysFS）|
| [`game_detail.md`](../game_detail.md) | game/ 目錄（loader / ToME 核心類別 / AI）|
| [`tome_content.md`](../tome_content.md) | ToME 內容層（NPC / 物品 / 任務 / 史料）|
| [`module_dev_guide.md`](../module_dev_guide.md) | 模組開發參考指南 |
