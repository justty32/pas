# Wesnoth 原始碼全解析百科全書 - 卷二：大自然的刻刀（水文與戰略設施）

當高度圖（0 到 1000 的數字陣列）生成後，世界還是光禿禿的。這份文件將帶你解析 `default_map_generator_job.cpp` 中，Wesnoth 是如何用演算法「雕刻」出湖泊、河流與人類的城堡。

---

## 第一節：會自己長大的湖泊 (`generate_lake`)

湖泊不是一個完美的圓形，它必須看起來像天然的水窪。Wesnoth 用了一個非常優雅的**遞歸 (Recursion) 擴散演算法**。

### 1. 函數簽名與防呆機制
```cpp
bool default_map_generator_job::generate_lake(terrain_map& terrain, int x, int y, int lake_fall_off, std::set<map_location>& locs_touched) {
    if(x < 0 || y < 0 || x >= terrain.w || y >= terrain.h || lake_fall_off < 0) {
        return false;
    }
```
**白話解讀**：當我們要在 `(x, y)` 點一滴水時，先檢查這個點有沒有跑到地圖外面。如果有，立刻停止（`return false`）。

### 2. 滴水成湖
```cpp
terrain[x][y] = t_translation::SHALLOW_WATER;
locs_touched.insert(map_location(x,y));
```
**白話解讀**：把這個格子的代碼強制改成淺水（`SHALLOW_WATER`）。同時，把這個格子寫入一個名為 `locs_touched` 的筆記本裡。這本筆記本很重要，它記住了湖泊目前長多大了。

### 3. 機率衰減的幾何擴散
這湖泊到底會長多大？由 `lake_fall_off` 這個變數決定。
```cpp
if((rng_()%100) < ulake_fall_off) {
    generate_lake(terrain,x+1,y,lake_fall_off/2,locs_touched);
}
// ... (對其他方向做一樣的事) ...
```
**白話解讀**：
- 電腦會擲一個 0 到 99 的骰子。如果骰出來的數字小於 `lake_fall_off`（比如說初始是 80%），它就會對隔壁格子（例如右邊的 `x+1`）**再呼叫一次這個函數自己**。
- **神來之筆**：注意看傳進去的參數變成了 `lake_fall_off/2`！
- **什麼意思？**：第一格有 80% 機率往外擴散，第二格就只剩 40%，第三格剩 20%，第四格 10%...。這種機率幾何衰減，確保了湖泊一定會停止生長，而且邊緣會長得坑坑巴巴的，非常自然。

---

## 第二節：尋找大海的河流 (`generate_river_internal`)

河流生成是這份代碼裡最精彩的「尋路演算法 (Pathfinding)」應用。

### 1. 終止條件：看見大海
```cpp
if(!on_map || terrain[x][y] == t_translation::SHALLOW_WATER || terrain[x][y] == t_translation::DEEP_WATER) {
    // Generate the river
    for(auto i : river) { terrain[i.x][i.y] = t_translation::SHALLOW_WATER; }
    return true;
}
```
**白話解讀**：河流會一直往前走（把走過的路記在 `river` 陣列裡）。如果它走到地圖外面，或者走到了已經是水的地方，太棒了，任務完成！把這條路徑上所有的格子都變成淺水，然後高喊 `return true`（成功了！）。

### 2. 克服萬難的「逆坡爬行」 (Uphill)
水往低處流，但如果河流遇到一個小土丘，就被困死了怎麼辦？
```cpp
if(on_map && !river.empty() && heights[x][y] > heights[river.back().x][river.back().y] + river_uphill) {
    return false;
}
```
**白話解讀**：
- 電腦檢查你現在這一步 `(x, y)` 的高度，是不是比你上一步 `river.back()` 的高度還要高？
- **寬容機制**：程式碼加上了 `river_uphill` 這個常數（通常是幾十）。意思是：**「只要這個坡沒有比我上一步高出超過 `river_uphill`，我就能硬切過去（模擬河水侵蝕切開小山丘）。」** 如果高太多，抱歉，這條路走不通 (`return false`)。

### 3. 隨機的流向
```cpp
auto adj = get_adjacent_tiles(current_loc);
std::shuffle(std::begin(adj), std::end(adj), rng_);
```
**白話解讀**：河流在十字路口該往哪走？電腦會找出周圍的六個格子，然後像洗撲克牌一樣把它們**隨機打亂** (`std::shuffle`)。然後一個個試試看。這保證了每次生成的河流都是彎彎曲曲的，不會是一條死板的直線。

---

## 第三節：風水寶地在哪裡？ (`rank_castle_location`)

地圖建好了，要把玩家的城堡放在哪？這個函數會為每一個格子打分數，分數最高的就能建城堡。

### 1. 太擠了不准建
```cpp
for(std::vector<map_location>::const_iterator c = other_castles.begin(); c != other_castles.end(); ++c) {
    const std::size_t distance = distance_between(loc,*c);
    if(distance < 6) return 0;
    if(distance < min_distance) return -1;
    // ...
}
```
**白話解讀**：電腦會檢查這塊地距離「已經建好城堡的玩家」有多遠。如果小於 6 格（甚至在對方眼皮底下），直接打 0 分（廢地）。如果小於設定的最小安全距離，打 -1 分。

### 2. 邊疆得分法
```cpp
const int border_ranking = min_distance - std::min<int>(x_from_border,y_from_border) + ...;
```
**白話解讀**：遊戲不希望大家一開始就擠在地圖正中央大亂鬥。它希望你從邊緣開始發展。所以它計算了這塊地距離地圖四個邊緣的距離（取最近的那個）。離邊緣越近，在一定的公式下，可以獲得額外的加分。

### 3. 早停優化 (Early Exit)
```cpp
int current_ranking = border_ranking*2 + avg_distance*10 + lowest_distance*10;
const int max_possible_ranking = current_ranking + 11*11;
if(max_possible_ranking < highest_ranking) {
    return current_ranking; // 不用算了，你輸定了
}
```
**白話解讀**：算完了距離分數後，接下來要算「地形豐富度」（周圍有沒有山有水）。但算周圍 11x11 的格子很累。所以電腦先偷看了一下目前的最高分 (`highest_ranking`)。如果這塊地目前的基礎分，**就算周圍 11x11 全是好地形（滿分 121）加起來**，還是比不過目前的最高分，那就直接放棄這塊地，替 CPU 省下了大量計算時間。這就是工程師的巧思。
