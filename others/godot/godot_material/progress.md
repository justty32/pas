# godot_material — 進度保存

> 最後更新：2026-05-28。從 `CONCEPT.md` 落地的可用初版。

## 一句話：這是什麼

2D Sprite 的「基底 texture × 材質疊加層」shader 套件。傳統做法一個變體出一張圖會貼圖爆炸；
這套讓劍／護甲／角色／tile 用同一張基底，靠材質 texture 與顏色 tint 動態組合出無限變體。

## 檔案清單

```
godot_material/
├── shaders/
│   ├── sprite_material.gdshader            # 單材質疊加（Multiply / Additive / Screen 三模式）
│   └── sprite_material_multislot.gdshader  # 多槽（RGB mask 切刃/柄/護手三區）
├── gd/
│   └── sprite_material.gd                  # SpriteMaterial 靜態 helper
└── progress.md
```

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| 單材質 shader | 三種 blend mode + tint + 強度 | ✅ 完成 |
| 多槽 shader | RGB mask 三通道，各槽獨立 tint/強度 | ✅ 完成 |
| GD helper | `apply()` / `apply_multislot()` / `clear()` / `make_solid_texture()` | ✅ 完成 |
| 真機驗證 | 在 Godot 4 編輯器拖入 Sprite2D 測試 | ⏸ **待真機驗證** |

## 設計重點

### 1. 強度 + Alpha 雙重控制
材質 texture 的 `alpha` 通道天然就是「哪些區域要套這個材質」的遮罩；
`material_strength` 則是全域強度旋鈕。最終疊加係數 `k = strength × material.alpha`。

### 2. tint 與 texture 解耦
程序生成材質時，常見需求是「同一份噪聲紋路，換色就變不同金屬」。`tint` uniform 就是給這用的——
材質 texture 出灰階紋路即可，顏色從 `tint` 餵。

### 3. 多槽用 RGB mask
單張 mask texture 的 R/G/B 三通道分別代表三個材質槽。這比傳三張 mask 省記憶體，
也讓素材製作端只需畫一張遮罩圖。劍刃／劍柄／護手剛好對得上。

### 4. `COLOR = ... * COLOR`
shader 末尾乘上原本的 `COLOR` 是為了保留 Sprite2D 的 `modulate` 與 `self_modulate` 正常運作，
不會被 shader 吃掉。

## 用法範例

```gdscript
# 鐵劍：灰金屬材質
var iron_tex := SpriteMaterial.make_solid_texture(Color(0.7, 0.7, 0.75))
SpriteMaterial.apply(sword_sprite, iron_tex, 1.0, SpriteMaterial.BlendMode.MULTIPLY)

# 紫晶劍：紫色材質 + Additive 微光
var crystal_tex := SpriteMaterial.make_solid_texture(Color(0.7, 0.4, 1.0))
SpriteMaterial.apply(sword_sprite, crystal_tex, 0.6, SpriteMaterial.BlendMode.ADDITIVE)

# 帶 tint 的程序材質（同一張噪聲圖染不同色）
SpriteMaterial.apply(sword_sprite, noise_tex, 1.0,
		SpriteMaterial.BlendMode.MULTIPLY, Color(0.3, 0.8, 0.5))

# 多槽：劍刃藍、劍柄棕、護手金
SpriteMaterial.apply_multislot(sword_sprite, sword_region_mask,
		null, null, null,
		PackedColorArray([Color.STEEL_BLUE, Color(0.4, 0.25, 0.1), Color.GOLD]))
```

## 整合進真實 Godot 專案

1. 把整個 `godot_material/` 資料夾複製到專案內（建議放 `res://addons/godot_material/`）。
2. 若改放別處，修改 `gd/sprite_material.gd` 開頭兩個 `_PATH` 常數。
3. GDScript 自動取得 `class_name SpriteMaterial`，全專案任何地方都可用。

## 待決事項（從 CONCEPT.md 帶過來）

- [ ] 材質 texture 是藝術家繪製還是程序生成（噪聲 + 色相旋轉）—— 兩條路都支援，看遊戲方向。
- [ ] 稀有度色調是材質 texture 的一部分還是額外 uniform —— 目前 `tint` 已支援，看用法是否夠用。
- [ ] Tilemap 走哪個方案（Texture2DArray vs 分層）—— 目前未涵蓋，等 `godot_world_map` 啟動時再回來補。

## 下一步（按需）

1. **真機驗證**：在 Godot 4 拖一個 Sprite2D + 任一張 PNG，試 `SpriteMaterial.apply(...)`，
   觀察三種 blend mode 是否符合預期。出問題回報，修 shader。
2. **配套工具**（選用）：寫一個 `make_palette()` 從 Color 陣列產 1×N 的 palette texture，
   用 UV.x 索引取色（適合像素風）。
3. **Tilemap 整合**：等 `godot_world_map` 開工時，把 Texture2DArray 方案落地到此倉庫。
