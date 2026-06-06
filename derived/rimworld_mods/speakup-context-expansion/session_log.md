# session_log — speakup-context-expansion

- 讀分析 00/01/extension_points 與 SpeakUp 原始碼，鎖定 B1/B3 改碼接點（ExtraGrammarUtility.ExtraRules）。
- 查證三情境未被 vanilla SpeakUp 覆蓋：威脅/drafted 完全沒有；食物只有個人 mood thought（NeedFood/饥饿）非殖民地存糧；死亡只有 DeadMansApparel 間接提及。三者皆採用，無替換。
- 以 monodis 驗證所有要用的 API 存在於本機 Assembly-CSharp.dll：Map.dangerWatcher.DangerRating(StoryDanger none/low/high)、Pawn.Drafted、ResourceCounter.TotalHumanEdibleNutrition、MapPawns.FreeColonistsCount、Pawn.Kill(Nullable<DamageInfo>,Hediff)、Pawn.IsColonist、TickManager.TicksGame、GenDate.TicksPerDay；SpeakUp.DialogManager.Initiator/Recipient 為 public static 欄位。
- 決定注入機制＝Harmony Postfix SpeakUp.ExtraGrammarUtility.ExtraRules()（外掛式，不改原 mod，沿用其 r_logentry 管線與數值約束）。
- 建立 mod：About.xml（pas.speakup.contextexpansion, loadAfter SpeakUp/Harmony）、4 個 .cs（Mod 入口/Injector/DeathTracker GameComponent/Pawn.Kill patch）、csproj(net48)、zzz_context_expansion.xml 台詞、PROJECT.md、docs/context_variables.md。
- dotnet build -c Release 成功（0 警告 0 錯誤），輸出 1.6/Assemblies/SpeakUpContextExpansion.dll；assemblyref 乾淨（mscorlib/Assembly-CSharp/SpeakUp/0Harmony）。修過一處：GenDate 在 RimWorld 命名空間，補 using RimWorld。
- 未做：實機 in-game 驗證（本機未啟動遊戲）；邏輯靠 API 對照＋編譯保證。
