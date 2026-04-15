# 🤖 Slay The Robot: 高階開發指南 (Senior Guide)

歡迎進入進階開發階段！如果你已經掌握了如何透過 JSON 建立基本的卡牌和敵人，這篇指南將帶領你深入了解 **Slay The Robot** 的底層邏輯，教你如何撰寫 GDScript 來實作複雜的遊戲機制。

---

## 1. 撰寫自定義行動 (Custom Actions)

當內建的行動（如傷害、格擋）不足以滿足需求時，你需要撰寫自己的 `Action`。

### 步驟：
1. 在 `scripts/actions/` 下建立一個新的 GDScript。
2. 繼承 `BaseAction` 或 `BaseAsyncAction` (如果你需要等待動畫或使用者輸入)。

### 範例：隨機丟棄手牌 (ActionDiscardRandom)
```gdscript
extends BaseAction
# scripts/actions/player_actions/ActionDiscardRandom.gd

func perform_action() -> void:
    # 1. 獲取參數（可以從 JSON 傳入）
    var discard_count = get_action_value("discard_count", 1)
    
    # 2. 獲取玩家引用
    var player = Global.get_player()
    if not player: return

    # 3. 執行邏輯
    for i in range(discard_count):
        player.hand.discard_random_card()

    # 4. 處理延遲（讓玩家看清楚發生了什麼）
    await Global.get_tree().create_timer(time_delay).timeout
```

---

## 2. 狀態效果與攔截器 (Status Effects & Interceptors)

這是框架最強大的部分。**攔截器 (Interceptor)** 允許你在行動執行前「攔截」並修改它的數值。例如，「力量」Buff 就是一個攔截器，它會增加所有「傷害行動」的傷害值。

### 建立一個具有攔截器的狀態：
1. **定義 Interceptor**: 繼承 `BaseActionInterceptor`。
2. **定義 Status Data**: 在 JSON 中連結這個 Interceptor。

### 範例：雙倍傷害狀態
在 `scripts/action_interceptors/InterceptorDoubleDamage.gd`:
```gdscript
extends BaseActionInterceptor

func process_action_interception(processor: ActionInterceptorProcessor, _preview_mode: bool) -> int:
    # 檢查這是不是一個傷害行動
    var damage = processor.get_shadowed_action_values("damage", 0)
    if damage > 0:
        # 將傷害翻倍並存回 processor
        processor.shadowed_action_values["damage"] = damage * 2
    
    return ACTION_ACCEPTENCES.CONTINUE
```

然後在你的 `status_effect.json` 中，將 `action_interceptor_id` 指向對應的資料。

---

## 3. 遺物系統與信號 (Artifacts & Signals)

遺物通常透過監聽遊戲中的 **信號 (Signals)** 來觸發。

### 範例：擊殺時抽牌遺物
```gdscript
extends BaseArtifact
# scripts/artifacts/ArtifactDrawOnKill.gd

func _connect_signals() -> void:
    # 監聽全局信號
    Signals.enemy_died.connect(_on_enemy_died)

func _on_enemy_died(_enemy: BaseCombatant) -> void:
    # 觸發行動：抽 1 張牌
    var action_data = [{
        Scripts.ACTION_DRAW_GENERATOR: { "draw_amount": 1 }
    }]
    var actions = ActionGenerator.create_actions(Global.get_player(), null, [], action_data, null)
    ActionHandler.add_actions(actions)
```

---

## 4. 進階資料補丁 (Data Patching)

當你想修改原版遊戲的內容（例如：加強原有的「打擊」卡）而不直接修改原檔時，請使用 `patch_data`。

### 範例：修改原版卡片
```json
{
    "patch_data": {
        "card_values": "merge"
    },
    "properties": {
        "object_id": "card_strike",
        "card_values": {
            "damage": 99
        }
    }
}
```
`patch_data` 的類型可以是 `overwrite` (預設), `merge` (合併字典), 或 `append` (加入陣列)。

---

## 5. 核心流程控制：ActionHandler

所有的遊戲邏輯都是透過 `ActionHandler` 這個 Singleton 管理的。它維護了一個 **行動堆疊 (Action Stack)**。

- **`ActionHandler.add_actions(actions)`**: 將新行動放到堆疊頂端。
- **即時執行**: 如果你希望某個行動不經過堆疊立即執行，可以直接呼叫 `action.perform_action()`，但請小心這可能會打斷目前的動畫流程。

---

## 6. 調試與日誌 (Debug)

利用 `DebugLogger` 來追蹤行動的執行過程：
```gdscript
DebugLogger.log_message("執行了自定義行動", DebugLogger.LOG_CHANNELS.ACTIONS)
```
你可以在遊戲內的調試面板中看到不同頻道的日誌輸出。

---

## 結語

深入開發的關鍵在於閱讀 `scripts/actions/BaseAction.gd` 和 `autoload/ActionHandler.gd`。理解了行動如何被攔截、修改與執行後，你就能創造出無限可能的機制！

如果有任何問題，建議參考 `scripts/action_interceptors/` 下的 `InterceptorVulnerable.gd` (易傷效果) 作為實戰範例。
