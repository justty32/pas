using System;
using System.Collections.Generic;
using System.Linq;
using BepInEx;
using BepInEx.Configuration;
using HarmonyLib;
using SweetPotato;
using UnityEngine;

// 《下一站江湖Ⅱ》Mod：閒置 NPC 原地坐下／打坐（自主版，BepInEx）
//
// 由來：本遊戲幾乎沒有椅子物件，原「找椅子坐」不可行，改為「原地坐下」。
// 實機驗證（2026-05-23）確認：
//   - 通用坐姿 clip = "chusheng_sit"（約 6 成人形 NPC 擁有；dazuo/sit/sitnew/chu_sit 在路人身上多半沒有）。
//   - AnimationComponent.PlayAnim 回傳值會說謊（載不到 clip 時 fallback CrossFade 也回 true），
//     必須用 HaveAnim() 判斷該 NPC 是否真有此 clip。
//   - 定格坐姿用 PlayAnim(clip, 0f, 0.99f)（仿 NpcController.cs:1257 對 defaultAnim 的做法）。
//   - 維持坐姿需：壓住 m_AutomatAIScript.m_bUpdateable、ExitXiuXian()、被覆蓋就每幀重播。
//
// 環境陷阱（前期踩過）：本遊戲會銷毀 BepInEx 注入的 GameObject → 注入的 MonoBehaviour.Update 不 tick、
//   且 plugin Instance 變 Unity「fake null」。對策：邏輯放純 C# 物件、用 Harmony patch AppGame.Update 驅動、
//   null 判斷一律用 ReferenceEquals。
// 詳見 work/analysis/.../tutorial/npc_sit_on_chair_mod.md
namespace SitOnChairMod
{
    [BepInPlugin("com.lorkhan.sitonchair", "Sit On Chair", "0.2.0")]
    public class SitOnChairPlugin : BaseUnityPlugin
    {
        public static SitOnChairPlugin Instance;
        public static ManualLogSourceWrapper Log;

        // ---- 即時落盤的檔案日誌，繞過 BepInEx DiskLogListener 緩衝疑慮 ----
        public static string DiagPath;
        public static void DiagFile(string msg)
        {
            try { System.IO.File.AppendAllText(DiagPath, $"{DateTime.Now:HH:mm:ss.fff} {msg}\n"); }
            catch { }
        }

        // ---- 設定 ----
        public ConfigEntry<bool> cfgEnabled;
        public ConfigEntry<string> cfgSitAnims;      // 逗號分隔的坐姿 clip 候選，依序取 NPC 第一個 HaveAnim 的
        public ConfigEntry<float> cfgIdleSeconds;
        public ConfigEntry<float> cfgSitDuration;
        public ConfigEntry<float> cfgChance;
        public ConfigEntry<int> cfgMaxSitters;
        public ConfigEntry<bool> cfgOnlyRandomNpc;
        public ConfigEntry<float> cfgNpcScanInterval;
        public ConfigEntry<bool> cfgVerbose;
        public ConfigEntry<KeyCode> cfgDumpKey;
        public ConfigEntry<KeyCode> cfgProbeKey;
        public ConfigEntry<bool> cfgAutoDiag;
        public ConfigEntry<float> cfgAutoDiagInterval;

