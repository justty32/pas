# 《下一站江湖Ⅱ》BepInEx Mod 開發指南 — 踩坑全紀錄與通用骨架

> 日期：2026-05-23　狀態：實戰驗證完成（SitOnChairMod 0.2.0 已上線運作）
>
> 這份是「下次做任何 mod 都先讀」的總綱。把第一個 mod（閒置 NPC 原地坐下）一路踩到的坑、
> 解法、已核實的 API、可直接複製的程式骨架全部收錄。每條都附原始碼路徑+行號。

---

## 0. TL;DR — 三條保命法則

1. **不要靠注入的 `MonoBehaviour.Update`**：本遊戲會銷毀 BepInEx 建的 GameObject，注入的 Update **永遠不會被呼叫**。
   邏輯放**純 C# 物件**，用 **Harmony patch `AppGame.Update`** 當每幀驅動。
2. **plugin/自建物件是 Unity「fake null」**：`obj == null` 會回 `true`（Unity 運算子重載）但 C# 參考其實有效。
   判斷自家物件存活一律用 **`ReferenceEquals(obj, null)`**。
3. **`AnimationComponent.PlayAnim` 回傳值會說謊**：載不到 clip 時也回 `true`。
   判斷某 NPC 有無某動畫一律用 **`HaveAnim(name)`**。

---

## 1. 環境致命陷阱（本遊戲特有，最重要）

### 1.1 注入的 MonoBehaviour.Update 不被 tick
**現象**：`BaseUnityPlugin.Awake()` 會跑，但同物件上的 `Update()` 永遠不執行；連 `AddComponent` 出來的
新 MonoBehaviour 也只跑 `Awake` 不跑 `Update`。心跳、按鍵偵測、所有每幀邏輯全部靜默。

**根因**：本遊戲會把 BepInEx Chainloader 建立的 manager GameObject（及我們自己 `AddComponent`/`new GameObject`
建的）銷毀或排除在 PlayerLoop 之外。`Awake` 是 `AddComponent` 當下同步呼叫的，所以會跑；之後沒有 tick。

**解法**：
- 邏輯不要放 MonoBehaviour，放**純 C# 物件**（`new`，存成 static 參考，Unity 不會碰它）。
- 用 **Harmony patch 遊戲自己每幀會跑的方法** `AppGame.Update` 的 Postfix 來呼叫你的 `Tick()`。
  `AppGame` 是遊戲主迴圈入口，保證每幀執行。

```csharp
[HarmonyPatch(typeof(AppGame), "Update")]
public static class AppGameUpdatePatch
{
    static void Postfix()
    {
        var mgr = MyManager.Inst;          // 純 C# 物件
        if (mgr == null) return;
        try { mgr.Tick(); } catch (Exception ex) { /* 落盤 log */ }
    }
}
```

### 1.2 plugin Instance 是 Unity「fake null」
**現象**：在 `Tick()` 裡 `if (Plugin.Instance == null) return;` 會**每幀提前 return**，邏輯全被擋。

**根因**：plugin 本體是 MonoBehaviour，其 GameObject 被遊戲銷毀後，Unity 的 `==` 運算子對「已銷毀物件」
回傳 `true`，但該 C# 物件與其欄位（ConfigEntry 等）其實還活著、可正常存取。

**解法**：自家物件的存活判斷一律 `ReferenceEquals`。存取其 ConfigEntry 欄位完全沒問題。
```csharp
var p = Plugin.Instance;
if (ReferenceEquals(p, null)) return;     // 對：真 C# null 語義
// if (p == null) return;                 // 錯：fake-null 會誤擋
bool on = p.cfgEnabled.Value;             // 欄位存取正常
```
> 反例（本次真的踩到）：`if (P != null && P.cfgVerbose.Value)` 因 `P != null` 恆為 false，整段被跳過。

