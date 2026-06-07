# PapyrusUtil SE/AE (v4.6)

## 定位

SKSE plugin，與 JContainers 同類——都是「為 Papyrus 補資料儲存與工具函式」的依賴 library，本身**沒有任何遊戲內容**。但兩者走的是不同路線：

- **JContainers**：容器物件（JArray/JMap/JFormMap…）+ 路徑字串定址 + 容器生命週期管理。功能強、概念重，使用者要理解 root/temporary 容器與 GC。
- **PapyrusUtil**：**輕量、扁平的 KV**。不需要建立或管理任何容器物件——直接以 `(Form, key 字串)` 或 `(json 檔名, key 字串)` 為複合鍵存取 int/float/form/string 與 list。入門成本極低。

readme 一句話定位（`Readme - PapyrusUtilSE.txt` Description 段）：

> SKSE plugin that allows you to save any amount of int, float, form and string values on any form or globally from papyrus scripts. Also supports lists. These values can be accessed from any mod allowing easy dynamic compatibility.

「any mod can access」是它的設計哲學：所有 mod 共用同一個全域命名空間，靠 key 前綴（如 `rnd_hungervalue`）避免撞名，達成**零硬依賴的跨 mod 相容**（`StorageUtil.psc:37-58` 的註解詳述此用法）。

三大支柱：

| 支柱 | 鍵的形態 | 持久化位置 |
|---|---|---|
| **StorageUtil** | `(Form, key)` 或全域 `(none, key)` | 存檔內（co-save） |
| **JsonUtil** | `(json 檔名, key)` | **外部 .json 檔**（獨立於存檔，可遊戲外編輯） |
| **PapyrusUtil** | 無狀態 | 純陣列/字串/數值工具，無持久化 |

## 檔案結構

來源：`~/skyrim_mods/PapyrusUtil/`

| 路徑 | 內容 |
|---|---|
| `SKSE/Plugins/PapyrusUtil.dll` | native 核心（約 1.4 MB） |
| `Scripts/*.pex` | 6 個編譯後腳本（ActorUtil / JsonUtil / MiscUtil / ObjectUtil / PapyrusUtil / StorageUtil） |
| `Scripts/Source/*.psc` | **完整 API 原始碼**（同名 6 份，可讀） |
| `Source/Scripts/*.psc` | 同上的 CK source 路徑複本（v3.41 起複製到 `/source/scripts`） |
| `Readme - PapyrusUtilSE.txt` | 說明文件 |

依賴（readme Requirements 段）：SKSE64 SE/AE 2.2.6+、Skyrim SE/AE 1.6.1170、**Address Library for SKSE Plugins**（Nexus #32444）。

JsonUtil 的外部檔起始目錄是 `data/skse/plugins/StorageUtilData/`，檔名可含相對路徑與省略副檔名（`JsonUtil.psc:12-21`）。

## Papyrus API 面（按函式數排序）

來源：`~/skyrim_mods/PapyrusUtil/Scripts/Source/*.psc`

| 模組 | 函式數 | 職責 |
|---|---|---|
| `StorageUtil.psc` | 286 | 在 form 上或全域存 int/float/form/string 與 list，用 form+key 取回（核心） |
| `JsonUtil.psc` | 138 | 同 StorageUtil 但存到**外部 .json 檔**，可遊戲外編輯、獨立於存檔 |
| `PapyrusUtil.psc` | 101 | 版本檢查 + 陣列/字串/數值工具（無狀態） |
| `MiscUtil.psc` | 23 | TFC 飛行鏡頭、TM 選單開關、cell 掃描、檔案 IO、印 console 等雜項 |
| `ActorUtil.psc` | 6 | actor 的 AI package override 堆疊 |
| `ObjectUtil.psc` | 8 | 替換選定物件的動畫（**SE 已停用**，見下） |

函式數之所以龐大，是因為每個操作都對 int/float/string/Form **四型各一份**，再乘上 value 與 list 兩種形態、以及一系列衍生（Has/Unset/Pluck/Adjust/Count…）。實際「概念」遠少於函式數。

