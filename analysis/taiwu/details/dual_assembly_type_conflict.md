# 編譯 mod 的型別解析：版本差異與 API 漂移（含一段已作廢的舊版歧路）

> 日期：2026-05-22 起，2026-05-23 重大訂正
> 場景：編譯 `~/repo/pas/projects/taiwu/MySwordArt/`（流光劍法 mod）。
> **最重要教訓：一切型別綁定／命名空間都必須以「實裝遊戲版本的 DLL」為準。**反編譯源（`~/dev/taiwu-src/`）與參考 mod 的 IL 只在「同版」時才可信。

---

## 0. 結論先講（針對現裝 **0.0.79.60**）

- 後端、前端**都用普通引用即可，不需要任何 `extern alias`**——現版 `GameData.dll` 不再重複定義 Config 型別，CS0433 衝突不存在。
- 正確的參考資產引用：
  - 後端引用 `Backend/` 下的 `GameData.dll`、`GameData.Shared.dll`、`GameData.Utilities.dll`、`GameData.Combat.Math.dll`、`Redzen.dll`。
  - 前端引用 `Managed/Assembly-CSharp.dll` ＋ **`Backend/` 下的** `GameData.Shared.dll`、`GameData.Utilities.dll`（netstandard，`Managed/` 沒有，可被 net48 引用）。
- 型別歸屬（現版，與同版參考 mod IL 一致）：
  | 型別 | 命名空間 | Assembly |
  |---|---|---|
  | `CombatSkillItem`/`SpecialEffectItem`/`SkillBookItem`/`CombatSkill`/`SpecialEffect` | `Config` | **GameData.Shared** |
  | `ConfigData<,>`/`ConfigItem<,>` | `Config.Common` | **GameData.Shared** |
  | `CombatSkillKey` | `GameData.Domains.CombatSkill` | **GameData.Shared** |
  | `ModInfo` | `GameData.Domains.Mod` | **GameData.Shared**（前端取 mod 目錄用） |
  | `EDataModifyType` | **`GameData.Combat.Math`** | **GameData.Combat.Math** |
  | `AdaptableLog` | `GameData.Utilities` | **GameData.Utilities** |
  | `CombatSkillEffectBase`/`SpecialEffectBase`/`DomainManager`/`Events`/`DataContext`/`CombatCharacter`/`AffectedDataKey` | `GameData.*` | **GameData**(dll) |
- csproj 仍須：`<Compile Include="**/*.cs" Exclude="obj/**/*.cs;bin/**/*.cs" />`（否則 obj 內自動生成的 `*.AssemblyAttributes.cs` 造成 `CS0579`）。

## 1. 各檔 using 重點（現版）
- `Backend/Effects/LiuGuangSwordIntent.cs`：類別宣告在 `namespace GameData.Domains.SpecialEffect.MySwordArt`，可靠外層命名空間看到 `AffectedDataKey`/`SpecialEffectBase`；但 **`EDataModifyType` 在 `GameData.Combat.Math`，必須額外 `using GameData.Combat.Math;`**（舊版此 enum 在 `GameData.Domains.SpecialEffect`，靠外層自動可見，故舊版沒寫 using 也能編——這是漂移陷阱）。
- `Shared/DataConfigAppender.cs`：需 `using Config;`＋`using Config.Common;`（後者供 `ConfigData<,>`/`ConfigItem<,>`）。
- `Frontend/Plugin.cs`：`using GameData.Domains.Mod;`＋普通引用 GameData.Shared，即可解析 `ModInfo`。

## 2. 版本漂移實例（這次踩到的雷）
| 項目 | 舊版 0.0.76.43 | 現裝 0.0.79.60 |
|---|---|---|
| Config 型別是否在 `GameData.dll` 重複定義 | **是**（→ CS0433，需 extern alias） | **否**（普通引用即可） |
| `CombatSkillKey` 來源 | `GameData.dll` | `GameData.Shared` |
| `EDataModifyType` 命名空間 | `GameData.Domains.SpecialEffect` | `GameData.Combat.Math` |
| `ModInfo`（前端） | 在 `Assembly-CSharp` | 在 `GameData.Shared` |
| `AdaptableLog` | 在 `GameData.Utilities` 與 `GameData.dll` 重複 | 僅 `GameData.Utilities` |

實機症狀對照：
- 對舊版編譯後在 **0.0.76.43** 跑 → 前端 `TypeLoadException`（Config 型別佈局對不上）。
- 同一 dll 在 **0.0.79.60** 跑 → 前端 `TypeLoadException: Could not resolve 'GameData.Domains.Mod.ModInfo' in assembly 'Assembly-CSharp'`（ModInfo 已移到 GameData.Shared）。
- → 唯一正解：**對實裝版本的 DLL 重新編譯**。

## 3. 已作廢的舊版歧路（保留以備將來又遇到重複型別）
若哪天又裝到「`GameData.dll` 與 `GameData.Shared.dll` 重複定義 Config 型別」的版本而撞 CS0433，可用 extern alias 解：
- csproj 對 `GameData.Shared` 加 `<Aliases>shared</Aliases>`、對 `GameData.Utilities` 加 `<Aliases>util</Aliases>`，全域留 `GameData.dll`；
- 用一份共用 `GlobalUsings.cs`：`extern alias shared; extern alias util; global using shared::Config.Common; global using CombatSkillItem = shared::Config.CombatSkillItem; ...; global using AdaptableLog = util::GameData.Utilities.AdaptableLog;`
- 注意 `AdaptableLog` 無法只靠命名空間消歧義（`GameData.Utilities` 這個命名空間在兩個 assembly 都有），必須用 assembly 別名。
**但現裝 0.0.79.60 不需要這套，已全數移除。**

## 4. 驗證方式
用 `ikdasm <dll> | grep -oE '\[Assembly\]Namespace.Type'` 查自家 dll 的 typeref 綁定，與「同版」參考 mod 比對。本 mod 現已對齊（見 §0 表）。前後端皆 `Build succeeded 0/0`。
