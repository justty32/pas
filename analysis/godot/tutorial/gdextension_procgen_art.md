# 程序藝術生成系統：ProcGenArt 逐像素生成 Image

## 目標

在 pixel-art 等級的低解析度 2D 遊戲中，用 C++ GDExtension **逐像素**程序生成基底圖像
（岩石輪廓、葉片、傷痕、生物部件），對 Godot 只暴露 `ImageTexture`，
再交給材質疊加系統（見 [[gdextension_material_2d]]）深化為多種變體。

這是 [[gdextension_procgen_mesh]] 的 2D 平行版本：
**前者逐頂點生 `ArrayMesh`，本系統逐像素生 `Image`**；
兩者共用「C++ 生成核心 + 確定性 hash + seed 重現 + GDScript 場景組裝」的同一套骨架。

來源概念：`others/godot/godot_procgen_art/CONCEPT.md`。

---

## 核心設計

```
MapCoreProcGenArt（C++ RefCounted）— 生成核心與 Godot 渲染無關，只回傳 Image
  ├── generate_shape(width, height, ShapeParams)  → Image（FORMAT_RGBA8 / L8）
  ├── generate_limb(length, width, curve_factor, seed)  → Image（灰階 L8）
  ├── generate_eye(pupil_shape, iris_pattern, seed)     → Image
  ├── generate_wing(span, vein_density, seed)           → Image
  └── generate_body(roughness, segment_count, seed)     → Image

GDScript 側
  ├── ImageTexture.create_from_image(img) → 指派給 Sprite2D.texture
  ├── 多個部件 Sprite2D 各自擺放（位置/旋轉/縮放）
  └── 掛 sprite_material.gdshader 做著色（見 material_2d）
```

**設計原則**：C++ 只負責「像素計算」，產出**灰階或 RGBA 的 `Image`**；
擺放、動畫、著色全留在 Godot 側。封裝邊界刻意切在 `Image` / `ImageTexture`，
讓生成核心可以單獨測試（甚至離線輸出 PNG 比對），不綁定任何 Godot 場景概念。

### 封裝邊界（與 Godot 無關的核心）

| 部分 | 負責方 | 介面型別 |
|------|--------|---------|
| 像素計算（SDF / noise / 規則） | C++ 純函式（不碰 Node） | 輸入 int/float 參數，輸出 `PackedByteArray` |
| 包成 Godot 資源 | C++ 薄層 | `Image::create_from_data(...)` → `Ref<Image>` |
| 轉 GPU 貼圖 | GDScript 或 C++ | `ImageTexture::create_from_image(img)` |
| 擺放 / 旋轉 / 動畫 | Godot（多個 Sprite2D + AnimationPlayer） | — |
| 顏色 / 種族 / 狀態著色 | Godot shader（material_2d） | — |

關鍵：`compute_pixel()` 這類函式**不依賴任何 `godot::` 型別**（除了回傳用的 `Color`），
理論上可抽成 header-only 庫單獨單元測試；只有最外層 `generate_*()` 接觸 `Ref<Image>`。

---

## 原始碼位置

本系統尚未實作，以下為**建議**檔案佈局（對齊現役 `mapcore_godot` 的整合模式）：

- `mapcore_godot/src/procgen_art.h`（類別宣告，仿 `procgen_mesh_builder.h`）
- `mapcore_godot/src/procgen_art.cpp`（逐像素生成實作）
- `mapcore_godot/src/register_types.cpp`（新增 `GDREGISTER_CLASS(MapCoreProcGenArt);`）

平行對照範本（已實作、結構照抄）：
- `others/gamecore/mapcore_godot/src/procgen_mesh_builder.cpp`（逐頂點生 `ArrayMesh`）
- `others/gamecore/mapcore_godot/src/procgen_mesh_builder.h`（`GDCLASS` + `_bind_methods` 宣告模式）
- `others/gamecore/mapcore_godot/src/register_types.cpp` L14–L22（`ClassDB` 註冊；新類別比照 L20 加一行）