### StorageUtil —— 核心 `(Form, key)` KV

複合鍵的設計集中在前 4 個型別組（`StorageUtil.psc:77-115`）：

```papyrus
int    function SetIntValue(Form ObjKey, string KeyName, int value) global native      ; :77
float  function SetFloatValue(Form ObjKey, string KeyName, float value) global native   ; :78
string function SetStringValue(Form ObjKey, string KeyName, string value) global native ; :79
Form   function SetFormValue(Form ObjKey, string KeyName, Form value) global native     ; :80

int    function GetIntValue(Form ObjKey, string KeyName, int missing = 0) global native ; :112
Form   function GetFormValue(Form ObjKey, string KeyName, Form missing = none) global native ; :115
```

關鍵語意（`StorageUtil.psc:70-114` 註解）：

- `ObjKey` 設 `none` 即「全域」儲存；給任意 `Form` 即「掛在該 form 上」——這就是 per-form 狀態表的入口。
- key（`KeyName`）大小寫不敏感；四個型別各自獨立命名空間（`SetIntValue(none,"abc",1)` 與 `SetFloatValue(none,"abc",2.0)` 互不影響，`:27-35`）。
- `Get*` 帶 `missing` 預設值，缺鍵時回傳它。
- form 被刪除時，掛在其上的值會在下次存檔時清掉（`:11-13`）。

list 版以同樣的 `(Form, key)` 複合鍵指向一個有序串列（`StorageUtil.psc:150-284`）：

```papyrus
int  function FormListAdd(Form ObjKey, string KeyName, Form value, bool allowDuplicate = true) global native ; :153
Form function FormListGet(Form ObjKey, string KeyName, int index) global native                              ; :165
int  function FormListCount(Form ObjKey, string KeyName) global native                                       ; :284
int  function IntListAdd(Form ObjKey, string KeyName, int value, bool allowDuplicate = true) global native   ; :150
```

衍生操作齊全：`Pluck*`（取出即刪，`:124-127`）、`Adjust*`（±現值，`:137-138`）、`*ListShift/*ListPop`（頭尾取出，`:198-211`）、`*ListSort/*ListSlice/*ListToArray`（`:327-388`）、`Count*ValuePrefix` / `Clear*ValuePrefix`（按 key 前綴批次統計或清除，`:424-492`）。另有 `FileXxx` 一整組（`:568-806`）已 **DEPRECATED**，內部全部轉呼 `JsonUtil` 寫到共用的 `../StorageUtil.json`。

### JsonUtil —— 把命名空間換成「外部 json 檔名」

函式表面與 StorageUtil 幾乎一一對應，唯一差別是把首參數從 `Form ObjKey` 換成 `string FileName`（`JsonUtil.psc:7-11` 明說「work in exactly the same way」）：

```papyrus
int  function SetIntValue(string FileName, string KeyName, int value) global native        ; :56
Form function SetFormValue(string FileName, string KeyName, form value) global native       ; :59
int  function GetIntValue(string FileName, string KeyName, int missing = 0) global native   ; :61
int  function FormListAdd(string FileName, string KeyName, Form value, bool allowDuplicate = true) global native ; :79
```

檔案生命週期函式（`JsonUtil.psc:33-53`）：

```papyrus
bool function Load(string FileName) global native                              ; :33
bool function Save(string FileName, bool minify = false) global native         ; :34
bool function Unload(string FileName, bool saveChanges = true, ...) global native ; :35
bool function IsGood(string FileName) global native                            ; :40  (parser 無誤?)
string function GetErrors(string FileName) global native                       ; :42  (格式化錯誤字串)
```

一般情況**不必手動 Load/Save**：玩家存檔時所有被改過的 json 自動寫回（`:23-28`）。

JsonUtil 還有 StorageUtil 沒有的**任意路徑存取**（v3.3 加入，`:175-228`），可讀寫任意 json 結構，適合自訂格式的資料表：

