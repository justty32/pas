# 進度保存 / Session Resume

> 更新：2026-05-23 21:12　|　下次接手請先讀這份，再看 `analysis/下一站江湖Ⅱ/session_log.md`

## 一句話現況

mod 目標已從「閒置 NPC 找椅子坐」**轉向「閒置 NPC 原地坐下／打坐」**（因為本遊戲幾乎沒有椅子物件）。
**核心已實機驗證成功**：通用坐姿 clip = `chusheng_sit`，強制 NPC 播放後肉眼確認真的坐下。
已把 plugin 改寫成正式「原地坐下版 0.2.0」並編譯部署，**待實機驗證自主行為**（閒置 NPC 自己隨機坐下、被打擾起身）。

## ✅ 已攻克的關鍵問題（別重查）

1. **跑錯遊戲**：之前在跑《太吾繪卷》(838350) 不是《下一站江湖Ⅱ》(1606180)。已確認改跑對的遊戲。
2. **注入的 MonoBehaviour.Update 不被 tick**：本遊戲會銷毀 BepInEx 建的 GameObject。
   → 對策：邏輯放**純 C# 物件**，用 **Harmony patch `AppGame.Update`**（每幀必跑）驅動。
3. **plugin Instance 變 Unity「fake null」**：`== null` 回 true 但 C# 參考仍有效。
   → 對策：null 判斷一律用 **`ReferenceEquals`**。
4. **`PlayAnim` 回傳值會說謊**：載不到 clip 時 fallback `CrossFade` 也回 `true`（`AnimationComponent.cs:646`，三條分支都設 `result=true`）。8/8 全 True 是假象。
   → 對策：判斷 NPC 是否真有某 clip 一律用 **`HaveAnim()`**（`AnimationComponent.cs:779`，真查 `animationClipDescription`）。
5. **椅子死路**：~10GB 資產裡 "Chair" 字串僅約 19 個，實機掃描 0 張 → 放棄找椅子，改原地坐。
6. **通用坐姿 clip = `chusheng_sit`**：實機 HaveAnim 統計 **chusheng_sit=5/8**，而 `dazuo/sit/sitnew/chu_sit` 在路人身上 **0/8**，`idle`=8/8。視覺鎖定 NPC 播 `chusheng_sit` → 使用者確認「成功了」=真的坐下。
7. **定格坐姿手法**：`PlayAnim(clip, 0f, 0.99f)`（仿本體對 defaultAnim 的做法 `NpcController.cs:1257`，0.99=跳到 clip 末端坐定姿勢）。
8. **意外發現**：本體 `XiuXian`（休閒）系統會讓閒置 NPC 自動播 `freetime1~6`（`NpcXiuXianAnimComponent.cs`）。我們坐下前要先 `ExitXiuXian()` 並壓住 AI，免得被它蓋掉。

## plugin 現況（`SitOnChairMod/` → 原地坐下版 0.2.0）

- `SitOnChairMod.cs`：純 C# manager（`SitOnChairManager.Inst`），由 Harmony postfix `AppGame.Update` 每幀呼叫 `Tick()`。
  - **Tick 流程**：熱鍵 → AutoDiag(預設關) → `MaintainSitters()`（每幀維持坐姿）→ 每 0.5s `ProcessNpcs()`（評估誰坐/起）。
  - **坐下條件**：`IsEligible`（人形/活著/可互動/mesh 載完）＋ 非 `IsDisturbed`（戰鬥/比較/被搶）＋ nav 停止 ＋ 閒置 ≥ `IdleSeconds` ＋ `HaveAnim` 有坐姿 clip ＋ 機率 `Chance`。
  - **坐下**：`PauseNpcAi(true)` + `ExitXiuXian()` + `PlayAnim(clip,0f,0.99f)`；`clip` 由 `PickSitClip` 取 `SitAnims` 候選中該 NPC 第一個 `HaveAnim` 的。
  - **維持**：每幀若 `!IsAnimName(clip)` 就重播、持續壓 AI。
  - **起身**：坐滿 `SitDuration` 秒 / 被打擾 / 劇情中 → `BreakPrimAnm()` + `EnterState(IDLE,true)` + `PauseNpcAi(false)`。
  - **F8** = 傾印附近 15m NPC（合格/被擾/有無坐姿 clip/phase）。
  - **F9** = `HaveAnim` 探測附近 8 個 NPC 擁有哪些坐姿 clip + 印 def/save/cur/XiuXian 清單。