Godot 內建 API（以 `projects/godot-cpp/gdextension/extension_api.json`，Godot v4.6.stable 為準）：
- `Image::create_from_data(int width, int height, bool use_mipmaps, Image.Format format, PackedByteArray data)`（**static**）
- `Image::create(int width, int height, bool use_mipmaps, Image.Format format)`（**static**，建空白圖）
- `Image::set_pixel(int x, int y, Color color)` / `Image::fill(Color color)`
- `Image::resize(int width, int height, Image.Interpolation interpolation)`（放大 pixel art 用 `INTERPOLATE_NEAREST=0`）
- `ImageTexture::create_from_image(Image image)`（**static**）/ `ImageTexture::update(Image image)`
- `RandomNumberGenerator::set_seed(int)` / `randf()` / `randf_range(float, float)` / `randi_range(int, int)`
- 格式常數：`Image::FORMAT_L8=0`（單通道灰階）、`Image::FORMAT_LA8=1`、`Image::FORMAT_RGBA8=5`

對應 godot-cpp 標頭（建置時由 `binding_generator.py` 從上述 json 生成於 `gen/include/godot_cpp/classes/`）：
`image.hpp`、`image_texture.hpp`、`random_number_generator.hpp`。

---

## C++ 內部實作細節

### 類別骨架（仿 procgen_mesh_builder.h）

```cpp
#pragma once
#include <godot_cpp/classes/image.hpp>
#include <godot_cpp/classes/ref_counted.hpp>

namespace godot {

class MapCoreProcGenArt : public RefCounted {
    GDCLASS(MapCoreProcGenArt, RefCounted);
protected:
    static void _bind_methods();
public:
    // 不規則岩石輪廓（noise 擾動圓 + SDF 填充），回傳 RGBA8
    Ref<Image> generate_shape(int width, int height, float roughness,
                              int sides, int seed);
    // 灰階部件：四肢（顏色交給材質系統）
    Ref<Image> generate_limb(int width, int height, float curve_factor, int seed);
};

} // namespace godot
```

`_bind_methods()` 完全比照 `procgen_mesh_builder.cpp` L60–L76：

```cpp
void MapCoreProcGenArt::_bind_methods() {
    ClassDB::bind_method(
        D_METHOD("generate_shape", "width", "height", "roughness", "sides", "seed"),
        &MapCoreProcGenArt::generate_shape,
        DEFVAL(32), DEFVAL(32), DEFVAL(0.25f), DEFVAL(6), DEFVAL(0)
    );
}
```

### 像素緩衝 → Image（封裝邊界唯一的 Godot 接觸點）

對照 `procgen_mesh_builder.cpp` 的 `MeshBuf::build()`（L45–L55，把頂點陣列塞進 `ArrayMesh`），
2D 版的等價物是「把 RGBA 位元組塞進 `Image`」：

```cpp
// 等價於 MeshBuf：純資料容器，最後一步才接觸 Godot
struct PixelBuf {
    int w, h;
    PackedByteArray data;          // RGBA8，長度 = w*h*4

    PixelBuf(int width, int height) : w(width), h(height) {
        data.resize(w * h * 4);
    }
    inline void set(int x, int y, const Color &c) {
        int idx = (y * w + x) * 4;
        data[idx + 0] = uint8_t(c.r * 255.0f);
        data[idx + 1] = uint8_t(c.g * 255.0f);
        data[idx + 2] = uint8_t(c.b * 255.0f);
        data[idx + 3] = uint8_t(c.a * 255.0f);
    }
    // 唯一接觸 Godot 資源的地方
    Ref<Image> build() const {
        return Image::create_from_data(w, h, false, Image::FORMAT_RGBA8, data);
    }
};
```

> 注意：`Image::create_from_data` 是**靜態方法**，回傳 `Ref<Image>`。
> 直接寫 `PackedByteArray` 比逐格 `set_pixel()` 快（後者每格都過 Variant 邊界）。

### 確定性 hash（與 procgen_mesh 共用同一套）

直接沿用 `procgen_mesh_builder.cpp` L21–L30 的 `hf` / `hf3`，
保證**相同 seed → 相同圖像**，便於快取與離線比對：

```cpp
static float hf(int a, int b) {
    unsigned int h = static_cast<unsigned int>(a * 1619 + b * 31337);
    h ^= (h << 13);
    h = h * (h * h * 15731u + 789221u) + 1376312589u;
    return static_cast<float>(h & 0x7fffffffu) / 2147483647.0f;
}
```