        void Awake()
        {
            Instance = this;
            Log = new ManualLogSourceWrapper(Logger);

            DiagPath = System.IO.Path.Combine(Paths.BepInExRootPath, "sitonchair_diag.log");
            try { System.IO.File.WriteAllText(DiagPath, $"{DateTime.Now:HH:mm:ss.fff} ==== AWAKE（原地坐下版 0.2.0）====\n"); } catch { }

            // 預設 runInBackground=false → 視窗失焦時 Unity 不跑迴圈。強制開啟。
            Application.runInBackground = true;

            cfgEnabled       = Config.Bind("General", "Enabled", true, "總開關");
            cfgSitAnims      = Config.Bind("Sit", "SitAnims", "chusheng_sit,dazuo,sit,sitnew",
                "坐姿動畫候選（逗號分隔，依序取該 NPC 第一個真的擁有的）。chusheng_sit 為實測最通用的坐姿。");
            cfgIdleSeconds   = Config.Bind("Sit", "IdleSecondsBeforeSit", 6f, "閒置（nav 停止）幾秒後才考慮坐下");
            cfgSitDuration   = Config.Bind("Sit", "SitDurationSeconds", 20f, "坐多久後自動起身");
            cfgChance        = Config.Bind("Sit", "Chance", 0.5f, "每次評估通過時實際坐下的機率（0~1）");
            cfgMaxSitters    = Config.Bind("Sit", "MaxConcurrentSitters", 8, "同時最多幾個 NPC 在坐");
            cfgOnlyRandomNpc = Config.Bind("Sit", "OnlyRandomNpc", false, "是否只讓隨機路人 NPC 坐（true=不動劇情NPC）");
            cfgNpcScanInterval = Config.Bind("Perf", "NpcScanInterval", 0.5f, "NPC 狀態評估間隔（秒）");
            cfgVerbose       = Config.Bind("Diagnostics", "Verbose", false, "詳細日誌（每個 NPC 坐下/起身都印）");
            cfgDumpKey       = Config.Bind("Diagnostics", "DumpKey", KeyCode.F8, "傾印附近 NPC 概況的熱鍵");
            cfgProbeKey      = Config.Bind("Diagnostics", "ProbeKey", KeyCode.F9, "用 HaveAnim 探測附近 NPC 擁有哪些坐姿 clip");
            cfgAutoDiag      = Config.Bind("Diagnostics", "AutoDiag", false, "免按鍵：每隔 N 秒自動探測一次（除錯用，預設關）");
            cfgAutoDiagInterval = Config.Bind("Diagnostics", "AutoDiagInterval", 5f, "自動探測間隔（秒）");

            // 純 C# 物件（本遊戲會銷毀我們建的 GameObject）
            _mgr = new SitOnChairManager();
            SitOnChairManager.Inst = _mgr;

            // 由 Harmony postfix AppGame.Update 驅動（注入的 MonoBehaviour.Update 不被呼叫）
            try
            {
                var harmony = new Harmony("com.lorkhan.sitonchair");
                harmony.PatchAll(typeof(SitOnChairPlugin).Assembly);
                DiagFile("Harmony PatchAll 完成（由 AppGame.Update 驅動）");
            }
            catch (Exception ex)
            {
                DiagFile($"[harmony-err] PatchAll 失敗：{ex.GetType().Name}: {ex.Message}");
            }

            Logger.LogInfo("Sit On Chair（原地坐下版）已載入。F8=傾印 / F9=探測坐姿 clip。");
            DiagFile($"AWAKE 完成 runInBackground={Application.runInBackground} unityVer={Application.unityVersion}");
        }

        private SitOnChairManager _mgr;
    }

    // 注入的 MonoBehaviour.Update 在本遊戲不被呼叫 → patch AppGame.Update（每幀跑）來驅動。
    [HarmonyPatch(typeof(AppGame), "Update")]
    public static class AppGameUpdatePatch
    {
        private static int _frame;
        static void Postfix()
        {
            _frame++;
            if (_frame == 1 || _frame % 600 == 0)
            {
                var inst = SitOnChairPlugin.Instance;
                SitOnChairPlugin.DiagFile($"[hb] frame={_frame} Inst_RefNull={ReferenceEquals(inst, null)} mgrNonNull={SitOnChairManager.Inst != null}");
            }
            var mgr = SitOnChairManager.Inst;
            if (mgr == null) return;
            try { mgr.Tick(); }
            catch (Exception ex) { SitOnChairPlugin.DiagFile($"[tick-err] {ex.GetType().Name}: {ex.Message}"); }
        }
    }

