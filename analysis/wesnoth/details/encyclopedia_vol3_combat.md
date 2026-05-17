# Wesnoth 原始碼全解析百科全書 - 卷三：死神的算盤（AI 戰鬥與風險評估）

這份文件將帶你解析 `src/ai/default/attack.cpp`。當電腦 AI 決定要不要攻擊你的時候，它不是看心情，而是經過了一系列極度嚴密的機率與風險計算。

---

## 核心函數：`attack_analysis::rating` (攻擊評分系統)

這個函數是 AI 戰鬥大腦的核心。它會計算出一個分數（`Value`）。分數越高，AI 就越想打你。如果分數是負的，打死它都不會動手。

### 1. 目標的身價：快升級的兵最值錢
```cpp
target_value = defend_it->cost();
const unsigned int defend_experience = defend_it->can_advance() ? defend_it->experience() : 0;
target_value += (static_cast<double>(defend_experience) / static_cast<double>(defend_it->max_experience())) * target_value;
```
**白話解讀**：
- 電腦先看你的兵值多少錢（`cost()`）。
- 然後，它會檢查你的經驗值 (`experience()`)。如果你的兵經驗值快滿了（快升級了），電腦會把這個經驗值的比例（例如 90%）加算到這隻兵的「賞金」上。
- **結論**：對 AI 來說，一隻快升級的 1 級兵，可能比一隻剛招募的 2 級兵還「香」。這就是為什麼你的老兵總是容易被集火。

### 2. 基礎評分公式：一場精算的豪賭
```cpp
double value = chance_to_kill*target_value - avg_losses*(1.0-aggression);
```
**白話解讀**：
這是 AI 決定是否攻擊的基礎公式：**預期收益 - 預期損失**。
- `chance_to_kill * target_value`：把你打死的機率 乘上 你的賞金。這叫「預期收益」。
- `avg_losses`：AI 模擬戰鬥後，預估自己會損失多少血量換算成的金錢。
- `(1.0 - aggression)`：`aggression` 是 AI 的好戰度（通常在 0 到 1 之間）。如果好戰度是 1.0，括號裡就變成 0，代表 AI **完全不把自己的損失當一回事**，變成視死如歸的狂戰士。

### 3. 風險敞口 (Exposure)：為什麼 AI 總躲在山上？
如果你要打人，通常得移動到目標旁邊。這時，AI 會評估「打完之後，我會不會很危險？」
```cpp
if(terrain_quality > alternative_terrain_quality) {
    // Calculate the 'exposure' of our units to risk.
    const double exposure = exposure_mod*resources_used*(terrain_quality - alternative_terrain_quality)*vulnerability/std::max<double>(0.01,support);
    value -= exposure*(1.0-aggression);
}
```
**白話解讀**：
這段代碼是 Wesnoth AI 靈魂所在！
- `alternative_terrain_quality`：如果 AI 不打你，它原本可以躲在的最好地形（例如防禦力 70% 的高山）。
- `terrain_quality`：為了打你，它必須移動到的地形（例如防禦力 40% 的平地）。
- `terrain_quality - alternative_terrain_quality`：如果這個數字大於 0，代表 AI 放棄了原本的好地形。
- **扣分懲罰 (`exposure`)**：
    - 懲罰有多重？取決於 `vulnerability`（周圍敵人有多少）除以 `support`（周圍隊友有多少）。
    - 如果 AI 周圍全是敵人，沒有隊友，這個懲罰會被放大到天際。
    - 最後把這個極大的懲罰從原本的 `value` 扣掉，導致 `value` 變成負數，AI 放棄攻擊。

### 4. 殘血收割機：尾刀優先權
```cpp
value += ((target_starting_damage/3 + avg_damage_inflicted) - (1.0-aggression)*avg_damage_taken)/10.0;
```
**白話解讀**：
- `target_starting_damage` 是目標「已經少掉的血量」。
- 電腦會偷偷給這個攻擊選項加一點分。意思就是：**「雖然打不死，但把它打更殘也是好的。特別是如果它本來就殘血，那就更該打。」** 這確保了 AI 會優先集火已經受傷的單位。

### 5. 放手一搏：被包圍時的瘋狂
```cpp
if(!is_surrounded || (support != 0 && avg_damage_taken != 0)) {
    // 執行理智檢查 (Sanity Check)，太危險就不打
    if(vulnerability > 50.0 && vulnerability > support*2.0 && chance_to_kill < 0.02) {
        return -1.0;
    }
}
```
**白話解讀**：
- 通常情況下，如果太危險（`vulnerability` 超高）且打不死人（`chance_to_kill < 0.02`），電腦會直接放棄 (`return -1.0`)。
- **但是！** 注意第一行的 `if(!is_surrounded)`。反過來說，如果這隻 AI 已經被你的大軍**死死包圍 (`is_surrounded == true`)**，而且完全沒有隊友支援，它就會**跳過這個理智檢查**！
- 這叫做「困獸之鬥」。反正跑不掉了，不如死前多咬你一口。這讓遊戲的 AI 行為非常符合真實戰場的人性。