3D 版用 `hf3` 擾動「頂點沿法線位移」（L107），2D 版改用它擾動「輪廓半徑」或「邊緣 SDF」。

### SDF 輪廓 + noise 擾動（generate_shape 核心）

3D 岩石的不規則感來自「頂點沿法線 noise 位移」（`procgen_mesh_builder.cpp` L104–L110）。
2D 等價技法：**對每個像素算到形狀中心的 signed distance，再用角度方向的 noise 擾動半徑**：

```cpp
Ref<Image> MapCoreProcGenArt::generate_shape(
    int width, int height, float roughness, int sides, int seed)
{
    PixelBuf buf(width, height);
    float cx = width * 0.5f, cy = height * 0.5f;
    float base_r = std::min(cx, cy) * 0.8f;

    const Color fill{0.55f, 0.50f, 0.45f, 1.0f};  // 灰棕（同 3D 岩石基礎色）

    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            float dx = x - cx, dy = y - cy;
            float dist  = std::sqrt(dx * dx + dy * dy);
            float angle = std::atan2(dy, dx);              // -PI ~ PI

            // 沿角度方向擾動半徑：把 angle 量化成 N 段，各段一個 hash 偏移
            int   bin = int((angle + KPI) / (2.0f * KPI) * 64.0f);
            float wob = (hf(bin + seed, bin * 7) - 0.5f) * roughness * base_r;
            float edge = base_r + wob;

            // signed distance：<0 在形狀內
            float sd = dist - edge;
            float a  = (sd < 0.0f) ? 1.0f : 0.0f;          // 硬邊（pixel art）

            // 面色明度抖動（同 3D 的 ±12%，L114–L117）
            float s = 0.88f + hf(x * 13 + seed, y * 7 + seed) * 0.24f;
            buf.set(x, y, Color(fill.r * s, fill.g * s, fill.b * s, a));
        }
    }
    return buf.build();
}
```

要更有機的形狀（裂縫、岩石稜角），把單一 `bin` noise 換成多頻疊加（fBm）或
多個 SDF 圓做布林 `subtract`（CONCEPT.md L34 的 SDF 組合）。

### 灰階部件（generate_limb：顏色留給材質系統）

CONCEPT.md L96 要求「部件輸出為灰階圖，顏色交給材質系統」。
對應用 `FORMAT_L8`（單通道）省記憶體，或保留 alpha 用 `FORMAT_LA8`：

```cpp
Ref<Image> MapCoreProcGenArt::generate_limb(
    int width, int height, float curve_factor, int seed)
{
    PackedByteArray data;
    data.resize(width * height * 2);                 // LA8：亮度 + alpha
    for (int y = 0; y < height; y++) {
        // 沿 Y 軸的中心線隨 curve_factor 彎曲（Bézier 近似）
        float t  = float(y) / height;
        float cx = width * 0.5f + std::sin(t * KPI) * curve_factor * width * 0.3f;
        float half_w = width * 0.4f * (1.0f - t * 0.5f);   // 末端漸細
        for (int x = 0; x < width; x++) {
            bool inside = std::abs(x - cx) < half_w;
            float lum   = inside ? (0.5f + hf(x + seed, y) * 0.3f) : 0.0f;  // 灰階明暗
            int idx = (y * width + x) * 2;
            data[idx + 0] = uint8_t(lum * 255.0f);
            data[idx + 1] = uint8_t(inside ? 255 : 0);
        }
    }
    return Image::create_from_data(width, height, false, Image::FORMAT_LA8, data);
}
```

### seed 與隨機來源

兩條路線，二選一（見「待決定」建議）：
- **確定性 hash（`hf`）**：純函式、無狀態、可平行、跨平台位元一致 — 與 procgen_mesh 一致，**推薦**。
- **`RandomNumberGenerator`**：`rng.set_seed(seed)` 後呼叫 `randf_range()`，
  好處是 GDScript 端可共用同一個 RNG 物件，缺點是有序列狀態、不便平行。

---

## GDScript 使用範例