    public class ManualLogSourceWrapper
    {
        private readonly BepInEx.Logging.ManualLogSource _l;
        public ManualLogSourceWrapper(BepInEx.Logging.ManualLogSource l) { _l = l; }
        public void Info(string m) => _l.LogInfo(m);
        public void Warn(string m) => _l.LogWarning(m);
        public void Error(string m) => _l.LogError(m);
    }

    public enum Phase { None, Sitting }

    public class SitAgent
    {
        public Phase phase = Phase.None;
        public float idleTimer;
        public float sitTimer;
        public string sitAnim;   // 此 NPC 正在用的坐姿 clip
    }

    public class SitOnChairManager
    {
        public static SitOnChairManager Inst;
        private readonly Dictionary<NpcController, SitAgent> _agents = new Dictionary<NpcController, SitAgent>();
        private float _npcScanAccum;
        private float _autoDiagAccum;
        private string[] _sitClipPrefs = { "chusheng_sit", "dazuo", "sit", "sitnew" };
        private string _sitClipsRaw;
        private bool _inputErrLogged;

        private SitOnChairPlugin P => SitOnChairPlugin.Instance;

        // 由 Harmony postfix（AppGame.Update）每幀呼叫
        public void Tick()
        {
            // plugin 是 MonoBehaviour，GameObject 被清後 Instance 變 Unity fake null（== null 回 true），
            // 但 C# 參考與 ConfigEntry 仍可用 → 用 ReferenceEquals 走真 null 語義。
            var p = P;
            if (ReferenceEquals(p, null)) return;

            // 診斷熱鍵
            try
            {
                if (Input.GetKeyDown(p.cfgDumpKey.Value)) DumpDiagnostics();
                if (Input.GetKeyDown(p.cfgProbeKey.Value)) ProbeNearbyNpcs();
            }
            catch (Exception ex)
            {
                if (!_inputErrLogged)
                {
                    _inputErrLogged = true;
                    SitOnChairPlugin.Log.Error($"[input] 讀按鍵失敗（可能是新版 Input System）：{ex.GetType().Name}: {ex.Message}");
                }
            }

            if (p.cfgAutoDiag.Value)
            {
                _autoDiagAccum += Time.unscaledDeltaTime;
                if (_autoDiagAccum >= p.cfgAutoDiagInterval.Value)
                {
                    _autoDiagAccum = 0f;
                    try { ProbeNearbyNpcs(); } catch (Exception ex) { SitOnChairPlugin.Log.Error($"[autodiag] {ex.Message}"); }
                }
            }

            if (!p.cfgEnabled.Value) { ReleaseAll(); return; }
            if (WorldManager.Instance == null || WorldManager.Instance.m_bLoadingScene) return;

            // 劇情中：全部起身停手
            if (WorldManager.Instance.m_IsInJuQing) { ReleaseAll(); return; }

            // 每幀：維持正在坐的 NPC（壓住 AI、被覆蓋就重播、被打擾就起身）
            MaintainSitters();

            // 評估間隔：決定誰該坐下、誰坐夠了
            _npcScanAccum += Time.deltaTime;
            if (_npcScanAccum < p.cfgNpcScanInterval.Value) return;
            float tickDt = _npcScanAccum;
            _npcScanAccum = 0f;
            ProcessNpcs(tickDt);
        }

        // ---- 每幀維持坐姿 ----
        private void MaintainSitters()
        {
            foreach (var kv in _agents)
            {
                var npc = kv.Key; var a = kv.Value;
                if (a.phase != Phase.Sitting) continue;
                if (ReferenceEquals(npc, null) || npc == null) continue; // 下一輪 ProcessNpcs 清理
                if (!IsEligible(npc) || IsDisturbed(npc)) { StandUp(npc, a); continue; }
                var ac = npc.m_AnimationComponent;
                if (ac != null && !ac.IsAnimName(a.sitAnim)) ac.PlayAnim(a.sitAnim, 0f, 0.99f);
                PauseNpcAi(npc, true);
            }
        }