### 1.3 即時落盤診斷檔（繞過 log 緩衝疑慮）
排查「到底有沒有在跑」時，BepInEx 的 `LogOutput.log` 可能讓你懷疑是緩衝沒 flush。用
`File.AppendAllText` 寫一個獨立檔，每行即時落盤，最可信：
```csharp
public static void DiagFile(string msg)
{
    try { System.IO.File.AppendAllText(DiagPath, $"{DateTime.Now:HH:mm:ss.fff} {msg}\n"); } catch { }
}
// DiagPath = Path.Combine(Paths.BepInExRootPath, "yourmod_diag.log");
```
搭配**幀計數心跳**（不要用 deltaTime，暫停時會凍）：第 1 幀印、之後每 N 幀印一次，確認驅動沒斷。

---

## 2. 動畫系統陷阱（NPC 行為類 mod 必讀）

來源：`SourceCode/Assembly-CSharp/SweetPotato/AnimationComponent.cs`

### 2.1 `PlayAnim` 回傳值會說謊 → 用 `HaveAnim`
`AnimationComponent.PlayAnim(...)`（`:646`）流程：載入 clip → 有就 `PlayerAnimCustom`；**沒有就 fallback
`Animator.CrossFade(animName,...)`**（`:709`，若該 state 不在 controller 裡就靜默失敗）→ **三條分支都設
`result = true`**（`:712`）。所以回傳 `true` 完全不保證畫面有動。

**正解**：`HaveAnim(name)`（`:779`）直接查 `animationClipDescription`，clip 真的存在才回 true。
```csharp
if (npc.m_AnimationComponent.HaveAnim("chusheng_sit")) { /* 這 NPC 真的有此 clip */ }
```
> 教訓：不同 NPC 的 animator controller 綁的 clip 不同。實測通用人形坐姿 = `chusheng_sit`（約 6 成有）；
> 而 `chu_sit`/`dazuo`/`sit`/`sitnew` 在路人身上常常 0/8。`idle` 才是人人都有。**先 HaveAnim 探測再用**。

### 2.2 定格在某姿勢（不要播完跳回 idle）
本體讓「靜止坐著」的 NPC 定格的做法（`NpcController.cs:1257`）：
```csharp
m_AnimationComponent.PlayAnim(clip, 0f, 0.99f);  // 第3參數 normalizedTimeOffset=0.99 → 跳到 clip 末端定格
```

### 2.3 維持動畫不被蓋掉
NPC 自身 AI 與「休閒系統」會把你播的動畫蓋回去。要持續維持某姿勢需三件事：
1. 壓住自身 AI：`npc.m_AutomatAIScript.m_bUpdateable = false;`
2. 關掉休閒動作元件：`npc.m_NpcXiuXianAnimComponent?.ExitXiuXian();`
   （`NpcXiuXianAnimComponent.cs`：閒置 NPC 會自動隨機播 `freetime1~6` 等休閒動作）
3. 每幀檢查、被覆蓋就重播：`if (!ac.IsAnimName(clip)) ac.PlayAnim(clip, 0f, 0.99f);`

恢復時：`ac.BreakPrimAnm(); ac.EnterState(STATE_ID.ACTION_STATE_IDLE, true); m_bUpdateable = true;`

---

## 3. Wine/Proton 環境除錯陷阱

- **先確認跑的是對的遊戲**：本作 AppId `1606180`，執行檔 `下一站江湖Ⅱ.exe`。曾誤在《太吾繪卷》
  (`838350`, `The Scroll of Taiwu.exe`) 裡測，當然沒反應。第一步：
  `ps aux | grep -iE "1606180|下一站江湖"`。
- **`LogOutput.log` 頂部 banner 時間被 Wine 凍結**（永遠某固定時刻），**別用它判斷有無重啟**；
  看 Linux 端檔案 `mtime`。