### 單張基底（最小流程，對照 CONCEPT.md L60–L64）

```gdscript
func make_rock_sprite(parent: Node2D, pos: Vector2, seed: int) -> void:
    var art := MapCoreProcGenArt.new()
    var img: Image = art.generate_shape(32, 32, 0.25, 6, seed)
    var tex: ImageTexture = ImageTexture.create_from_image(img)

    var sprite := Sprite2D.new()
    sprite.texture = tex
    sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST  # pixel art 不要模糊
    sprite.position = pos
    parent.add_child(sprite)
```

### 組合生物（多部件各自 Sprite2D — CONCEPT.md 採用方案）

CONCEPT.md L159 已拍板：**GDExtension 只生成各部件的 `Image`，擺放與動畫留在 GDScript**
（多個 Sprite2D），理由是動畫自由度優先（觸角飄動/眨眼用 AnimationPlayer 直接驅動）。

```gdscript
func make_creature(parent: Node2D, seed: int) -> void:
    var art := MapCoreProcGenArt.new()
    var root := Node2D.new()

    var body_img := art.generate_body(0.3, 4, seed)
    var body := _sprite(art, body_img, Vector2.ZERO)
    root.add_child(body)

    # 對稱擺放四肢：擺放數學在 GDScript，像素生成在 C++
    var legs := 4
    for i in legs:
        var limb_img := art.generate_limb(8, 16, 0.4, seed + i)
        var t := float(i) / legs
        var x := -16.0 + 32.0 * t
        var leg := _sprite(art, limb_img, Vector2(x, 8))
        leg.rotation = -0.3 if i < legs / 2 else 0.3   # 左右對稱
        root.add_child(leg)

    parent.add_child(root)

func _sprite(art, img: Image, pos: Vector2) -> Sprite2D:
    var s := Sprite2D.new()
    s.texture = ImageTexture.create_from_image(img)
    s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    s.position = pos
    return s
```

---

## 與其他系統的整合關係

```
ProcGenArt（本系統，生「基底形狀」灰階/RGBA Image）
        │ ImageTexture
        ▼
material_2d（[[gdextension_material_2d]]：基底 × 材質疊加 × 細節三層 shader）
        │ 著色後的 Sprite2D
        ▼
2D 染色 / 紙娃娃（[[gdextension_2d_dyeing_system]]：區域遮罩局部染色）
```

- **上游 → 本系統**：`generate_shape` 取代「美術手繪基底」，是 material_2d 的 `TEXTURE` 來源。
  灰階部件正好對應 [[gdextension_2d_dyeing_system]] 的「灰階基底」概念。
- **本系統 → material_2d**：同一張基底 `Image` 配不同材質層 → 鐵岩 / 紫晶岩 / 苔蘚岩等變體，
  不必為每個變體各生一張圖（material_2d 解決「貼圖爆炸」的同一目標）。
- **與 [[gdextension_image_to_sprite]]**：該文示範「磁碟圖片 → ImageTexture」，
  本系統把「磁碟載入」換成「程序生成」，下游（`ImageTexture` → `Sprite2D`）完全相同。
- **與 [[gdextension_procgen_mesh]]**：3D/2D 平行雙生；若同一專案兩者並用，
  `hf`/`hf3` 與 seed 約定共用，3D 物件與 2D 圖示可由同一 seed 派生一致風格。

---

## 效能 / 已知限制

- **解析度敏感**：逐像素是 O(w·h)。CONCEPT.md L5 已界定「目標解析度低（pixel art）」，
  32×32~128×128 等級每張數十微秒級可接受；不要拿來生 2K 大圖。
- **寫 `PackedByteArray` 優於逐格 `set_pixel()`**：後者每格穿越 Variant/綁定邊界，數量級慢。
- **不要在 `_process` 每幀重生**：生成屬一次性（同 [[gdextension_image_to_sprite]] 第 6 節）；
  變體切換用 material_2d 改 shader uniform，不重生 Image。
- **`ImageTexture` 佔顯存**：大量生物各自一組部件貼圖會累積；可對「相同 seed + 相同參數」做
  `Dictionary` 快取（同 [[gdextension_material_3d]] 的材質快取思路），重用 `Ref<Image>`。
