# LPC MUD → GDScript 移植狀態總覽

> 核對於 2026-06-01，Claude Code (Sonnet 4.6)

## 背景

WuXiaAndJiangHu_Godot 的原型是一套中文武俠 LPC MUD（類似「武林外傳」、「蓬萊碧落」風格的 MUD 伺服器）。  
作者正在將整套 MUD 邏輯移植到 Godot 4.0，形成單機/本機 RPG。

**移植策略**：
- 原始 `.c` 文件保留在原位（作為設計文件/參考）
- 同名 `.gd` 文件為翻譯版（同路徑，副檔名改為 `.gd`）
- `.gd` 中已完成的部分直接執行，未完成的部分保留 `# TODO` 或以 `#` 注釋

---

## 各模組移植進度

### 已完成（可執行）

| 模組 | 文件 | 移植完成部分 |
|---|---|---|
| dbase 核心 | `inherit/GameObject.gd` | `query()`/`set()`/`add()`/`query_temp()`/`set_temp()`/`delete()`/`delete_temp()` — 完整 |
| 型別相容層 | `inherit/GameObject.gd` | `mapp()`/`arrayp()`/`stringp()`/`intp()`/`undefinedp()` — 完整 |
| 移動系統基礎 | `inherit/GameObject.gd` | `weight`/`encumb`/`move()` — 部分（`move_object()` 仍為 stub） |
| 名字系統 | `inherit/Char.gd` | `set_name()`/`name()` — 完整 |
| 技能字典 | `inherit/Char.gd` | `set_skill()`/`delete_skill()`/`map_skill()`/`prepare_skill()` — 完整 |
| 忙碌狀態 | `inherit/Char.gd` | `start_busy()`/`is_busy()`/`continue_action()`/`remove_busy()` — 完整 |
| 師徒系統 | `inherit/Char.gd` | `create_family()`/`recruit_apprentice()` — 完整 |
| BBCode 顏色 | `inherit/GameObject.gd` | 全部 ANSI 色碼常數 → BBCode tag — 完整 |
| 戰鬥訊息模板 | `adm/daemons/COMBAT_D.gd` | `guard_msg[]`/`catch_hunt_msg[]`/`winner_msg[]` — 完整 |
| 傷害描述文字 | `adm/daemons/COMBAT_D.gd` | `damage_msg(damage, type)` — 完整（6 種傷害類型） |
| 血量狀態文字 | `adm/daemons/COMBAT_D.gd` | `eff_status_msg()`/`status_msg()` — 完整 |
| 戰鬥核心流程 | `adm/daemons/COMBAT_D.gd` | `do_attack()` — 大部分完成（語法錯誤存在） |
| 背包 UI | `inventory/` | GridBackpack/EquipmentSlots — 基本完成 |
| 物品資料庫 | `inventory/ItemDB.gd` | 基本完成 |
| 全域工具 | `Global.gd` | 存讀檔/目錄掃描/數字轉中文 — 完整 |

### 部分完成（有 TODO）

| 模組 | 文件 | 未完成部分 |
|---|---|---|
| 移動系統 | `inherit/GameObject.gd::move()` | `move_object()` 仍呼叫 `ob.free()` 而非正確移到容器 |
| Room reset | `inherit/Room.gd::reset()` | `make_inventory()` 邏輯被注釋 |
| Heart Beat | `inherit/Char.gd::heart_beat()` | 攻擊/狀態更新/掛機踢除 全部注釋 |
| short() | `inherit/Char.gd::short()` | 名稱顯示（稱號/門派/幫會前綴）全部注釋 |
| die()/unconcious() | `inherit/Char.gd` | 全部注釋 |
| 屬性查詢 | `inherit/Char.gd` | `query_str()`/`query_int()` 等全部注釋 |
| F_CONDITION | `inherit/Char.gd` | 狀態更新邏輯全部注釋 |
| F_DAMAGE | `inherit/Char.gd` | `receive_damage()`/`receive_wound()` 全部注釋 |
| F_FINANCE | `inherit/Char.gd` | `can_afford()`/`pay_money()` 全部注釋 |
| F_TEAM | `inherit/Char.gd` | 隊伍系統全部注釋 |
| Skill Daemon | `kungfu/skill/*.gd` | `power_point()`/`hit_ob()`/`double_attack()` 等核心方法未完成 |
| 技能 EXP | `inherit/Char.gd::improve_skill()` | 全部注釋 |

### 尚未翻譯（僅有 `.c` 原始版）

| 模組 | LPC 文件 |
|---|---|
| 自動存檔系統 | `adm/daemons/autosaved.c` |
| 頻道系統 | `adm/daemons/channeld.c` |
| 命令系統 | `adm/daemons/commandd.c` |
| 排程 | `adm/daemons/crond.c` |
| 道具功能 | `adm/daemons/disaster.c` |
| 地圖 | `adm/daemons/mapd.gd`（部分） |
| 所有 feature `.c` | `feature/*.c` |
| 命令 | `feature/command.c`/`move.c` 等 |

---

## 關鍵移植模式

### 1. dbase 字典取代 LPC 變數存取

LPC 原始碼中每個屬性是 `object->query("str")` 或 `ob->str`，移植為：

```gdscript
# LPC 原式
ob.query("str")          # → GDScript
dbase["str"]             # 或
query("str")             # 透過 GameObject.query()
```

### 2. LPC `call_other()` 取代為 GDScript 方法呼叫

```gdscript
# LPC: call_other(SKILL_D(skill), "query_action", me, ob)
# GDScript: 預計改為
var skill_d = load("res://kungfu/skill/" + skill + ".gd").new()
skill_d.query_action(me, ob)
```

### 3. `heart_beat()` 取代為 Godot Timer/`_process()`

LPC `set_heart_beat(1)` → 預計改為 Godot `Timer` 節點或 `_process(delta)` 計時

### 4. `call_out(func, delay)` 取代為 `await get_tree().create_timer(delay).timeout`

---

## 已知語法問題（COMBAT_D.gd）

`COMBAT_D.gd` 有多處 GDScript 語法錯誤，屬於 LPC→GDScript 翻譯不完整：

```gdscript
# 錯誤寫法（LPC 風格 elif）
elif: (damage < 20)       # 應為 elif damage < 20:

# 字典存取混用 {} 和 []
action["weapon"}          # 應為 action["weapon"]

# 括號不匹配
for userno in range(player.size() :   # 少了一個 )

# 使用未定義的宏
SKILL_USAGE_ATTACK        # 需要定義常數
```

這些問題說明 `COMBAT_D.gd` 目前**不可執行**，仍需進一步修正。
