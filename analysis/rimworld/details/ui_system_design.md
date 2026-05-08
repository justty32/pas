# RimWorld ARPG UI 系統設計：技能欄與天賦樹

RimWorld 使用 Unity 的 **IMGUI (Immediate Mode GUI)** 系統。所有 UI 繪製邏輯必須在每一幀執行。實作 ARPG UI 需要結合 `Window` 類別與自定義的 `Gizmo`。

## 1. 快捷技能欄 (Action Bar)

在 RimWorld 中，底部菜單通常由 `Gizmo` 組成。ARPG 技能欄可以透過擴充 `Pawn.GetGizmos` 或建立一個常駐的 `Window` 實作。

### 技術方案：自定義 Window
*   **特性**: 可拖動、自定義背景、支持熱鍵。
*   **實作細節**:
    *   建立一個 `MainButtonWorker` 在底部導航列增加開關按鈕。
    *   建立 `Window_ActionBar` 類別。
    *   使用 `Widgets.ButtonImage` 繪製技能圖示。
    *   使用 `TooltipHandler.TipRegion` 顯示技能說明。
    *   **冷卻效果**: 透過計算 `CooldownTicksLeft / MaxCooldownTicks` 的比例，使用 `GUI.DrawTexture` 覆蓋一個半透明遮罩。

## 2. 天賦樹系統 (Talent Tree)

這是最複雜的 UI 部分，需要處理節點連線、解鎖邏輯與滾動視圖。

### 技術方案：節點圖表
*   **佈局**: 建議使用固定的座標體系定義節點位置（如：Node A 在 100, 200）。
*   **實作細節**:
    *   **滾動區域**: 使用 `Widgets.BeginScrollView` 與 `Widgets.EndScrollView`。
    *   **連線繪製**: 使用 `Widgets.DrawLine` 或繪製拉伸的紋理。
    *   **狀態區分**: 
        *   *已解鎖*: 彩色。
        *   *可購買*: 灰色但有高亮邊框。
        *   *鎖定中*: 帶鎖頭圖示。

---

# C# UI 代碼範例

檔案路徑: `analysis/rimworld/details/examples/arpg_ui_snippets.cs`

```csharp
using System;
using System.Collections.Generic;
using UnityEngine;
using Verse;
using RimWorld;

namespace RimWorldARPG.UI
{
    // 範例 1: 快捷技能欄窗口
    public class Window_ActionBar : Window
    {
        public override Vector2 InitialSize => new Vector2(400f, 80f);

        public Window_ActionBar()
        {
            this.absorbInputAroundWindow = false; // 允許點擊窗口外部（重要：ARPG 需要邊走邊看技能）
            this.preventCameraMotion = false;
            this.draggable = true;
            this.doCloseX = false;
        }

        public override void DoWindowContents(Rect inRect)
        {
            Pawn pawn = Find.Selector.SingleSelectedPawn;
            if (pawn == null) return;

            float slotSize = 60f;
            float margin = 5f;

            for (int i = 0; i < 5; i++)
            {
                Rect slotRect = new Rect(i * (slotSize + margin), 0f, slotSize, slotSize);
                Widgets.DrawBoxSolid(slotRect, new Color(0.2f, 0.2f, 0.2f, 0.8f));
                
                // 模擬技能圖示
                if (Widgets.ButtonInvisible(slotRect))
                {
                    Log.Message($"觸發技能 {i + 1}");
                }

                // 繪製冷卻遮罩 (假設冷卻中)
                float cooldownPct = 0.4f; // 40%
                Rect cooldownRect = new Rect(slotRect.x, slotRect.y + slotRect.height * (1f - cooldownPct), slotRect.width, slotRect.height * cooldownPct);
                Widgets.DrawBoxSolid(cooldownRect, new Color(1f, 1f, 1f, 0.3f));
            }
        }
    }

    // 範例 2: 天賦樹節點資料結構
    public class TalentNode
    {
        public string label;
        public Vector2 pos;
        public List<TalentNode> children = new List<TalentNode>();
        public bool unlocked;

        public void Draw(Rect container)
        {
            Rect nodeRect = new Rect(pos.x, pos.y, 80f, 40f);
            if (Widgets.ButtonText(nodeRect, label))
            {
                unlocked = true;
            }

            // 繪製到子節點的連線
            foreach (var child in children)
            {
                Widgets.DrawLine(nodeRect.center, new Vector2(child.pos.x + 40, child.pos.y + 20), Color.white, 2f);
            }
        }
    }
}
```