- **多部件 = 多 Sprite2D = 多 draw call**：與 3D 的 MultiMesh 不同，2D 多部件無法天然合批；
  若一個生物部件數很多，可在 C++ 端先 `generate_*` 後合併成單張 Image（CONCEPT.md L132 列為可選），
  犧牲動畫自由度換 draw call。

---

## 待決定（對應 CONCEPT.md「待決定」與分層願景，逐項給建議）

### CONCEPT.md L157–L161 待決定項

- **生物動畫如何與程序部件整合（動態骨骼 vs 預製動畫 vs 純程式驅動）**
  **建議：純程式驅動為主、AnimationPlayer 為輔，暫不上 Skeleton2D。**
  理由：部件已是獨立 Sprite2D（L159 拍板），呼吸/觸角飄動這類週期動作用
  `_process` 改 `position`/`rotation`（程式驅動）最省事且能跟生成參數連動；
  少數固定動作（眨眼）用 AnimationPlayer 關鍵影格。動態骨骼（Skeleton2D + Bone2D）
  要綁權重，對 pixel art 等級的硬邊圖收益低、成本高，列為遠期。

- **程序幾何函式庫選型**
  **建議：自實作極簡 SDF + Bézier，不引第三方庫。**
  理由：低解析度下只需 `circle`/`segment`/`polygon` 三種 SDF 與布林（min/max/subtract），
  約百行 header-only 即可，且能保持「核心與 Godot 無關、可離線測試」的封裝邊界乾淨。
  CONCEPT.md L153 提到的 `stb_truetype` 曲線部分過重；真要曲線光柵化，
  優先用 De Casteljau 切線段再走 polygon SDF。

### 分層願景逐級建議（CONCEPT.md L18–L23）

- **Level 1（基底 + 材質疊加 shader，已有）**
  **建議：直接落在 material_2d 的三層 shader（[[gdextension_material_2d]]）。** 本系統負責供「基底」。

- **Level 2（程序幾何 + 像素組合 → 生成基底）= 本文件主體**
  **建議：先只交付 `generate_shape`（RGBA 不規則輪廓）+ `generate_limb`（LA8 灰階部件）兩支，
  確定性 hash 路線，跑通「生成 → ImageTexture → material_2d 著色」全鏈再擴充。**
  理由：最小可驗證閉環；其餘部件函式（eye/wing/body）形狀同套路，驗證一支等於驗證全部。

- **Level 3（生物部件系統）**
  **建議：部件「圖像生成」放 C++（本系統），「集合決策 + 擺放」放 GDScript。**
  理由：擺放是高層規則（幾條腿、對稱性），改動頻繁且需與動畫耦合，留在腳本端迭代快；
  C++ 只保證「給參數出一張部件圖」。與 CONCEPT.md L128–L136 的邊界表一致，
  但把「擺放計算」從 C++ 移到 GDScript（呼應 L159 的拍板，比 CONCEPT 表格更新）。

- **Level 4（接入 SD/Flux 等圖像生成模型，遠期）**
  **建議：把外部模型當「另一個 Image 來源」，介面同樣收斂到 `Ref<Image>`，不改下游。**
  理由：封裝邊界已定在 Image；無論基底來自 C++ 程序、磁碟 PNG（[[gdextension_image_to_sprite]]）
  或 SD 輸出，material_2d 與擺放層都無感。先解決「透明背景 + 解析度一致 + NEAREST 取樣」三個
  pixel-art 約束（CONCEPT.md L144）再接模型；短期不投入。

### 額外建議（封裝邊界）

- **建議：`generate_*()` 內部的 `compute_pixel` 邏輯不碰 `godot::Node`，只用 POD 參數與 `Color`，
  最外層才呼叫 `Image::create_from_data`。** 理由：守住 CONCEPT.md L12「生成核心與 Godot 無關、
  只暴露 ImageTexture」的承諾，使核心可單獨單元測試、可離線輸出 PNG 做視覺迴歸比對。

---

*記錄時間：2026-05-23*
*狀態：概念階段；本文件為實作設計指引。平行範本 [[gdextension_procgen_mesh]] 已實作於 mapcore_godot*
