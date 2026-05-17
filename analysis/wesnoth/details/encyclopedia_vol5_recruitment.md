# Wesnoth 原始碼全解析百科全書 - 卷五：將軍的帳本（AI 招募與反制引擎）

這份文件將帶你解析 `src/ai/default/recruitment.cpp`。AI 是如何決定要花錢買什麼兵的？它不像新手玩家一樣有錢就花，它肚子裡有一本嚴密的會計帳本，以及一本對付你的兵法書。

---

## 第一節：會計師的預測模型 (`get_estimated_income`)

AI 在買兵前，會先看未來 5 回合的財報。

### 1. 預測未來的金幣
```cpp
double recruitment::get_estimated_income(int turns) const {
    double income = 0;
    int current_villages = get_villages_count();
    int current_upkeep = get_upkeep();
    // ...
    income = (current_villages * game_config::village_income - current_upkeep) * turns;
    return income;
}
```
**白話解讀**：
- 電腦會算出自己目前有多少村莊（`current_villages`），乘以每個村莊能賺的錢（通常是 2 塊）。
- 然後減去目前軍隊要發的薪水（`current_upkeep`，維持費）。
- 將這個差額乘上 `turns`（通常預測未來 5 回合）。如果算出來是負的，代表 AI 發現自己快要破產了！

### 2. 啟動防禦機制：SAVE_GOLD
在 `update_state()` 函數中：
```cpp
if (gold < cheapest_unit_cost || (get_estimated_income(5) < 0 && gold < 50)) {
    state_ = SAVE_GOLD;
}
```
**白話解讀**：
如果未來 5 回合會虧錢，而且現在存款低於 50 塊，AI 就會進入 `SAVE_GOLD`（存錢）模式。在這個模式下，AI 會**拒絕招募任何分數不高的兵種**，把錢死死捏在手裡，直到看見極度划算的招募選項，或者撐到發薪水為止。

---

## 第二節：兵法大師的反制模型 (`do_combat_analysis`)

AI 怎麼知道你出了很多騎兵，所以它應該多出槍兵？這是因為它在腦海裡把所有兵種都打了一遍。

### 1. 蒐集敵方陣容
```cpp
void recruitment::do_combat_analysis(std::vector<data>* leader_data) {
    // ... (找出所有敵軍) ...
    for (const unit& u : units) {
        if (current_team().is_enemy(u.side())) {
            enemy_types.push_back(u.type_id());
        }
    }
```
**白話解讀**：電腦先環顧四周，把你的軍隊名單抄下來（例如：3 個騎兵、2 個弓箭手）。

### 2. 模擬競技場：哪種兵最好用？
```cpp
    for (const std::string& recruit : recruits) {
        double score = 0;
        for (const std::string& enemy : enemy_types) {
            score += compare_unit_types(recruit, enemy);
        }
        // ... (把分數加到這個兵種的招募評分上)
    }
}
```
**白話解讀**：
- 接下來，AI 打開自己的招募清單（假設有：精靈戰士、精靈弓箭手、精靈薩滿）。
- 它會讓「精靈戰士」在腦海裡去跟你的「3個騎兵+2個弓箭手」輪流打一架 (`compare_unit_types`)。
- `compare_unit_types` 裡面會計算：精靈戰士對騎兵的傷害有多少？抗性如何？會不會被秒殺？然後算出一個分數。
- **結論**：如果精靈戰士打輸了，他的招募評分就會很低。如果精靈薩滿（會減速）對付你的騎兵有奇效，薩滿的招募分數就會狂飆。AI 於是順理成章地買了一堆薩滿來針對你。

---

## 第三節：地形感知的熱力圖 (`update_important_hexes`)

AI 的兵種相剋不只看「人」，還看「地」。

### 1. 哪裡最重要？
```cpp
void recruitment::update_important_hexes() {
    // 收集所有敵人的位置
    // 收集所有村莊的位置
    // ...
```
**白話解讀**：AI 會把全地圖上的村莊、敵人和自己的城堡連成線，找出所謂的「前線」和「戰略要地」。

### 2. 看風水招募
```cpp
    for (const map_location& hex : important_hexes_) {
        ++important_terrain_[map[hex]];
    }
```
**白話解讀**：
- 找出前線後，AI 會看這些前線的格子是**什麼地形**？
- 如果統計出來，前線高達 70% 都是森林。AI 在執行前面的 `compare_unit_types` 時，就會**假設戰鬥是發生在森林裡**。
- 這時候，在森林裡防禦力高達 70% 的精靈，其戰鬥模擬評分會遠遠甩開在森林裡走不動的騎兵。AI 最終就會得出結論：「這場仗要在樹林裡打，所以我全部買精靈。」

這就是 Wesnoth 的 AI 雖然看起來簡單，但玩起來卻非常難纏的底層原因。它兼具了經濟學家的遠見、兵法家的相剋邏輯、以及地理學家的地形感知。
