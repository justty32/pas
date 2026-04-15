# 🤖 Slay The Robot: Godot 卡牌遊戲開發新手指南

歡迎來到 **Slay The Robot** 框架！這是一個專為 Godot 4 打造的開源框架，旨在簡化類似《殺戮尖塔》(Slay the Spire) 的 Roguelike 卡牌遊戲開發。

本教程將帶領 Godot 初學者一步步了解如何使用此框架打造自己的第一張卡片、敵人和角色。

---

## 1. 核心概念：資料驅動 (Data-Driven)

這個框架最大的特點是 **資料驅動**。這意味著你不需要為每一張卡片寫程式碼。相反，你只需要撰寫 **JSON 檔案** 來定義卡片的數值和行為，框架會自動載入並處理它們。

### 關鍵術語：
- **Action (行動)**：遊戲邏輯的原子單位（例如：造成傷害、獲得格擋、抽牌）。
- **Validator (驗證器)**：決定卡片是否可以使用的條件（例如：手牌中是否有 3 張牌）。
- **Interceptor (攔截器)**：修改行動的行為（例如：力量 Buff 會增加傷害行動的值）。

---

## 2. 專案架構說明

在你開始之前，先熟悉一下資料夾：

- `external/mods/`：**這是你放自定義內容的地方。** 建議將你的所有修改都放在一個新模組資料夾中。
- `scripts/actions/`：存放所有的行動邏輯。
- `autoload/Scripts.gd`：這個檔案像是一個目錄，定義了所有行動的常數路徑。
- `scenes/ui/`：如果你想修改 UI 介面，這裡有卡片和戰鬥畫面的場景。

---

## 3. 實戰：建立你的第一張卡片

我們將使用 JSON 格式來建立一張新卡片。請在 `external/mods/example_mod/cards/` 下建立一個名為 `my_first_card.json` 的檔案。

### 範例：重擊 (Heavy Strike)
```json
{
	"properties": {
		"object_id": "card_heavy_strike",
		"card_name": "重擊",
		"card_description": "造成 [damage] 點傷害。",
		"card_type": 0,
		"card_rarity": 1,
		"card_energy_cost": 2,
		"card_values": {
			"damage": 15,
			"number_of_attacks": 1
		},
		"card_play_actions": [
			{
				"res://scripts/actions/meta_actions/ActionAttackGenerator.gd": {
					"time_delay": 0.0
				}
			}
		],
		"card_texture_path": "external/sprites/cards/red/card_red.png"
	}
}
```

### 關鍵欄位解析：
- `card_type`：`0` 是攻擊 (Attack)，`1` 是技能 (Skill)，`2` 是能力 (Power)。
- `card_values`：在這裡定義變數（如 `damage`），這會自動替換 `card_description` 中的 `[damage]`。
- `card_play_actions`：這是最重要的部分。我們使用了 `ActionAttackGenerator.gd` 來處理攻擊邏輯。

---

## 4. 實戰：定義一個簡單的敵人

敵人也是用資料定義的。在 `external/mods/example_mod/enemies/` (若無此資料夾請建立) 建立一個 JSON 檔案。

### 範例：小機器人 (Small Bot)
```json
{
	"properties": {
		"object_id": "enemy_small_bot",
		"enemy_name": "小機器人",
		"enemy_health": 20,
		"enemy_health_max": 20,
		"enemy_attack_states": {
			"attack": {
				"attack_damage": 5,
				"number_of_attacks": 1
			}
		},
		"enemy_texture_path": "external/sprites/enemies/enemy_red_small.png"
	}
}
```

---

## 5. 實戰：建立你的角色

要讓你的卡片出現在遊戲中，你需要將它們分配給一個角色。查看 `external/mods/example_mod/characters/character_red.json`：

```json
{
	"patch_data": {
		"character_starting_card_object_ids": "append"
	},
	"properties": {
		"character_starting_card_object_ids": [
			"card_heavy_strike"
		],
		"object_id": "character_red"
	}
}
```
透過將你的卡片 ID 加到 `character_starting_card_object_ids`，你就可以在開始遊戲時擁有這張牌。

---

## 6. 如何測試你的修改？

1. 打開 Godot 專案。
2. 確保 `external/mod_list.json` 中啟用了你的模組 (`"enabled": true`)。
3. 執行遊戲，選擇對應的角色（如紅色角色）。
4. 你應該能在起始牌組中看到你的「重擊」卡片！

---

## 7. 進階提示：查看 Scripts.gd

當你想嘗試更複雜的效果（例如抽牌、獲得能量）時，請打開 `autoload/Scripts.gd`。在那裡你可以找到所有可用的行動路徑。

例如，如果你想讓卡片抽兩張牌，你可以在 `card_play_actions` 中加入：
```json
{
	"res://scripts/actions/meta_actions/ActionDrawGenerator.gd": {
		"draw_amount": 2
	}
}
```

---

## 結語

Slay The Robot 框架讓你專注於遊戲設計而不是底層程式碼。建議多參考 `autoload/Global.gd` 裡面的範例，那是最好的學習對象！

祝你開發愉快！🤖⚔️