        // ---- 評估間隔處理 ----
        private void ProcessNpcs(float dt)
        {
            var p = P;
            var dir = WorldManager.Instance.m_Dir;

            var npcs = new List<NpcController>();
            foreach (var v in dir.Values)
            {
                var npc = v as NpcController;
                if (npc != null) npcs.Add(npc);
            }

            // 清理已消失的 agent
            var gone = _agents.Keys.Where(k => k == null || !npcs.Contains(k)).ToList();
            foreach (var k in gone) { _agents.Remove(k); }

            int activeSitters = _agents.Count(kv => kv.Value.phase == Phase.Sitting);

            foreach (var npc in npcs)
            {
                try
                {
                    if (!_agents.TryGetValue(npc, out var a)) { a = new SitAgent(); _agents[npc] = a; }
                    activeSitters = StepNpc(npc, a, dt, activeSitters);
                }
                catch (Exception e)
                {
                    if (p.cfgVerbose.Value) SitOnChairPlugin.Log.Error($"[npc] 例外: {e.Message}");
                }
            }
        }

        private int StepNpc(NpcController npc, SitAgent a, float dt, int activeSitters)
        {
            var p = P;

            if (!IsEligible(npc) || IsDisturbed(npc))
            {
                if (a.phase == Phase.Sitting) { StandUp(npc, a); activeSitters--; }
                a.idleTimer = 0f;
                return activeSitters;
            }

            switch (a.phase)
            {
                case Phase.None:
                {
                    // 本體已把它設成坐姿 → 不插手
                    if (IsAlreadySitting(npc)) { a.idleTimer = 0f; break; }
                    // 必須靜止（nav 停止）
                    bool resting = npc.m_MoveComponent == null || npc.m_MoveComponent.IsNavStop();
                    if (!resting) { a.idleTimer = 0f; break; }

                    a.idleTimer += dt;
                    if (a.idleTimer < p.cfgIdleSeconds.Value) break;
                    if (activeSitters >= p.cfgMaxSitters.Value) break;

                    // 必須真的有坐姿 clip（HaveAnim，不被 PlayAnim 假回傳值騙）
                    string clip = PickSitClip(npc);
                    if (clip == null) { a.idleTimer = 0f; break; } // 此 NPC 沒坐姿動作，跳過

                    if (UnityEngine.Random.value > p.cfgChance.Value) { a.idleTimer = 0f; break; }

                    BeginSit(npc, a, clip);
                    activeSitters++;
                    break;
                }

                case Phase.Sitting:
                {
                    a.sitTimer += dt;
                    if (a.sitTimer >= p.cfgSitDuration.Value) { StandUp(npc, a); activeSitters--; }
                    // 每幀維持交給 MaintainSitters
                    break;
                }
            }
            return activeSitters;
        }

        private string PickSitClip(NpcController npc)
        {
            var ac = npc.m_AnimationComponent;
            if (ac == null) return null;
            RefreshSitClipPrefs();
            for (int i = 0; i < _sitClipPrefs.Length; i++)
            {
                try { if (ac.HaveAnim(_sitClipPrefs[i])) return _sitClipPrefs[i]; } catch { }
            }
            return null;
        }

        // 依 config 字串重建坐姿 clip 候選（只在字串變動時重建）
        private void RefreshSitClipPrefs()
        {
            var raw = P != null ? P.cfgSitAnims.Value : null;
            if (raw == _sitClipsRaw) return;
            _sitClipsRaw = raw;
            var list = (raw ?? "").Split(',').Select(s => s.Trim()).Where(s => s.Length > 0).ToArray();
            if (list.Length > 0) _sitClipPrefs = list;
        }

