# 2D vs Low Poly 3D 技術取捨分析

> 決策文件，非逐步教學。彙整「為何最終選 Low Poly 3D」，並把每條判斷連到已完成的實作 / 教學作佐證。
> **結論已定（2026-05-22）：採用 Low Poly 3D。** 本文補強論證並追蹤剩餘待決定。

概念來源：`others/godot/godot_lowpoly/CONCEPT.md`。

---

## 背景

原始預想是「先做 2D，再挑戰 3D」。但在規劃 2D tilemap 大世界地圖與程序藝術系統時發現：**大世界地形與生態系那塊，3D 反而是「理所當然就這樣做」，2D 的分層方案反而需要更多設計與自訂 shader**。Low Poly 3D 在多項工作量上比 2D 更低，遂改採 3D。

---

## 逐需求取捨對比

每列附「為何」與對應已完成教學 / 實作的佐證連結。

| 需求 | 2D 方案 | Low Poly 3D 方案 | 優勢方 | 為何 / 佐證 |
|------|---------|-----------------|--------|------------|
| 地形高低差 | 丘陵 shader 疊加層，視覺有限 | poly 高度直接表現，燈光自動加深 | **3D** | hilliness 直接驅動 vertex Y，燈光天生加深陰影；見 [[gdextension_3d_world_map]]、`mapcore_godot/src/terrain_mesh_builder.cpp`。2D 須自訂等高線 / 陰影 shader（見 [[gdextension_world_map_2d]] 的多層方案）|
| 生態圈 / 植被 | 每種 tile 需 shader 混合 | 3D 物件直接擺放，密度隨機即可 | **3D** | MultiMesh GPU instancing 散佈樹 / 岩，密度隨機；見 [[gdextension_procgen_mesh]]、`biome_scatter.gd`。2D 須為每種組合設計可混合 tile |
| 角色換裝 | Sprite2D 多層貼圖拼接 | Blender 骨骼 + 材質，工具鏈成熟 | 平手 | 2D 見 [[gdextension_character_2d]]（自建疊層 + 自訂 shader）；3D 見 [[gdextension_character_3d]]（glTF + `material_override` 原生）。各有成熟路線 |
| 材質複用 | **需自訂 shader overlay** | 標準 UV + albedo，天生如此 | **3D** | 2D 要自寫 `sprite_material.gdshader`（[[gdextension_material_2d]]）；3D 直接 `StandardMaterial3D` + `material_override`（[[gdextension_material_3d]]）|
| 程序生成素材 | 像素操作（C++ GDExtension）| 多邊形操作（C++ 生成 mesh）| 平手 | 概念平行：逐像素 `Image`（[[gdextension_procgen_art]]）vs 逐頂點 `ArrayMesh`（[[gdextension_procgen_mesh]]，已實作）|
| 2D UI / HUD | 原生 | Control 節點，同樣原生 | 平手 | 兩者皆用 `Control`，無差異 |
| 美術門檻 | 像素畫 or 程序像素 | low poly 建模 or 程序 mesh | 略偏 2D | 像素畫門檻略低；但兩者都可程序生成，差距被 procgen 拉平 |

**判斷集中點**：地形、植被、材質三項 3D 明顯佔優，其餘平手——故 3D 整體勝出。

---

## 規避「程序生成工業感」的已驗證技法

3D 路線最大風險是程序生成的千篇一律感，已用下列技法緩解（多數已實作於 mapcore_godot）：

| 技法 | 實作狀態 | 位置 |
|------|---------|------|
| 頂點擾動（vertex jitter）| ✅ | `terrain_mesh_builder.cpp`（每格頂點 ±jitter）|
| Noise displacement（hash noise）| ✅ | `procgen_mesh_builder.cpp`（hf3 hash 位移）|
| 尺度變化（隨機旋轉 + 縮放）| ✅ | `biome_scatter.gd`（0.45x~1.55x）|
| 非對稱（非均勻 XYZ 縮放）| ✅ | `procgen_mesh_builder.cpp`（各軸 0.6~1.4 倍）|
| 面色調變化（±12%）| ✅ | `procgen_mesh_builder.cpp`（per-face hash）|
| 不規則面細分 | ❌ 未實作 | 目前 uniform grid |

