# 玩家便利(QoL/作弊) backend mod：行動點無限 ＋ 開局解鎖驛站

> 日期：2026-05-23
> 目標版本：太吾繪卷實裝版 **0.0.79.60**
> mod 原始碼：`~/repo/pas/projects/taiwu/QolCheats/`
> 唯一事實來源：反編譯原始碼 `~/dev/taiwu-src/backend/`（本文所有 path:line 皆指此處）
> 性質：單機自用作弊/便利。一個 backend plugin 同時做兩件事，基類用 `TaiwuRemakeHarmonyPlugin`
>      （同時能跑一般生命週期邏輯與 Harmony patch）。

---

## 0. 結論先行

| 功能 | 做法 | 目標 (path:line) |
|---|---|---|
| 行動點無限 | **Harmony Prefix** 攔截 `ExtraDomain.ConsumeActionPoint`，回 false（skip 不扣） | `backend/GameData/GameData/Domains/Extra/ExtraDomain.cs:4031` |
| 開局解鎖驛站 | `OnEnterNewWorld`/`OnLoadedArchiveData` 時：① `SetWorldFunctionsStatus(4)` 跨州 ＋ `(3)` 州內；② 逐區域安全 `UnlockStation(costAuthority:false)` | World 旗標 `WorldDomain.cs:713`；解鎖 `MapDomain.cs:7688` |

- 編譯：`Build succeeded 0 Warning(s) 0 Error(s)`。
- 部署：Config.lua(GBK) + `QolCheats.Backend.dll` 已入遊戲 `Mod/QolCheats/`。
- typeref 綁定（ikdasm 驗證）：`ExtraDomain/MapDomain/WorldDomain/TaiwuDomain/DataContextManager/DataContext`→`[GameData]`、`MapAreaData`→`[GameData.Shared]`、`AdaptableLog`→`[GameData.Utilities]`、`HarmonyPatch`→`[0Harmony]`。

---

## 1. 功能一：行動點無限

### 1.1 行動點機制（原始碼依據）

行動點的「貨幣本體」是 `ExtraDomain._actionPointCurrMonth`：

- 月初值 `300`（`GetActionPointPerMonth()` `ExtraDomain.cs:4016-4019` 回 300；`InitializeActionPoint` :4021-4024）。
- 上限 `GlobalConfig.Instance.ActionPointLimitPerMonth = 600`（`GlobalConfig.cs:1170`），由 `ChangeActionPoint` 的 `Math.Min(...,600)` 封頂（`ExtraDomain.cs:4052`）。
- 10 點 = 1 天（多處 `/10`，如 `WorldDomain.GetLeftDaysInCurrMonth` `WorldDomain.cs:7050-7053`）。

**扣除統一入口**：`ConsumeActionPoint(DataContext, int)`（`ExtraDomain.cs:4031-4034`）→ `ChangeActionPoint(context, -value)`。

全 backend 的扣除呼叫點**全部**走 `ConsumeActionPoint`（直接或經 `WorldDomain.ConsumeActionPoint` 轉手）：

- `BuildingDomain.cs:431`（修習武學）
- `WorldDomain.cs:7058`（`AdvanceDaysInMonth`）、`WorldDomain.cs:7063`（`ConsumeActionPoint` 轉手）
- `AdventureDomain.cs:729`（`WithholdingActionPoint`，奇遇預扣）
- `MapDomain.cs:5693`（原地待命）、`MapDomain.cs:6445`（跨月移動）、`MapDomain.cs:7949`（旅行推進）

唯一直接呼叫 `ChangeActionPoint` 的點是 `Character.cs:6112`——茶師(TeaTaster)技能**回復**行動點（正值 delta），與扣除無關，不受本 patch 影響。

**檢查/讀值**都讀同一個 `_actionPointCurrMonth`：
- `IsActionPointEnough(value)`：`value <= _actionPointCurrMonth`（`ExtraDomain.cs:4041-4044`）
- `GetTotalActionPointsRemaining()`：回 `_actionPointCurrMonth`（:4036-4039）
- `GetActionPointCurrMonth()`：回 `_actionPointCurrMonth`（:23545-23548）

### 1.2 選用做法與安全性論證

**做法：Prefix 攔截 `ConsumeActionPoint` 回 `false`（跳過原方法 → 不扣）。**

```csharp
[HarmonyPatch(typeof(ExtraDomain), nameof(ExtraDomain.ConsumeActionPoint))]
internal static class ExtraDomain_ConsumeActionPoint_Patch
{
    [HarmonyPrefix]
    private static bool Prefix() => false; // skip original：行動點不被消耗
}
```

