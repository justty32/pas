# 魔紋系統：從煉金到人體改造的 C# 實作指南

魔紋系統的核心在於「數據的傳遞」：從**素材 (ThingDef)** -> **汁液 (ThingWithComps)** -> **魔紋 (Hediff)**。

## 1. 程序化汁液：CompMagicInk

普通的 `ThingDef` 是靜態的，但「魔紋汁液」需要根據熬煮的素材與品質動態生成屬性。

```csharp
public class CompMagicInk : ThingComp
{
    // 紀錄該汁液包含的屬性加成 (例如: MoveSpeed +0.2)
    public List<StatModifier> statOffsets = new List<StatModifier>();
    public float qualityMultiplier = 1.0f;

    public override void PostExposeData()
    {
        base.PostExposeData();
        Scribe_Collections.Look(ref statOffsets, "statOffsets", LookMode.Deep);
        Scribe_Values.Look(ref qualityMultiplier, "qualityMultiplier", 1.0f);
    }

    public override string TransformLabel(string label)
    {
        return label + " (已熬煮)";
    }
}
```

## 2. 動態屬性 Hediff：Hediff_MagicTattoo

這是最關鍵的部分。RimWorld 的 `Hediff_Implant` 通常只讀取 XML。我們需要自定義一個類別，在初始化時從「汁液」中抓取數據。

```csharp
public class Hediff_MagicTattoo : Hediff_Implant
{
    // 儲存從汁液繼承來的屬性
    public List<StatModifier> inheritedOffsets = new List<StatModifier>();

    // 覆寫屬性偏移量，讓系統能讀取到我們的動態數據
    public override IEnumerable<StatModifier> StatOffsets
    {
        get
        {
            if (inheritedOffsets == null) yield break;
            foreach (var offset in inheritedOffsets)
            {
                yield return offset;
            }
        }
    }

    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Collections.Look(ref inheritedOffsets, "inheritedOffsets", LookMode.Deep);
    }
}
```

## 3. 手術邏輯：將汁液轉化為魔紋

我們需要自定義一個 `RecipeWorker` 來處理手術。

```csharp
public class Recipe_ApplyMagicTattoo : Recipe_Surgery
{
    public override void ApplyOnPawn(Pawn pawn, BodyPartRecord part, Pawn billDoer, List<Thing> ingredients, Bill bill)
    {
        // 1. 找到放入手術台的汁液
        Thing inkThing = ingredients.FirstOrDefault(t => t.TryGetComp<CompMagicInk>() != null);
        if (inkThing == null) return;

        CompMagicInk inkComp = inkThing.TryGetComp<CompMagicInk>();

        // 2. 在 Pawn 身上建立魔紋 Hediff
        Hediff_MagicTattoo tattoo = (Hediff_MagicTattoo)HediffMaker.MakeHediff(recipe.addsHediff, pawn, part);
        
        // 3. 數據轉移：將汁液的屬性複製到 Hediff 中
        tattoo.inheritedOffsets = new List<StatModifier>();
        foreach (var mod in inkComp.statOffsets)
        {
            tattoo.inheritedOffsets.Add(new StatModifier { stat = mod.stat, value = mod.value * inkComp.qualityMultiplier });
        }

        pawn.health.AddHediff(tattoo, part);
    }
}
```

## 4. 視覺渲染：Harmony 注入

要在 Pawn 身上畫出紋身，我們需要攔截 `PawnRenderer`。

```csharp
[HarmonyPatch(typeof(PawnRenderer), "RenderPawnAt")]
public static class Patch_RenderTattoo
{
    [HarmonyPostfix]
    public static void Postfix(PawnRenderer __instance, Vector3 drawLoc, Rot4 rotation, bool portrait)
    {
        Pawn pawn = (Pawn)AccessTools.Field(typeof(PawnRenderer), "pawn").GetValue(__instance);
        
        // 檢查是否有魔紋
        var tattoo = pawn.health.hediffSet.GetFirstHediffOfDef(YourDefOf.MagicTattoo) as Hediff_MagicTattoo;
        if (tattoo != null)
        {
            // 根據旋轉角度選擇貼圖
            Graphic graphic = GraphicDatabase.Get<Graphic_Multi>("UI/Tattoos/MyTattoo", ShaderDatabase.Cutout, Vector2.one, Color.white);
            
            // 計算繪製矩陣 (略微抬高 Y 軸以防 Z-fighting)
            Vector3 tattooLoc = drawLoc + new Vector3(0, 0.01f, 0);
            graphic.Draw(tattooLoc, rotation, pawn);
        }
    }
}
```

## 5. 技術重點總結

*   **StatModifier 的深度拷貝**: `StatModifier` 是引用類型，賦值時務必建立新實例，否則修改汁液會影響到所有已紋身的 Pawn。
*   **存檔一致性**: 務必在 `ExposeData` 中使用 `LookMode.Deep` 處理屬性列表，否則讀檔後魔紋會變成空殼。
*   **性能**: `StatOffsets` 會頻繁被呼叫，儘量避免在 `get` 訪問器中進行複雜運算，數據應在手術時預先計算好。

---
*文件路徑: analysis/rimworld/details/magic_tattoo_implementation.md*