- config `BepInEx/config/com.lorkhan.sitonchair.cfg`（已重寫為新 schema，本次 `Verbose=true` 方便看 `[sit]` 坐下/起身）：
  `SitAnims`(預設 `chusheng_sit,dazuo,sit,sitnew`)、`IdleSecondsBeforeSit`、`SitDurationSeconds`、`Chance`、`MaxConcurrentSitters`、`OnlyRandomNpc`、`NpcScanInterval`、`Verbose`、`AutoDiag`。
- `SitOnChairMod.csproj`：`dotnet build -c Release` → 自動輸出 `BepInEx/plugins/SitOnChairMod.dll`。**改 DLL 必須完整重啟遊戲**才生效。

### 用到的遊戲 API（已對原始碼核實）
- 列舉 NPC：`WorldManager.Instance.m_Dir`（`Dictionary`）→ `as NpcController`；`m_bLoadingScene`、`m_IsInJuQing`
- 動畫：`AnimationComponent` `PlayAnim(name,fade,offset)`(`:646`)、`HaveAnim`(`:779`)、`IsAnimName`(`:762`)、`GetCurAnim`(`:830`)、`BreakPrimAnm`(`:897`)、`EnterState(STATE_ID,force)`(`:456`)
- 狀態：`NpcController.m_IsInCombat`/`IsInSightCombat()`；`NpcEntity.m_CanInteract/m_CompareWithPlayer/m_RobbedByPlayer/IsDead()/IsHumanOrAnimal()/IsAnimal()/IsRandomNpc()/saveAnim/m_NpcPrototype.defaultAnim`
- 其他：`Position`、`m_MeshComponent.IsLoadComplete()`、`m_MoveComponent.IsNavStop()`、`m_NpcXiuXianAnimComponent.ExitXiuXian()/GetAllAnims()`、`m_AutomatAIScript.m_bUpdateable`

## 下一步 TODO（醒來接續）

1. 🟡 **驗證自主行為**：完全重啟遊戲 → 進場景到 NPC 多處站定 → 看附近 NPC 會不會自己陸續坐下、約 20 秒起身、靠近互動/開打就起身。讀 `BepInEx/LogOutput.log` 的 `[sit] xxx 坐下/起身`。
2. 微調手感：`Chance`（坐下機率）、`IdleSecondsBeforeSit`、`SitDurationSeconds`、`MaxConcurrentSitters`。
3. 坐姿是否正常（會不會浮空/陷地/朝向怪）→ 若有，研究 NpcXiuXianAnim 表是否有座位錨點或本體坐下的位置處理。
4. 定案後：`Verbose=false`，考慮移除 ProbeNearbyNpcs/F9 等診斷碼（或保留當工具）。
5. 回填 `tutorial/npc_sit_on_chair_mod.md` 的「待驗證清單」（chusheng_sit 已驗證為通用坐姿）。

## 環境備忘

- BepInEx 5.x 已裝（`BepInEx/core/`），`0Harmony.dll` 也在；csproj 已引用。
- 反編譯原始碼在 `SourceCode/Assembly-CSharp/`（3004 cs）。本體資料 `下一站江湖Ⅱ_Data/StreamingAssets/DB/db1.txt`（80MB）。
- 除錯陷阱：`LogOutput.log` 頂部 banner 時間被 Wine 凍結，別信，看 Linux 端 mtime；`.NET` 字面量是 UTF-16，`strings` 要加 `-e l`。
- 額外即時落盤診斷檔：`BepInEx/sitonchair_diag.log`（`[hb]` 心跳、`[tick-err]`、`[probe]` 統計）。