效果：`_actionPointCurrMonth` 永遠維持月初值（300），所有檢查/顯示自然永遠充足且不下降＝「每月可無限行動」。

**為何選這個、為何安全（對比其他候選）**：

- ✅ **單一攔截點覆蓋所有扣除路徑**，副作用最小，無遺漏。
- ✅ **不改讀值 getter** → UI 行動點數字 / 剩餘天數顯示完全正常（顯示真實的滿值 300=30 天，不溢出、不顯示異常）。這比「Postfix 把 getter 回大值」安全：後者會讓 `GetLeftDaysInCurrMonth = 600/10 = 60 天` 之類，雖不溢位但顯示怪異，且仍無法阻止扣除真正發生（讀寫不一致）。
- ✅ **不碰 `ChangeActionPoint`** → 過月時 `UpdateActionPoint(+300)`（`ExtraDomain.cs:4026-4029`）正常補點、茶師回復點正常、`Math.Min(...,600)` 封頂仍在 → 不溢位。對比「Prefix `ChangeActionPoint` skip 全部」會連回復/補點都擋掉。
- ✅ **奇遇預扣不破壞**：`AdventureDomain.WithholdingActionPoint`（`AdventureDomain.cs:727-731`）雖呼叫 `ConsumeActionPoint`，但它另記一筆獨立的 `_actionPointWithhold`；`RemoveWithheldActionPoint`（:733-739）用的是 `_actionPointWithhold` 自己的帳，與 `_actionPointCurrMonth` 無關。skip 扣除不影響 withhold 收支平衡。
- ⚠️ **跨月長途旅行**：`MapDomain.cs:7946-7955` 旅行用 `actualCost = Math.Min(cost, GetTotalActionPointsRemaining())`，若一趟 `cost > 300` 仍會在 :7951 `actualCost < cost` 時觸發 `AdvanceMonth` 過月。這是**遊戲固有行為**（旅行超過一個月本就會跨月），非 bug；過月後行動點補回，玩家仍「行動點不掉」。

---

## 2. 功能二：開局解鎖驛站

### 2.1 驛站系統與解鎖 gate（原始碼依據）

驛站(快速旅行/傳送)有**兩層 gate**：

1. **每區域旗標** `MapAreaData.StationUnlocked`（`MapAreaData.cs:49`）＋ 該區的 `StationBlockId`（:43，預設 `-1` 見 :78）。解鎖方法 `MapDomain.UnlockStation(context, areaId, costAuthority=true)`（`MapDomain.cs:7688-7731`）：`costAuthority:true` 時會花太吾「威望」資源、不足會丟例外（:7699-7714）；`costAuthority:false` 純解鎖。
2. **世界功能旗標** `WorldFunctionType`（位元集，`WorldFunctionType.cs`）：
   - `IntraStateTravel = 3`（州內傳送）
   - `InterStateTravel = 4`（跨州傳送）

   讀寫：`WorldDomain.GetWorldFunctionsStatus(byte)` / `SetWorldFunctionsStatus(DataContext, byte)`（`WorldDomain.cs:708-721`，`Set` 對已設值是 no-op）。

**真正的傳送 gate** 在 `MapDomain.AllowCrossAreaTravel`（`MapDomain.cs:1467-1468`）：

```csharp
return (fromAreaId != taiwuVillage.AreaId && toAreaId != taiwuVillage.AreaId)
    || (太吾村Area.StationUnlocked && DomainManager.World.GetWorldFunctionsStatus(4)); // 4=InterStateTravel
```

`MerchantDomain.cs:1368` 用同一組 gate。

**為何「綁開局進度」**：status 3/4 在 backend C# 幾乎沒有 `Set` 點（僅 `WorldDomain.FixAbnormalDomainArchiveData` :317-320 在 status 4 已開時補 status 3），它們的正常解鎖在**事件腳本**經 `WorldFunctions.SetWorldFunctionsStatus`（EventFunction 53，`WorldFunctions.cs:29-38`）觸發——對應開局劇情/主線進度（`MainStoryLineProgress`）。這證實了「驛站要遊戲進行到一定開局進度才開放」。

世界生成時的開局自動解鎖也有數量限制 `MapInitUnlockStationStateCount`（`MapDomain.cs:3701-3724` 只解鎖太吾所在＋鄰近少數州），其餘要玩家自己花威望逐個解鎖。

### 2.2 選用做法與安全性論證

**做法：在 `OnEnterNewWorld` / `OnLoadedArchiveData` 兩個生命週期裡：**
1. `SetWorldFunctionsStatus(context, 4)` ＋ `(context, 3)` — 打開跨州/州內傳送。
2. **自寫安全迴圈**遍歷 `areaId 0..134`，對「未解鎖且 `StationBlockId >= 0`」的區域呼叫 `UnlockStation(context, areaId, costAuthority:false)`。

