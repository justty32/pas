# 程序藝術生成系統

## 核心哲學

**目標解析度低（pixel art 等級）→ 程式操作像素可行且高效。**

不依賴美術手繪大量素材，改由：
1. AI 撰寫生成程式（規則 + 隨機變數）
2. 程式組合像素，產生基底圖像
3. 再透過材質疊加系統（見 `../godot_material/`）深化為多種變體

生成核心與 Godot 無關，封裝為 **C++ GDExtension**，對 Godot 只暴露 `ImageTexture`。

---

## 生成管線層次

```
Level 1（已有）：基底素材 + 材質疊加 shader
Level 2（下一步）：程序幾何 + 像素組合 → 生成基底素材本身
Level 3（生物系統）：部件程序生成 + 部件程序擺放 → 組合成完整生物
Level 4（遠期）：接入圖像生成模型（SD 等）作為輸入端
```

---

## Level 2：程序幾何與像素生成

### 幾何類型

- **多邊形**：點列 + 填色（已簡單）
- **曲線**：Bézier 曲線、B-spline → 轉為像素輪廓 → 填充
- **程序輪廓**：noise 擾動直線/圓 → 有機形狀（岩石、葉片、傷痕）
- **SDF 組合**：signed distance field 布林操作（union / subtract / intersect）→ 複雜形狀

### 像素操作流程（C++）

```cpp
// GDExtension 側：生成一張 Image 回傳給 Godot
Ref<Image> generate_shape(int width, int height, ShapeParams p) {
    PackedByteArray buf;
    buf.resize(width * height * 4);  // RGBA

    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            Color c = compute_pixel(x, y, p);  // 規則 + 隨機
            int idx = (y * width + x) * 4;
            buf[idx+0] = uint8_t(c.r * 255);
            buf[idx+1] = uint8_t(c.g * 255);
            buf[idx+2] = uint8_t(c.b * 255);
            buf[idx+3] = uint8_t(c.a * 255);
        }
    }

    return Image::create_from_data(width, height, false, Image::FORMAT_RGBA8, buf);
}
```

GDScript 側：
```gdscript
var img: Image = ProcGenArt.generate_shape(32, 32, params)
var tex: ImageTexture = ImageTexture.create_from_image(img)
sprite.texture = tex
```

### AI 的角色

- **人定義意圖**：「生成一個不規則的岩石輪廓，帶裂縫」
- **AI 撰寫** `compute_pixel()` 的規則邏輯（SDF 組合、noise 參數）
- **人調整隨機種子或參數**，AI 可進一步 fine-tune 規則

---

## Level 3：生物部件系統

### 設計原則

生物 = **部件圖像** × **部件擺放**，兩者各自程序生成。

```
生物生成流程：
  seed → 決定部件集合（幾條腿？翅膀？觸角？）
       → 各部件各自程序生成圖像
       → 程序決定各部件的位置/旋轉/縮放
       → 組合輸出為單張 Image（或多層 Sprite2D）
```

### 部件圖像生成

每種部件類型有自己的生成函式：
- `generate_limb(length, width, curve_factor, seed)` → 四肢
- `generate_eye(pupil_shape, iris_pattern, seed)` → 眼睛
- `generate_wing(span, vein_density, seed)` → 翅膀
- `generate_body(contour_roughness, segment_count, seed)` → 軀幹

部件輸出為**灰階圖**，顏色交給材質系統。

### 部件擺放生成

擺放規則 = 硬約束（對稱性、比例）+ 隨機擾動：

```cpp
struct PartPlacement {
    Vector2 position;   // 相對於軀幹中心
    float   rotation;
    float   scale;
};

// 例：四肢對稱擺放
PartPlacement place_limb(int leg_index, int total_legs, float body_length) {
    float t = float(leg_index) / total_legs;  // 沿軀幹分布
    float x = body_length * t - body_length * 0.5f;
    float y = body_width * 0.5f + rng.randf_range(-2, 2);  // 小隨機擾動
    float rot = -PI * 0.3f + rng.randf_range(-0.2f, 0.2f);
    return {Vector2(x, y), rot, 1.0f};
}
```

### AI 的角色

- **部件圖像**：AI 撰寫各部件的 `generate_*()` 函式
- **擺放規則**：AI 設計 `place_*()` 的約束邏輯
- **部件集合決策**：可用 AI agent 依照「生物類型描述」產生部件清單，再呼叫對應生成函式
- **視覺 review**：將生成結果截圖給 AI，讓 AI 評估並調整參數（閉環迭代）

### 與 Godot 的邊界

| 部分 | 負責方 |
|------|--------|
| 部件圖像生成（像素計算） | C++ GDExtension |
| 部件擺放計算 | C++ GDExtension |
| 圖像合併為單張 Image | C++ GDExtension |
| 接收 ImageTexture，顯示 | Godot（Sprite2D） |
| 材質疊加（顏色/種族/狀態） | Godot shader |
| 動畫（觸角飄動、呼吸） | Godot AnimationPlayer |

---

## Level 4（遠期）：接入圖像生成模型

- 用 SD / Flux 等模型生成**風格一致的部件基底圖像**
- 進入分層 shader 系統做材質疊加
- AI 生成模型負責「風格」，程序系統負責「組合與變體」
- 需要解決：解析度一致性、透明背景、pixel art 風格約束

---

## 技術選型

- **生成核心**：C++ GDExtension（參考 `mapcore_cpp_square` 的整合模式）
- **圖像格式**：`Image::FORMAT_RGBA8`，灰階生成後交 shader 著色
- **隨機**：`RandomNumberGenerator`（GDExtension 側用 `std::mt19937`，seed 從 GDScript 傳入）
- **幾何**：自實作 SDF / Bézier，或引入 header-only 函式庫（如 `stb_truetype` 的曲線部分）

---

## 待決定

- [x] 部件擺放：GDExtension 只生成每個部件的 `ImageTexture`，擺放與動畫留在 GDScript 側（多個 Sprite2D）。理由：動畫自由度優先，觸角飄動/眨眼等後續動畫可直接用 AnimationPlayer 驅動。
- [ ] 生物的動畫如何與程序生成的部件整合（動態骨骼 vs 預製動畫 vs 純程式驅動）
- [ ] 程序幾何的幾何函式庫選型

---

*記錄時間：2026-05-22*
