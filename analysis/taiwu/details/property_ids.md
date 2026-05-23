# 角色屬性 ID 對照表（PropertyId 0–111）

> 日期：2026-05-22
> 來源：`~/repo/pas/projects/taiwu/MoreFactionCombatSkills/CombatSkills.yml` 標頭註解（行 1–112）對照 `~/dev/taiwu-src/Assembly-CSharp/` 內屬性 enum。
> 用途：寫武功/特效/裝備 mod 時，凡是用到 `PropertyId`（如 `UsingRequirement`、`PropertyAddList`、`AffectedDataKey`、`EquipAddPropertyDict`）的地方都查這張表。

## 使用情境

- **`UsingRequirement`**（CombatSkillItem）：`[[PropertyId, Value], ...]`，例如 `[[0, 160], [87, 300]]` = 需要臂力 160 + 劍法**造詣** 300。
  - ⚠ **需求只能用「基礎屬性 / 造詣 Attainment」，不可用「資質 Qualification」。** 後端 `Character.GetPropertyValue(ECharacterPropertyReferencedType)` 不支援 Qualification* 系列，放進 `UsingRequirement` 會在計算技能顯示資料時拋 `Cannot get value of character property type Qualification...` 並令 GameData 後端進程**崩潰斷線**（2026-05-23 實機踩雷）。劍法請用 `87 AttainmentSword`（劍法造詣）而非 `73 QualificationSword`（劍法資質）。參考 mod 佛王之劍系列即用 `87`。
  - 此表的 PropertyId 即 `ECharacterPropertyReferencedType` 列舉值（`~/dev/taiwu-src/backend/GameData.Shared/ECharacterPropertyReferencedType.cs`，值 = 行號−3）。
- **`PropertyAddList` / `EquipAddPropertyDict`**：裝備該武功時對角色屬性的加成。
- **特效類別內** `new AffectedDataKey(charId, propertyId, ...)`：動態修改某屬性。

## 完整對照表

### 六大基礎屬性（0–5）
| ID | 英文 | 中文 |
|---:|---|---|
| 0 | Strength | 臂力 |
| 1 | Dexterity | 靈敏 |
| 2 | Concentration | 定力 |
| 3 | Vitality | 體質 |
| 4 | Energy | 根骨 |
| 5 | Intelligence | 悟性 |

### 戰鬥命中/閃避/穿透（6–27）
| ID | 英文 | 說明 |
|---:|---|---|
| 6 | HitRateStrength | 力道命中 |
| 7 | HitRateTechnique | 技巧命中 |
| 8 | HitRateSpeed | 身法命中 |
| 9 | HitRateMind | 心神命中 |
| 10 | PenetrateOfOuter | 外功穿透 |
| 11 | PenetrateOfInner | 內功穿透 |
| 12 | AvoidRateStrength | 力道閃避 |
| 13 | AvoidRateTechnique | 技巧閃避 |
| 14 | AvoidRateSpeed | 身法閃避 |
| 15 | AvoidRateMind | 心神閃避 |
| 16 | PenetrateResistOfOuter | 外功抗穿透 |
| 17 | PenetrateResistOfInner | 內功抗穿透 |
| 18 | RecoveryOfStance | 架勢回復 |
| 19 | RecoveryOfBreath | 提氣回復 |
| 20 | MoveSpeed | 移動速度 |
| 21 | RecoveryOfFlaw | 破綻回復 |
| 22 | CastSpeed | 出招速度 |
| 23 | RecoveryOfBlockedAcupoint | 點穴回復 |
| 24 | WeaponSwitchSpeed | 換武器速度 |
| 25 | AttackSpeed | 攻擊速度 |
| 26 | InnerRatio | 內息比例 |
| 27 | RecoveryOfQiDisorder | 內息紊亂回復 |

### 抗毒（28–33）
| ID | 英文 | 中文 |
|---:|---|---|
| 28 | ResistOfHotPoison | 抗生毒/烈毒 |
| 29 | ResistOfGloomyPoison | 抗幽毒 |
| 30 | ResistOfColdPoison | 抗寒毒 |
| 31 | ResistOfRedPoison | 抗赤毒 |
| 32 | ResistOfRottenPoison | 抗腐毒 |
| 33 | ResistOfIllusoryPoison | 抗奇毒 |

### 文藝/雜學資質 Qualification（34–49）
| ID | 英文 | 中文 |
|---:|---|---|
| 34 | QualificationMusic | 琴 資質 |
| 35 | QualificationChess | 棋 資質 |
| 36 | QualificationPoem | 書 資質 |
| 37 | QualificationPainting | 畫 資質 |
| 38 | QualificationMath | 術 資質 |
| 39 | QualificationAppraisal | 品鑑 資質 |
| 40 | QualificationForging | 鍛造 資質 |
| 41 | QualificationWoodworking | 木工 資質 |
| 42 | QualificationMedicine | 醫 資質 |
| 43 | QualificationToxicology | 毒 資質 |
| 44 | QualificationWeaving | 織錦 資質 |
| 45 | QualificationJade | 玉 資質 |
| 46 | QualificationTaoism | 道 資質 |
| 47 | QualificationBuddhism | 佛 資質 |
| 48 | QualificationCooking | 廚 資質 |
| 49 | QualificationEclectic | 雜學 資質 |