**為何不直接呼叫現成的 `GmCmd_UnlockAllStation`**（`MapDomain.cs:5552-5566`）：
它內部對每個未解鎖區域呼叫 `GetBlock(areaId, _areas[areaId].StationBlockId)`（:5558）。當某區域 `StationBlockId == -1`（無驛站格，如部分破碎之地），`GetBlock(areaId, -1)` 會走 `GetRegularAreaBlocks(areaId)[-1]`（`MapDomain.cs:2750-2754`）→ **`IndexOutOfRangeException`**。後端未捕捉例外 = 整個 GameData 進程崩潰斷線。故改自寫迴圈，先判 `StationBlockId >= 0` 才解鎖。

**取得 DataContext 的方式**（`OnEnterNewWorld`/`OnLoadedArchiveData` 本身不帶 context）：
`DataContextManager.GetCurrentThreadDataContext()`（`GameData/Common/DataContextManager.cs:11`）。依據 `ModDomain.OnLoadedArchiveData`（`ModDomain.cs:200-218`）內部即用此法取得 context 後才呼叫各 plugin 的生命週期。

**生命週期觸發時機**（`ModDomain.cs`）：
- `:184-198 InitializeOnEnterNewWorld()` → 對每個 plugin 呼叫 `OnEnterNewWorld()`（世界資料已就緒）。
- `:200-218 OnLoadedArchiveData()` → 取 context 後呼叫各 plugin `OnLoadedArchiveData()`（讀檔後）。

**安全性論證**：
- ✅ 全程 `try-catch`：外層吞所有未預期例外（避免崩潰斷線）；內層每個 area 單獨 `try-catch`，單一區域失敗只跳過該區、不拖垮整局。
- ✅ 防呆：`context == null` 跳過；`GetTaiwuCharId() < 0`（太吾未建立，`_taiwuCharId` 初值 -1 見 `TaiwuDomain.cs:658`）跳過；`area == null || area.StationUnlocked || area.StationBlockId < 0` 跳過。
- ✅ `UnlockStation(costAuthority:false)` 不花威望、不丟「威望不足」例外。對「已解鎖」會丟例外（:7695-7698），故先判 `!StationUnlocked`。
- ✅ `SetWorldFunctionsStatus` 對已設值 no-op，重複呼叫（OnEnterNewWorld 與 OnLoadedArchiveData 都跑）安全。

**副作用評估**：
- 只動 status 3、4 兩個傳送旗標，**不碰** `MainStoryLineProgress`，不會跳過/觸發其他開局劇情。其餘世界功能（如門派劇情、市集等）旗標皆未動。
- 額外好處：`UnlockStation` 會把該區及鄰區 `Discovered = true`（:7719-7729），即解鎖驛站的區域順帶在地圖上「已探索」，符合驛站可達的直覺。
- 因 `HasArchive=false`，本 mod 不寫自己的存檔資料；解鎖效果是直接寫進 World/Map domain 的標準存檔欄位（透過 `SetElement_Areas`/`SetWorldFunctionsStatuses`），會隨遊戲存檔一起保存。

---

## 3. Harmony plugin 寫法（基類選擇）

整個 plugin 用 **`TaiwuRemakeHarmonyPlugin`**（`PluginHelper` 只認直接基類，見 `mod_loader.md` §3）。基類 `Initialize()` 已做 `HarmonyInstance.PatchAll(本組件)`、`Dispose()` 已做 `UnpatchSelf()`，故功能一的 `[HarmonyPatch]` 自動掛上；功能二覆寫 `OnEnterNewWorld`/`OnLoadedArchiveData` 即可。一個 dll 只能有一個帶 `[PluginConfig]` 的 public 進入點。

完整原始碼見 `~/repo/pas/projects/taiwu/QolCheats/Backend/Plugin.cs`。

---

## 4. 編譯與部署

### 4.1 csproj 範本
`~/repo/pas/projects/taiwu/QolCheats/Backend/QolCheats.Backend.csproj`（照抄 ChenJiaBao 範本）：
net6.0、`PlatformTarget x64`、`LangVersion 14.0`、`EnableDefaultCompileItems=false`、`<Compile Include="**/*.cs" Exclude="obj/**/*.cs;bin/**/*.cs"/>`；引用 `GameData`/`GameData.Shared`/`GameData.Utilities`/`Redzen`（`$(BK)=$(Game)/Backend`）＋ `0Harmony`/`TaiwuModdingLib`（`$(MG)=Managed`）。0.0.79.60 用**普通引用、不需 extern alias**。