```papyrus
int  function GetPathIntValue(string FileName, string Path, int missing = 0) global native ; :190
function SetPathIntValue(string FileName, string Path, int value) global native            ; :183
int[] function PathIntElements(string FileName, string Path, int invalidType = 0) global native ; :198
```

範例（`:177-180`）：對 `{ "foo": { "bar": [3,10,7] } }` 呼叫 `GetPathIntValue("filename.json", ".foo.bar[1]")` 回傳 `10`。

### PapyrusUtil —— 版本檢查 + 純陣列/字串/數值工具

無持久化，全是把 Papyrus 缺的陣列/字串操作補成 native：

```papyrus
int function GetVersion() global native        ; :4   (4.6 回 46 —— 來自 DLL)
int function GetScriptVersion() global         ; :7   (回 46 —— 來自 .pex，用來偵測安裝錯位)
```

陣列工具對 float/int/string/Form/Alias/Actor/ObjectReference 各一份（`PapyrusUtil.psc:24-107`）。代表：

```papyrus
Form[] function PushForm(Form[] ArrayValues, Form push) global native                       ; :28
Form[] function SliceFormArray(Form[] ArrayValues, int StartIndex, int EndIndex = -1) global native ; :98
int[]  function RemoveDupeInt(int[] ArrayValues) global native                              ; :45
Form[] function GetMatchingForm(Form[] ArrayValues1, Form[] ArrayValues2) global native     ; :67
function SortStringArray(string[] ArrayValues, bool descending = false) global native       ; :107
```

另含字串切/接（`StringSplit`/`StringJoin`，`:135-138`）、`ClampInt`/`WrapInt`/`SignInt` 等數值小工具（`:151-162`），以及一批為繞過 SKSE bool 陣列 bug 而提供的非 native bool 版（`:169-247`）。註解警告 `Push*` 每次都重建整個陣列，迴圈裡別用（`:22-23`）。

### MiscUtil / ActorUtil / ObjectUtil

MiscUtil 代表函式（`MiscUtil.psc`）：

```papyrus
function ToggleFreeCamera(bool stopTime = false) global native                  ; :30  (TFC 飛行鏡頭)
function SetMenus(bool enabled) global native                                   ; :78  (TM；SE 下不作用)
function PrintConsole(string text) global native                               ; :69  (印到 console)
string function ReadFromFile(string fileName) global native                    ; :58  (讀檔)
bool   function WriteToFile(string fileName, string text, bool append = true, bool timestamp = false) global native ; :61
Actor[] function ScanCellNPCs(ObjectReference CenterOn, float radius = 0.0, Keyword HasKeyword = none, bool IgnoreDead = true) global native ; :18  (cell 掃描)
```

ActorUtil 是 AI package override 堆疊（`ActorUtil.psc`，跨存檔持久；priority 0–100，最高者執行）：

```papyrus
function AddPackageOverride(Actor targetActor, Package targetPackage, int priority = 30, int flags = 0) global native ; :13
bool function RemovePackageOverride(Actor targetActor, Package targetPackage) global native                          ; :16
int  function ClearPackageOverride(Actor targetActor) global native                                                  ; :22
```

ObjectUtil（動畫替換）在 SE 版**已整組停用**——函式被註解掉以強制舊腳本編譯失敗、提醒移植（`ObjectUtil.psc:22-27`）。

## 關鍵設計

### 對比 JContainers

| 面向 | JContainers | PapyrusUtil |
|---|---|---|
| 定址模型 | 容器物件 + 路徑字串（`.sofia.affinity`） | `(Form, key)` 或 `(jsonfile, key)` 直接 KV |
| 概念負擔 | 重（容器生命週期、root/temporary、GC） | 輕（無物件、無生命週期） |
| per-form 持久化 | `JFormDB`（`solveFltSetter` 等） | `StorageUtil.SetFloatValue(akActor, key, v)` |
| 外部可編輯資料 | 需 Lua/domain | **JsonUtil 原生支援**（外部 .json） |
| 巢狀/任意結構 | 強項（容器可任意巢狀） | JsonUtil 的 Path API 可達，StorageUtil 為扁平 KV |
| 跨 mod 共用 | 容器需傳遞 handle | 全域共用命名空間 + key 前綴，零硬依賴 |

