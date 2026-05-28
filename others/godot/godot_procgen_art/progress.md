# godot_procgen_art — 進度保存

> 最後更新：2026-05-28。從 `CONCEPT.md` 落地的純 GDScript 原型。

## 一句話：這是什麼

2D pixel art 級程序生成圖像工具：SDF 組合 / Bézier 曲線 / noise 擾動 + 生物部件圖像生成。
**純 GDScript** 後備版（CONCEPT 原規畫走 C++ GDExtension，但 mapcore 端沒做）。

## 真相校準

| 來源 | 角色 |
|------|------|
| CONCEPT 原規畫 C++ GDExtension（mapcore_cpp_square 模式） | 未做（mapcore 端沒對應實作） |
| **本檔 純 GDScript 版** | pixel art 級解析度（16~128 px）夠快，作為原型與規格 |
| 未來 C++ 端 | 若有效能瓶頸，照本檔 API 重寫即可 |

GDScript 端 `Image.set_pixel()` 在 32×32 大概是 1k 個 pixel，跑一次性生成不會卡頓；
即使 128×128 也只 16k pixels，比每幀 shader 算的開銷小得多（一次生成永久使用）。

## 檔案清單

```
godot_procgen_art/
├── CONCEPT.md
├── gd/
│   ├── proc_image.gd        # ProcImage：SDF / Bézier / Image 填色工具
│   └── proc_part.gd         # ProcPart：軀幹 / 四肢 / 頭 / 眼 / 翅膀 generator
└── progress.md
```

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| ProcImage.new_image / to_texture | 建空 Image + 轉 ImageTexture | ✅ 完成 |
| SDF helpers | circle / box / union / subtract / smooth_union | ✅ 完成 |
| fill_sdf | 用 callable SDF 掃描整圖填色 + 邊緣 | ✅ 完成 |
| Bézier raster | quadratic / cubic + Bresenham draw_line | ✅ 完成 |
| noisy_sdf | 把 SDF 結果加 FastNoiseLite 擾動，產有機輪廓 | ✅ 完成 |
| ProcPart.generate_body | 拉伸橢圓 + noise 輪廓 | ✅ 完成 |
| ProcPart.generate_limb | 兩圓 + 矩形 smooth union + 漸細 | ✅ 完成 |
| ProcPart.generate_head | 圓 + 輪廓 noise | ✅ 完成 |
| ProcPart.generate_eye | 鞏膜 + 瞳孔（兩 pass） | ✅ 完成 |
| ProcPart.generate_wing | 軸對齊翅膀 SDF + 貝茲翼脈 | ✅ 完成 |
| 與 godot_character.PaperDoll2D 整合 | 程序生成的灰階 mask → SpriteMaterial 染色 | ✅ 概念對齊（用法範例展示） |
| C++ GDExtension 版 | 若有效能瓶頸再啟動 | ⏸ 未做 |
| 真機驗證 | Godot 4 跑五種 part 看視覺 | ⏸ **待真機驗證** |

## 設計重點

### 1. SDF 而非像素掃描的多邊形 / 圓 / 矩形
SDF（Signed Distance Field）能用 `union/subtract/smooth_union` 任意組合複雜形狀，
比逐多邊形 rasterize 更靈活。`fill_sdf(image, callable)` 一行就把整張圖填好，
且可加 `edge_threshold` 順便標出邊緣（給輪廓描邊用）。

### 2. noisy_sdf：CONCEPT「程序輪廓 noise 擾動」的落地
任何 base_sdf 包一層 `noisy_sdf(base, freq, amp, seed)` 就有有機輪廓——
這是「不像工業感」的關鍵技法。岩石、葉片、傷痕、生物軀幹通用。

### 3. ProcPart 輸出灰階 mask
CONCEPT 點明「部件輸出為灰階圖，顏色交給材質系統」。本檔 generate_* 全部
輸出 RGBA8 但只用白色 + 透明（generate_eye 是例外，因為需要瞳孔黑點）。
顏色交給 godot_material/SpriteMaterial 的 `tint` + `material_tex` 處理。

### 4. CONCEPT 待決事項「部件擺放在 GDScript 側」已確認
CONCEPT 自己已 [x]：「部件擺放與動畫留在 GDScript 側（多個 Sprite2D）」。
本檔不做「合成單張 Image」的路線——程序生成的灰階 mask 直接餵
`godot_character.PaperDoll2D.equip_with_material()` 當 base texture，
擺位走 Bone2D / AnimationPlayer，動畫自由度最大。

## 用法範例

### 程序生成怪物部件 + 紙娃娃組合
```gdscript
# 程序生成五個部件（每次 seed 不同 = 不同個體）
var body_img := ProcPart.generate_body(64, 80, 0.18, rng.randi())
var limb_img := ProcPart.generate_limb(30, 10, 0.65, rng.randi())
var head_img := ProcPart.generate_head(32, 0.12, rng.randi())
var eye_img := ProcPart.generate_eye(12, 0.4)
var wing_img := ProcPart.generate_wing(48, 30, 4, rng.randi())

# 轉 texture
var body_tex := ProcImage.to_texture(body_img)
var head_tex := ProcImage.to_texture(head_img)
# ...

# 用 PaperDoll2D 組裝（每個部件一個 Sprite2D 槽）
character.equip_with_material("body", body_tex, biome_color_tex)
character.equip_with_material("head", head_tex, biome_color_tex)
character.equip_with_material("wing_l", wing_tex, biome_color_tex)
# ...

# 動畫由 AnimationPlayer 控制各部件骨骼旋轉，每幀觸角飄動等
```

### SDF 組合產岩石輪廓
```gdscript
var img := ProcImage.new_image(48, 48)
var base := func(p: Vector2) -> float:
    var c1 := ProcImage.sd_circle(p, Vector2(24, 24), 18)
    var c2 := ProcImage.sd_circle(p, Vector2(28, 20), 8)
    return ProcImage.sd_smooth_union(c1, c2, 4.0)
var sdf := ProcImage.noisy_sdf(base, 0.25, 3.0, 42)
ProcImage.fill_sdf(img, sdf, Color(0.5, 0.45, 0.40))  # 岩石灰色
sprite.texture = ProcImage.to_texture(img)
```

## 待決事項（從 CONCEPT.md 帶過來）

- [x] **部件擺放**：CONCEPT 已決定走 GDScript 多 Sprite2D 路線，本檔對齊。
- [ ] **生物動畫**：與 godot_character 的 Skeleton2D + AnimationPlayer 對齊。
      下一步等真有怪物資料時做。
- [ ] **C++ GDExtension 版**：等到大量生成（一次幾百個怪物）成為效能瓶頸再啟動。
- [ ] **Level 4 接 SD 等生成模型**：遠期，本檔不規範。

## 與其他模組的串接

| 模組 | 互動 |
|------|------|
| `godot_material.SpriteMaterial` | 程序部件輸出的灰階 mask 餵 `material_tex` / `texture` |
| `godot_character.PaperDoll2D.equip_with_material()` | 程序部件 + 染色一行串接 |
| `godot_procgen_mesh`（3D 對應） | 概念平行，3D 端走 ArrayMesh + vertex color |

## 下一步（按需）

1. **真機驗證**：跑五個 generate_* 看視覺、嘗試組合一隻完整怪物。
2. **怪物生成器**：一個 `ProcCreature` 上層 → 隨 seed 決定有幾條腿、有沒有翅膀、有幾顆眼睛，
   調 ProcPart 各函式組合。
3. **C++ port**：若效能瓶頸出現，照本檔 SDF / Bézier API 等價重寫。