### 4.2 編譯
```bash
cd ~/repo/pas/projects/taiwu/QolCheats/Backend
dotnet build -c Release QolCheats.Backend.csproj
# → Build succeeded. 0 Warning(s) 0 Error(s)
```

### 4.3 部署（Config.lua 轉 GBK、dll 入 Plugins/）
```bash
GAME="/home/lorkhan/.local/share/Steam/steamapps/common/The Scroll Of Taiwu"
mkdir -p "$GAME/Mod/QolCheats/Plugins"
iconv -f UTF-8 -t GBK ~/repo/pas/projects/taiwu/QolCheats/dist/Config.lua -o "$GAME/Mod/QolCheats/Config.lua"
cp ~/repo/pas/projects/taiwu/QolCheats/Backend/bin/Release/QolCheats.Backend.dll "$GAME/Mod/QolCheats/Plugins/QolCheats.Backend.dll"
```

### 4.4 manifest（`dist/Config.lua`，UTF-8 原始檔）
重點欄位：`GameVersion = "0.0.79.60"`、`Source = 0`、`BackendPlugins = {[1]="QolCheats.Backend.dll"}`、`HasArchive=false`、`ChangeConfig=false`。

---

## 5. 使用者實機驗證步驟

> 啟動遊戲 → mod 列表啟用「便利作弊：行動點無限＋開局解鎖驛站」→ 開新世界（或讀檔）。

### 5.1 行動點無限怎麼看
- 開局後在地圖上做任何耗行動點的事（移動到鄰格、修習武學、原地待命推進日子）。觀察右上/角色面板的**行動點數值不下降**（或「本月剩餘天數」始終維持滿值）。
- 連續做多次行動，行動點仍不減少 → 生效。
- 可選：看後端 log（NLog；過月或進世界時會有 `[QolCheats.Plugin]` 的解鎖訊息）。行動點 patch 本身無 log，靠數值不掉判斷。

### 5.2 驛站開局可用怎麼確認
- 開新世界後**立刻**打開大地圖 / 旅行(快速旅行)介面，嘗試**跨州傳送**到遠方州的據點。正常開局此功能被鎖（需劇情進度），裝 mod 後應**一開始就能選擇遠方驛站直接傳送**。
- 地圖上各州的驛站圖示應已點亮 / 可選。
- 後端 log 會出現：`[QolCheats.Plugin] [OnEnterNewWorld] 驛站解鎖完成：本次新解鎖 N 個區域；已解鎖常規區域總數=...；InterStateTravel(4)=True、IntraStateTravel(3)=True。`（讀檔則是 `[OnLoadedArchiveData]`）。

---

## 6. 可調點

- **行動點若想「顯示也變超大」而非只是不掉**：可額外 Postfix `GetTotalActionPointsRemaining` / `GetActionPointCurrMonth` 回較大值（注意 `ActionPointLimitPerMonth=600` 是合理上限，回 600 顯示 60 天；回更大值會讓「剩餘天數」顯示誇張但不崩）。本版刻意不做以保顯示正常。
- **只想解鎖部分驛站**：把功能二迴圈改成只對特定 `areaId` 解鎖，或保留 `costAuthority:true` 走正常花威望流程。
- **想連太吾村本身的驛站一起確保解鎖**：迴圈已涵蓋所有常規區域（含太吾村 area），跨州 gate 的 `太吾村.StationUnlocked` 條件即被滿足。
- **若只要其中一個功能**：移除對應段落即可（兩功能彼此獨立）。

---

## 7. 最大風險 / 需實機確認處

1. **patch 方法簽章版本漂移**：本版對 0.0.79.60 反編譯源驗證 `ConsumeActionPoint(DataContext, int)`、`UnlockStation(DataContext, short, bool)`、`SetWorldFunctionsStatus(DataContext, byte)`、`GetElement_Areas(int)` 等簽章；若遊戲改版需重新對齊並重編。Prefix 用無參數簽章（`Prefix()` 回 bool）降低參數漂移風險。
2. **驛站開局即用是否連帶影響開局教學/引導**：理論上只動 status 3/4 與各區 `StationUnlocked`，不碰主線進度；但**極早期（如還在出生地/引導階段 area 135/136）**是否會讓玩家提前離開引導區，需實機觀察。若有異常可改為僅在 `OnLoadedArchiveData`（讀檔）解鎖，或加「主線進度 >= 某值才解鎖」條件。
3. **跨月旅行觸發過月**：如 §1.2 所述屬固有行為，非 bug，但玩家若期待「長途旅行也完全不過月」會與直覺有落差。
4. **與其他改動行動點/驛站的 mod 並用**：本 mod 的 Harmony prefix skip 與他人對同方法的 patch 可能交互；單機自用通常無虞。