        private void BeginSit(NpcController npc, SitAgent a, string clip)
        {
            var p = P;
            // 壓住自身 AI、停掉休閒動作元件，避免蓋掉坐姿
            PauseNpcAi(npc, true);
            if (npc.m_NpcXiuXianAnimComponent != null) npc.m_NpcXiuXianAnimComponent.ExitXiuXian();

            // 0.99=定格在 clip 末端坐姿（仿 NpcController.cs:1257）
            npc.m_AnimationComponent.PlayAnim(clip, 0f, 0.99f);

            a.phase = Phase.Sitting;
            a.sitTimer = 0f;
            a.sitAnim = clip;
            if (p.cfgVerbose.Value) SitOnChairPlugin.Log.Info($"[sit] {npc.name} 坐下（{clip}）");
        }

        private void StandUp(NpcController npc, SitAgent a)
        {
            try
            {
                if (npc != null && a.phase == Phase.Sitting && npc.m_AnimationComponent != null)
                {
                    npc.m_AnimationComponent.BreakPrimAnm();
                    npc.m_AnimationComponent.EnterState(STATE_ID.ACTION_STATE_IDLE, true);
                }
                if (npc != null) PauseNpcAi(npc, false); // 恢復 AI
            }
            catch { }
            // 注意：P 是 fake-null 的 MonoBehaviour，必須用 ReferenceEquals，不能用 P != null（會回 false）
            if (!ReferenceEquals(P, null) && P.cfgVerbose.Value && npc != null)
                SitOnChairPlugin.Log.Info($"[sit] {npc.name} 起身");
            a.phase = Phase.None;
            a.idleTimer = 0f;
            a.sitTimer = 0f;
            a.sitAnim = null;
        }

        private void ReleaseAll()
        {
            foreach (var kv in _agents.ToList())
                if (kv.Key != null && kv.Value.phase == Phase.Sitting) StandUp(kv.Key, kv.Value);
        }

        // 暫停/恢復 NPC 自身 AI 腳本更新
        private void PauseNpcAi(NpcController npc, bool pause)
        {
            try { if (npc.m_AutomatAIScript != null) npc.m_AutomatAIScript.m_bUpdateable = !pause; }
            catch { }
        }

        // ---- 判斷 ----
        private bool IsEligible(NpcController npc)
        {
            var p = P;
            var e = npc.m_NpcEntity;
            if (e == null) return false;
            if (npc.m_MeshComponent == null || !npc.m_MeshComponent.IsLoadComplete()) return false;
            if (e.IsDead()) return false;
            if (!e.m_CanInteract) return false;
            if (!e.IsHumanOrAnimal() || e.IsAnimal()) return false; // 只讓人坐
            if (p.cfgOnlyRandomNpc.Value && !e.IsRandomNpc()) return false;
            return true;
        }

        private bool IsDisturbed(NpcController npc)
        {
            var e = npc.m_NpcEntity;
            if (npc.m_IsInCombat || npc.IsInSightCombat()) return true;
            if (e != null && (e.m_CompareWithPlayer || e.m_RobbedByPlayer)) return true;
            return false;
        }

        private bool IsAlreadySitting(NpcController npc)
        {
            var ac = npc.m_AnimationComponent;
            if (ac == null) return false;
            string cur = null;
            try { cur = ac.GetCurAnim(); } catch { }
            if (string.IsNullOrEmpty(cur)) return false;
            // 本體已設成坐姿（含 sit/sitnew/dazuo/chusheng_sit/chu_sit）
            return cur.IndexOf("sit", StringComparison.OrdinalIgnoreCase) >= 0
                || cur.IndexOf("dazuo", StringComparison.OrdinalIgnoreCase) >= 0;
        }