一句話：**要做複雜資料結構、巢狀容器、Lua 整合，選 JContainers；只要 per-form / per-key 狀態與設定檔，PapyrusUtil 概念更輕、夠用且更快上手。**

### JsonUtil 的獨特賣點

資料存在 `data/skse/plugins/StorageUtilData/*.json`，特性是**獨立於存檔、可在遊戲外被工具或使用者編輯**（`JsonUtil.psc:12-28`）。這讓它天生適合兩類資料：

- **設定（config）**：mod 設定值放 json，使用者或 MCM 改了，不綁特定存檔。
- **資料表（data table）**：隨 mod 出貨的靜態查表資料（掉落表、權重、對白池…），runtime 唯讀載入。

對照之下 StorageUtil 的值寫進 co-save，是「runtime 狀態」的歸宿（跟著存檔走、玩家各自不同）。

### 共用命名空間的代價

所有 mod 寫同一個全域儲存，沒有命名隔離；官方對策是「key 前綴你的 mod 名」（`StorageUtil.psc:37-41`）。這是約定而非強制，產生內容時必須自律加前綴。

### 已知限制

- CreatorsClub `.esl` 來源的 form 透過 StorageUtil/JsonUtil 儲存/取回會失準（readme Compatibility 段）——存 form 值時需留意來源 plugin 類型。

## 對 ModForge 的意義

ModForge 目前用 **GLOB（GlobalVariable）** 存 runtime 狀態（見 `src/ModForge.Core/Spec.Globals.cs` 與 `Generator.Build.Globals.cs`，CLAUDE.md「已落地功能 → GlobalVariable」）。GLOB 對少量旗標夠用，但：

- 每個狀態要一個 record，FormID 會膨脹；
- **做不到 per-actor 的狀態表**（例：每個 NPC 各自的好感度、各自的對話進度）。

PapyrusUtil 正好補這兩個洞，且**比 JContainers 輕**：

**(a) 二者都是 native 依賴，不該預設。** 產出依賴 PapyrusUtil 的 plugin，等於要求終端使用者裝 PapyrusUtil（且 AE/SE 版本須對應 SKSE）。和 JContainers 一樣應視為**進階選項**，預設仍走 GLOB 與 vanilla 機制。

**(b) 若要選一個當「進階狀態儲存」後端，PapyrusUtil 入門成本低於 JContainers。** ModForge 的腳本是程式化生成的，生成器只要在模板裡塞固定樣板呼叫即可——`StorageUtil.SetFloatValue(akActor, "MF_<feature>_<key>", v)` / `GetFloatValue(...)` 這種扁平 KV 比 JContainers 的容器生命週期更容易**正確地機器生成**（不必管 root 容器何時建立、何時 GC，少一整類洩漏 bug）。per-form 狀態正是 GLOB 補不到的部分。

**(c) JsonUtil 對「資料驅動的生成內容」特別契合。** ModForge 的本質是「生成時就決定一批資料」。這批靜態資料表（掉落權重、對白池、NPC 屬性表…）用 JsonUtil 的做法是：**生成階段把表寫成 .json 隨 mod 一起出貨，runtime 用 `JsonUtil.GetIntValue/GetPathIntValue` 唯讀載入**。好處是表獨立於存檔、可被使用者或外部工具檢視與微調，且不佔用任何 FormID——這比把資料塞進 GLOB 或硬編進腳本都乾淨。`SetPath*/GetPath*` 的任意路徑 API（`JsonUtil.psc:183-208`）讓 ModForge 可輸出自訂結構的表，而非被迫攤平。

務實結論：**短期不動（GLOB + vanilla 足以涵蓋現有功能）；當出現「per-actor 狀態」或「大型資料驅動內容」的需求時，PapyrusUtil 是比 JContainers 更輕、更適合機器生成的後端候選——StorageUtil 對 runtime per-form 狀態，JsonUtil 對隨 mod 出貨的靜態資料表。**
