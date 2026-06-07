# JContainers SE (v4.2.9)

## 定位

SKSE plugin，為 Papyrus 補上**原生缺乏的資料結構與持久化儲存**。本身**沒有任何遊戲內容**——它是別的 mod 的依賴 library（MCM、複雜隨從、存檔大量狀態的 mod 常掛它）。

## 檔案結構

來源：`~/skyrim_mods/JContainers SE/Data/`

```
Data/
├── SKSE/Plugins/
│   ├── JContainers64.dll              ← native 核心（2.8 MB）
│   └── JCData/
│       ├── JContainers64.dll 的設定/資料
│       ├── InternalLuaScripts/        ← init.lua / jc.lua / api_for_lua.h
│       ├── lua/{jc,testing}/          ← 內建 Lua 模組
│       └── Domains/.force-install     ← domain 機制
├── scripts/                          ← 12 個 .pex（編譯後）
│   ├── JValue / JArray / JMap / JIntMap / JFormMap / JFormDB
│   ├── JDB / JString / JAtomic / JLua / JContainers
│   └── JContainers_DomainExample
└── scripts/source/                   ← 對應 12 個 .psc（完整 API 原始碼，可讀）
```

MO2 結構標準（`Data/` 在根，可直接平鋪安裝）。

## Papyrus API 面（按函式數排序）

來源：`~/skyrim_mods/JContainers SE/Data/scripts/source/*.psc`

| 模組 | 函式數 | 職責 |
|---|---|---|
| `JContainers_DomainExample.psc` | 235 | domain 機制示範（最完整的用法教學） |
| `JArray.psc` | 57 | 有序陣列（push/pop/insert/sort/find…） |
| `JValue.psc` | 40 | 所有容器共用的生命週期/序列化基礎 |
| `JFormDB.psc` | 26 | **per-Form 持久化 KV**（最實用） |
| `JMap` / `JIntMap` / `JFormMap` | 各 25 | string/int/Form 為鍵的 map |
| `JAtomic.psc` | 22 | 原子操作（thread-safe 計數等） |
| `JDB.psc` | 16 | 全域單例 DB 根（用路徑字串定址） |
| `JLua.psc` | 11 | 從 Papyrus 呼叫 Lua |
| `JContainers.psc` | 8 | 版本/維護 |
| `JString.psc` | 6 | 字串工具 |

### JFormDB —— 最值得 ModForge 注意的部分

來源：`JContainers SE/Data/scripts/source/JFormDB.psc:1` 起

它把「任意 Form → 一個 KV 樹」做成持久化儲存，用**路徑字串**定址：

```papyrus
Float function solveFlt(Form fKey, String path, Float default=0.0) global native
Bool  function solveFltSetter(Form fKey, String path, Float value, Bool createMissingKeys=false) global native
;; 同型還有 solveInt / solveStr / solveObj / solveForm
```

用法概念：`JFormDB.solveFltSetter(akActor, ".sofia.affinity", 50.0, true)`，即把「affinity=50」掛在某個 actor 上、跨存檔保存，不需要為每個狀態開一個 GlobalVariable。

### 生命週期注意

`JValue.psc` 開頭警告容器有生命週期管理（root/temporary），誤用會洩漏或被 GC。官方 wiki 連結就寫在 source 註解裡（`JValue.psc` 頂部）。

## 對 ModForge 的意義

ModForge 目前用 **GLOB（GlobalVariable）** 存 runtime 狀態（見 ModForge CLAUDE.md「已落地功能 → GlobalVariable」）。GLOB 適合少量旗標，但：

- 每個狀態要一個 record、ID 會膨脹；
- 無法做「per-actor 的狀態表」（例：每個 NPC 各自的好感度）。

JFormDB 正是補這個洞的方案。**但**它是 native 依賴——ModForge 若要產出依賴 JContainers 的 plugin，等於要求終端使用者安裝 JContainers。屬於「進階選項」，不該是預設。

→ 對照建議見 `others/modforge-relevance.md`。