- **改了 DLL 必須完整重啟遊戲**：BepInEx 只在啟動時載入 plugin。
- **`.NET` 字串字面量是 UTF-16**：普通 `strings` 抓不到（中文/字面量），要 `strings -e l xxx.dll`。
- **失焦停跑**：Unity 預設 `runInBackground=false`，視窗失焦時迴圈會停。Awake 設
  `Application.runInBackground = true;` 方便邊測邊看 log。

---

## 4. 開發工具鏈

### 4.1 csproj 範本（已驗證可編譯）
`net472`，參考 BepInEx + 0Harmony + 遊戲組件。輸出直接落到 plugins/：
```xml
<PropertyGroup>
  <TargetFramework>net472</TargetFramework>
  <OutputPath>../BepInEx/plugins/</OutputPath>
  <LangVersion>latest</LangVersion>
</PropertyGroup>
<!-- Reference: BepInEx.dll、0Harmony.dll（BepInEx/core/）、Assembly-CSharp.dll、
     UnityEngine + 需要的 module：CoreModule、AIModule、PhysicsModule、InputLegacyModule
     （Input 類要 InputLegacyModule 否則編不過）。皆在 下一站江湖Ⅱ_Data/Managed/ -->
```
編譯：`cd YourMod && dotnet build -c Release`（環境有 dotnet 10 / mono / csc / msbuild）。

### 4.2 查反編譯原始碼
- 原始碼：`SourceCode/Assembly-CSharp/`（3004 個 .cs，由 `ilspycmd -p` 反編譯而來）。
- 找類別/方法：`grep -rn 'Keyword' SourceCode/Assembly-CSharp/`
- 取單一型別最新還原：`ilspycmd -t <FullTypeName> 下一站江湖Ⅱ_Data/Managed/Assembly-CSharp.dll`
- 驗 IL（懷疑高階還原失真時）：`ilspycmd -il ...`
- 找動畫/字串名（資料表常以字面量出現）：`grep -rohE '"[a-z_]+sit[a-z_]*"' SourceCode/...`

---

## 5. 遊戲 API 速查（已對原始碼核實，附路徑/行號）

> 命名空間多在 `SweetPotato`。`using SweetPotato;`

### 世界/場景狀態
- `WorldManager.Instance.m_Dir` — `Dictionary`，所有 LocatableController（NPC/玩家等），值 `as NpcController` 取 NPC。
- `WorldManager.Instance.m_bLoadingScene` — 是否在載入場景（true 時別動）。
- `WorldManager.Instance.m_IsInJuQing` — 是否在劇情中（true 時建議停手/恢復原狀）。
- `PlayerController.Instance.Position` — 玩家位置。

### NPC（`NpcController` / `NpcEntity`）
- 位置：`npc.Position`（`LocatableController.cs:64`）
- 實體：`npc.m_NpcEntity`；原型：`npc.m_NpcEntity.m_NpcPrototype`（`.defaultAnim`、`.id`、`.bubblegroupid`…）
- 存檔姿勢：`npc.m_NpcEntity.saveAnim`（`NpcEntity.cs:34`）
- 載入完成：`npc.m_MeshComponent.IsLoadComplete()`
- 狀態判斷：`NpcEntity.IsDead()` / `m_CanInteract` / `IsHumanOrAnimal()` / `IsAnimal()` / `IsRandomNpc()`
- 被干擾：`npc.m_IsInCombat` / `npc.IsInSightCombat()` / `m_CompareWithPlayer` / `m_RobbedByPlayer`

### 動畫（`AnimationComponent`，`SweetPotato/AnimationComponent.cs`）
- `PlayAnim(name, fade=0, normalizedTimeOffset=0, speed=1, ...)`（`:646`）回傳 bool（會說謊，見 §2.1）
- `HaveAnim(name)`（`:779`）— **真查 clip 是否存在**
- `IsAnimName(name)`（`:762`）— 當前播的是不是這支
- `GetCurAnim()`（`:830`）— 當前動畫名
- `BreakPrimAnm()`（`:897`）、`EnterState(STATE_ID, forceSetState)`（`:456`）
- 狀態列舉：`STATE_ID`（`SweetPotato/STATE_ID.cs`）— `ACTION_STATE_IDLE=1`、`ACTION_STATE_IDLE1=2`、`ACTION_STATE_WALK`…