        // ---- 診斷 ----
        private void DumpDiagnostics()
        {
            if (WorldManager.Instance == null) { SitOnChairPlugin.Log.Info("[dump] 世界未就緒"); return; }
            Vector3 here = PlayerController.Instance != null ? PlayerController.Instance.Position : Vector3.zero;
            SitOnChairPlugin.Log.Info($"[dump] 玩家位置 {here}，目前坐著 {_agents.Count(kv => kv.Value.phase == Phase.Sitting)} 人");

            int nNpc = 0;
            foreach (var v in WorldManager.Instance.m_Dir.Values)
            {
                var npc = v as NpcController;
                if (npc == null || (npc.Position - here).sqrMagnitude > 225f) continue; // 15m 內
                nNpc++;
                _agents.TryGetValue(npc, out var a);
                string ph = a != null ? a.phase.ToString() : "-";
                SitOnChairPlugin.Log.Info($"   NPC {npc.name} dist={(npc.Position - here).magnitude:F1} elig={IsEligible(npc)} disturbed={IsDisturbed(npc)} sitClip={PickSitClip(npc) ?? "無"} phase={ph}");
            }
            SitOnChairPlugin.Log.Info($"[dump] 15m 內 NPC {nNpc} 個。");
        }

        private static readonly string[] SitProbeAnims =
            { "sit", "sitnew", "dazuo", "chu_sit", "chusheng_sit", "idle", "zhan" };

        // 用 HaveAnim 探測附近 NPC 真正擁有哪些坐姿 clip（PlayAnim 回傳值會說謊，見檔頭說明）
        private void ProbeNearbyNpcs()
        {
            if (WorldManager.Instance == null || PlayerController.Instance == null) return;
            Vector3 here = PlayerController.Instance.Position;
            var cand = new List<NpcController>();
            foreach (var v in WorldManager.Instance.m_Dir.Values)
            {
                var npc = v as NpcController;
                if (npc == null || !IsEligible(npc)) continue;
                if ((npc.Position - here).sqrMagnitude > 225f) continue;
                cand.Add(npc);
            }
            if (cand.Count == 0) { SitOnChairPlugin.Log.Warn("[probe] 附近沒有合格 NPC"); return; }
            cand = cand.OrderBy(n => (n.Position - here).sqrMagnitude).Take(8).ToList();

            var haveCount = new int[SitProbeAnims.Length];
            foreach (var npc in cand)
            {
                var ac = npc.m_AnimationComponent;
                if (ac == null) continue;
                string def = "?", sav = "?", cur = "?";
                try { def = npc.m_NpcEntity.m_NpcPrototype.defaultAnim; } catch { }
                try { sav = npc.m_NpcEntity.saveAnim; } catch { }
                try { cur = ac.GetCurAnim(); } catch { }
                var sb = new System.Text.StringBuilder($"[probe] {npc.name} def='{def}' save='{sav}' cur='{cur}' HAVE:");
                for (int i = 0; i < SitProbeAnims.Length; i++)
                {
                    bool h = false;
                    try { h = ac.HaveAnim(SitProbeAnims[i]); } catch { }
                    if (h) { haveCount[i]++; sb.Append(" " + SitProbeAnims[i]); }
                }
                try
                {
                    if (npc.m_NpcXiuXianAnimComponent != null)
                    {
                        var anims = npc.m_NpcXiuXianAnimComponent.GetAllAnims();
                        if (anims != null && anims.Count > 0)
                            sb.Append($" | XiuXian=[{string.Join(",", anims)}]");
                    }
                }
                catch { }
                SitOnChairPlugin.Log.Info(sb.ToString());
            }
            var stat = new System.Text.StringBuilder("[probe] HaveAnim 統計：");
            for (int i = 0; i < SitProbeAnims.Length; i++) stat.Append($"{SitProbeAnims[i]}={haveCount[i]}/{cand.Count} ");
            SitOnChairPlugin.Log.Info(stat.ToString());
            SitOnChairPlugin.DiagFile(stat.ToString());
        }
    }
}
