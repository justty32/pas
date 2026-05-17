# Wesnoth 原始碼全解析百科全書 - 卷一：創世的泥巴球（地貌生成核心）

這份文件將帶你逐行看懂 Wesnoth 是如何從一片虛無中，捏出有高山、有平原的世界。我們將解剖 `src/generators/default_map_generator_job.cpp` 裡最核心的函數。

---

## 核心函數：`generate_height_map` (生成高度圖)

這個函數的任務是：製造出地圖的「高低起伏」。它不決定哪裡是草地或雪地，它只決定哪裡高、哪裡低。

### 1. 準備沙坑：矩陣初始化
```cpp
height_map res(width, std::vector<int>(height,0));
```
**白話解讀**：電腦先準備了一個長寬各為 `width` 和 `height` 的大沙坑，並且用 `0` 把每個格子的初始高度都填平。

### 2. 決定要丟幾次泥巴：Iterations
```cpp
for(std::size_t i = 0; i != iterations; ++i) { ... }
```
**白話解讀**：`iterations` 是你在設定地圖時決定的「丘陵數量」。遊戲會跑一個大迴圈，每一次迴圈，就是上帝抓起一把泥巴往沙坑裡砸。

### 3. 尋找落點與極性：Island Mode (島嶼模式)
接下來，電腦要決定這把泥巴砸在哪裡。
```cpp
int x1 = island_size > 0 ? center_x - island_size + (rng_()%(island_size*2)) : static_cast<int>(rng_()%width);
int y1 = island_size > 0 ? center_y - island_size + (rng_()%(island_size*2)) : static_cast<int>(rng_()%height);
```
**白話解讀**：
- 如果**沒有**開島嶼模式：電腦閉著眼睛在整張地圖上隨便選一個坐標 `(x1, y1)`。
- 如果**有**開島嶼模式：電腦會先找到地圖正中心，然後只在中心附近 `island_size` 的範圍內挑選落點。這保證了泥巴大多落在中間，形成一塊完整的大陸。

**判斷是「造山」還是「挖坑」 (`is_valley`)**：
```cpp
bool is_valley = false;
if(island_size != 0) {
    const std::size_t dist = std::size_t(std::sqrt(diffx*diffx + diffy*diffy));
    is_valley = dist > island_size;
}
```
**白話解讀**：這段邏輯非常聰明。即使開啟了島嶼模式，偶爾泥巴還是會砸得太偏。電腦用畢氏定理（勾股定理）算了一下落點離地圖中心的距離 `dist`。如果這個距離大於 `island_size`（也就是砸到海裡了），`is_valley` 就會變成 `true`。這意味著這把泥巴不造山了，它變成一把鏟子，在邊緣**挖一個坑**，確保地圖邊緣永遠是低海拔的海洋。

### 4. Bounding Box (包圍盒) 的效能魔法
決定了落點 `(x1, y1)` 和半徑 `radius` 後，最笨的做法是跑遍整張地圖更新高度。Wesnoth 的工程師用了 Bounding Box。
```cpp
const int min_x = x1 - radius > 0 ? x1 - radius : 0;
const int max_x = x1 + radius < static_cast<long>(res.size()) ? x1 + radius : res.size();
```
**白話解讀**：這就像是你在沙坑砸了一個直徑 5 公分的泥巴，泥巴濺出去的範圍絕對不會超過 5 公分。所以程式碼算出了 `min_x` 和 `max_x`，畫出一個正方形。**只在這個正方形裡面**去計算高度變化。這讓地圖生成速度快了無數倍。

### 5. 高度疊加公式：幾何半球體
在剛才畫出的正方形裡，對每一個格子 `(x2, y2)` 進行高度更新。
```cpp
const int xdiff = (x2-x1);
const int ydiff = (y2-y1);
const int hill_height = radius - static_cast<int>(std::sqrt(static_cast<double>(xdiff*xdiff + ydiff*ydiff)));
```
**白話解讀**：這是一條標準的**半球體方程式**。
- 先算出當前格子 `(x2, y2)` 距離泥巴中心點 `(x1, y1)` 有多遠（直線距離）。
- 然後用泥巴的總半徑 `radius` 減去這個距離，得到 `hill_height`。
- 越靠近中心，減去的越少，高度就越高；越靠近邊緣，高度就趨近於 0。

**實裝高度**：
```cpp
if(hill_height > 0) {
    if(is_valley) {
        res[x2][y2] = max(0, res[x2][y2] - hill_height); // 挖坑
    } else {
        res[x2][y2] += hill_height;                      // 堆高
    }
}
```
**白話解讀**：如果這把是泥巴（不是鏟子），就把 `hill_height` 加到原本的高度上。如果是鏟子（`is_valley`），就減掉，但最低不能小於 0（用 `max` 函數保護，防止高度變成負數）。

### 6. 終極平整術：Normalize (正規化)
泥巴丟完了，但現在沙坑有的地方高度是 53，有的地方是 8921，這對後續寫程式很難處理。
```cpp
int highest = 0, lowest = 100000;
// ... (找出最高和最低點) ...
highest -= lowest;
for(x ...) {
    for(y ...) {
        res[x][y] -= lowest;
        res[x][y] *= 1000;
        if(highest != 0) res[x][y] /= highest;
    }
}
```
**白話解讀**：
這叫作線性映射。
1. 找出全圖最矮的地方，讓所有地方都減去這個最矮高度。這樣最矮的地方高度就變成 0 了。
2. 找出最高的地方（減去最矮高度後的差值）。
3. 把每個格子的高度乘上 1000，再除以最高點的差值。
4. **結果**：整張地圖的高度被完美地壓縮到了 **0 到 1000 的整數區間**。0 絕對是深海，1000 絕對是最高峰。這樣以後的程式只要說「高度大於 800 的放雪山」，就不會出錯了。