### 移動（`MoveComponent` / `UnitController`）
- 停止判斷：`npc.m_MoveComponent.IsNavStop()`（`MoveComponent.cs:330`）
- 導航前往：`npc.AutoFindWay(Vector3 dest, float stopDist, float speed, Action onFinish, STATE_ID state)`（`UnitController.cs:2390`）
- 停止：`npc.StopAllMove()`；朝向：`npc.SetDirectionY(float)`；速度：`npc.GetSpeed()`

### AI / 休閒控制
- 暫停/恢復自身 AI 腳本：`npc.m_AutomatAIScript.m_bUpdateable = false / true;`
- 休閒動作元件：`npc.m_NpcXiuXianAnimComponent`（`ExitXiuXian()` / `GetAllAnims()` 取該 NPC 真能播的休閒動作清單）
- 腳本 API 全集（963 函式）見 `answers/automat_script_api.md`、`others/automat_script_functions.txt`

---

## 6. 通用 Mod 骨架（直接複製改）

```csharp
using System; using BepInEx; using BepInEx.Configuration;
using HarmonyLib; using SweetPotato; using UnityEngine;

namespace MyMod
{
    [BepInPlugin("com.you.mymod", "My Mod", "0.1.0")]
    public class MyPlugin : BaseUnityPlugin
    {
        public static MyPlugin Instance;
        public ConfigEntry<bool> cfgEnabled;
        void Awake()
        {
            Instance = this;
            Application.runInBackground = true;
            cfgEnabled = Config.Bind("General", "Enabled", true, "總開關");
            MyManager.Inst = new MyManager();                 // 純 C# 物件
            new Harmony("com.you.mymod").PatchAll(typeof(MyPlugin).Assembly);
        }
    }

    [HarmonyPatch(typeof(AppGame), "Update")]               // 唯一可靠的每幀驅動
    public static class Driver
    {
        static void Postfix()
        {
            var m = MyManager.Inst; if (m == null) return;
            try { m.Tick(); } catch { /* 落盤 */ }
        }
    }

    public class MyManager
    {
        public static MyManager Inst;
        MyPlugin P => MyPlugin.Instance;
        public void Tick()
        {
            var p = P; if (ReferenceEquals(p, null)) return;  // fake-null 防呆
            if (!p.cfgEnabled.Value) return;
            var wm = WorldManager.Instance;
            if (wm == null || wm.m_bLoadingScene) return;
            // … 你的邏輯：foreach (var v in wm.m_Dir.Values) { var npc = v as NpcController; … }
        }
    }
}
```

---

## 7. 除錯流程 checklist（mod 沒反應時依序排查）

1. `ps aux | grep -iE "1606180|下一站江湖"` — 真的在跑這款遊戲？
2. `strings -e l BepInEx/plugins/MyMod.dll | grep 你的標記字串` — DLL 真的部署了最新版？
3. 看 `BepInEx/LogOutput.log` 有無 plugin 載入訊息（依 Linux mtime 判斷新鮮度，別信 banner 時間）。
4. 心跳有出現嗎？沒有 → 你是不是又靠 MonoBehaviour.Update 了（§1.1）。
5. 心跳有、邏輯沒跑 → 是不是被 `== null` fake-null 擋了（§1.2）。
6. 動畫/行為沒效果但回傳 true → 用 `HaveAnim` / 肉眼驗證，別信回傳值（§2.1）。
7. 改了 DLL/config → **完整重啟遊戲**才生效。

---

## 附：本指南的實證來源
第一個 mod **SitOnChairMod**（閒置 NPC 原地坐下）。完整可行性偵察見
`tutorial/npc_sit_on_chair_mod.md`；逐步除錯與決策過程見 `session_log.md`；接手點見 `../../progress.md`。