### 文藝/雜學造詣 Attainment（50–65）
| ID | 英文 | 中文 |
|---:|---|---|
| 50 | AttainmentMusic | 琴 造詣 |
| 51 | AttainmentChess | 棋 造詣 |
| 52 | AttainmentPoem | 書 造詣 |
| 53 | AttainmentPainting | 畫 造詣 |
| 54 | AttainmentMath | 術 造詣 |
| 55 | AttainmentAppraisal | 品鑑 造詣 |
| 56 | AttainmentForging | 鍛造 造詣 |
| 57 | AttainmentWoodworking | 木工 造詣 |
| 58 | AttainmentMedicine | 醫 造詣 |
| 59 | AttainmentToxicology | 毒 造詣 |
| 60 | AttainmentWeaving | 織錦 造詣 |
| 61 | AttainmentJade | 玉 造詣 |
| 62 | AttainmentTaoism | 道 造詣 |
| 63 | AttainmentBuddhism | 佛 造詣 |
| 64 | AttainmentCooking | 廚 造詣 |
| 65 | AttainmentEclectic | 雜學 造詣 |

### 武學資質 Qualification（66–79）
| ID | 英文 | 中文 |
|---:|---|---|
| 66 | QualificationNeigong | 內功 資質 |
| 67 | QualificationPosing | 身法 資質 |
| 68 | QualificationStunt | 絕技 資質 |
| 69 | QualificationFistAndPalm | 拳掌 資質 |
| 70 | QualificationFinger | 指法 資質 |
| 71 | QualificationLeg | 腿法 資質 |
| 72 | QualificationThrow | 暗器 資質 |
| 73 | QualificationSword | **劍法 資質** |
| 74 | QualificationBlade | 刀法 資質 |
| 75 | QualificationPolearm | 長兵 資質 |
| 76 | QualificationSpecial | 奇門 資質 |
| 77 | QualificationWhip | 軟鞭 資質 |
| 78 | QualificationControllableShot | 御射 資質 |
| 79 | QualificationCombatMusic | 樂理（戰鬥音）資質 |

### 武學造詣 Attainment（80–93）
| ID | 英文 | 中文 |
|---:|---|---|
| 80 | AttainmentNeigong | 內功 造詣 |
| 81 | AttainmentPosing | 身法 造詣 |
| 82 | AttainmentStunt | 絕技 造詣 |
| 83 | AttainmentFistAndPalm | 拳掌 造詣 |
| 84 | AttainmentFinger | 指法 造詣 |
| 85 | AttainmentLeg | 腿法 造詣 |
| 86 | AttainmentThrow | 暗器 造詣 |
| 87 | AttainmentSword | **劍法 造詣** |
| 88 | AttainmentBlade | 刀法 造詣 |
| 89 | AttainmentPolearm | 長兵 造詣 |
| 90 | AttainmentSpecial | 奇門 造詣 |
| 91 | AttainmentWhip | 軟鞭 造詣 |
| 92 | AttainmentControllableShot | 御射 造詣 |
| 93 | AttainmentCombatMusic | 樂理 造詣 |

### 賦性 Personality（94–100）
| ID | 英文 | 中文 |
|---:|---|---|
| 94 | PersonalityCalm | 冷靜 |
| 95 | PersonalityClever | 聰穎 |
| 96 | PersonalityEnthusiastic | 熱情 |
| 97 | PersonalityBrave | 勇壯 |
| 98 | PersonalityFirm | 堅毅 |
| 99 | PersonalityLucky | 福源 |
| 100 | PersonalityPerceptive | 通透 |

### 其他（101–111）
| ID | 英文 | 中文/說明 |
|---:|---|---|
| 101 | Attraction | 魅力 |
| 102 | Fertility | 生育 |
| 103 | HobbyChangingPeriod | 喜好變更週期 |
| 104 | MaxHealth | 氣血上限 |
| 105 | MaxNeili | 內力上限 |
| 106 | AttainmentDivinePower | 神術 造詣 |
| 107 | AttainmentGhostTechnique | 鬼術 造詣 |
| 108 | LifeSkillBookReadEfficiency | 雜學書閱讀效率 |
| 109 | CombatSkillBookReadEfficiency | 武學書閱讀效率 |
| 110 | CombatSkillProficiency | 武學熟練度 |
| 111 | CricketLuckPoint | 鬥蟋蟀運勢點 |

> 共 **112 個屬性**（0–111）。這也是 §解剖報告 §6.1 中 `new short[112]` 的來源——`EquipAddPropertyDict` 每個武功配一條長度 112 的屬性加成陣列。

## 對劍法 mod 最相關的 ID

| 用途 | ID |
|---|---:|
| 劍法資質（學習門檻） | 73 |
| 劍法造詣（威力換算） | 87 |
| 臂力（外功傷害） | 0 |
| 靈敏 | 1 |
| 氣血上限 | 104 |
| 內力上限 | 105 |
| 冷靜/勇壯/堅毅（特效條件常用） | 94 / 97 / 98 |
| 福源 | 99 |

> 注意中文譯名部分為推定（YAML 標頭原註解有缺漏或簡寫，例如「臀力」應為「臂力」、「合到」應為「通透」、「造紙」是 OCR/輸入殘留）。實機驗證以 `LanguageKey` 對應的字串表為準。