---

## 既有實作索引（3D 路線可行性的證據）

3D 路線並非紙上談兵，核心子系統皆已實作於 `others/gamecore/mapcore_godot`：

| 系統 | 位置 | 對應教學 |
|------|------|---------|
| 地形 Mesh 生成 | `src/terrain_mesh_builder.h/.cpp` | [[gdextension_3d_world_map]] |
| 程序岩石 / 樹 | `src/procgen_mesh_builder.h/.cpp` | [[gdextension_procgen_mesh]] |
| 地圖渲染器 | `demo/scenes/map_renderer_3d.gd` | — |
| 材質工廠 | `demo/scenes/material_library.gd` | [[gdextension_material_3d]] |
| 生態散佈 | `demo/scenes/biome_scatter.gd` | [[gdextension_procgen_mesh]] |
| 鏡頭控制 | `demo/scenes/camera_rig_3d.gd` | [[gdextension_camera_rig]] |
| 選取高亮（3D）| `demo/shaders/selection_outline.gdshader` | [[gdextension_selection_highlight]] |
| 邊緣發光 | `demo/shaders/rim_glow.gdshader` | [[gdextension_material_3d]] |

> mapcore 核心 C++ 邏輯（terrain / hilliness / water_depth / features）**不需更動**即可驅動 3D；改動僅在 GDExtension 橋接層（見 lowpoly CONCEPT 第 105–118 行的對照表）。唯一明顯缺口：河流尚未從 `TypedArray<Dict>` 轉成 3D curve mesh（CONCEPT 標 ❌）。

---

## 結論與建議路線

1. **採用 Low Poly 3D**（已決定）。地形 / 生態 / 材質三項決定性佔優，且核心系統已實作驗證。
2. **2D 資產不浪費**：[[gdextension_world_map_2d]]、[[gdextension_character_2d]]、[[gdextension_material_2d]] 等 2D 教學仍是 Minimap（[[gdextension_minimap]]）、UI、以及「2D 後備 / 對照」的有效參考——3D 場景上的 minimap、HUD 本質仍是 2D。
3. **下一步補完整 demo**：以 `mapcore_godot/demo` 為載體跑端到端（地形 + 水 + 散佈 + 鏡頭 + 選取已就緒），補河流 3D curve mesh 即達完整可玩原型。

---

## 待決定

逐項回應 `others/godot/godot_lowpoly/CONCEPT.md` 仍開放的事項（已決定者見 CONCEPT 內 `[x]`）：

- **角色：low poly 3D vs billboard 2D sprite？**
  - **建議：主要 / 近景單位用 low poly 3D（[[gdextension_character_3d]]），遠景 / 大量單位用 billboard 或 bake sprite LOD。** 理由：與已定的 3D 地形維度一致，避免「3D 地形 + 2D 立繪」的視覺割裂與燈光不一致；3D 角色的 Blender / glTF 工具鏈成熟（換裝靠 `material_override` 原生）。大量同款單位的 draw call 用 `MultiMeshInstance3D` LOD 解（見 [[gdextension_character_3d]] 效能節）。

- **Godot 3D pipeline 完整驗證（待跑完整 demo）？**
  - **建議：以 `mapcore_godot/demo` 為驗證載體跑端到端，缺口僅「河流 3D curve mesh」與 demo 整合。** 理由：地形 / 程序 mesh / 材質 / 散佈 / 鏡頭 / 選取六大系統皆已實作（見上方索引），單項已部分驗證；補上河流（把現有 `TypedArray<Dict>` 河流資料轉成 3D curve / mesh）並串成一個完整場景，即完成 pipeline 驗證。

---

*記錄時間：2026-05-23*
*狀態：決策分析；已決定採用 Low Poly 3D，核心系統已實作於 mapcore_godot，待補河流與完整 demo*
