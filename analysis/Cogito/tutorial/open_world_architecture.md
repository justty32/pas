# 系統架構：如何使用 COGITO 製作開放世界 (Open World) 遊戲

在 Godot 4 與 COGITO 中製作大型開放世界遊戲，需要面臨效能、地圖無縫切換、記憶體管理等挑戰。COGITO 預設的 `CogitoSceneManager` 是為「載入畫面過場」設計的，因此要實作無縫開放世界，您必須對架構進行區塊化 (Chunking) 與非同步加載 (Async Loading)。

---

## 1. 核心引擎設定：雙精度 (Double Precision)
當開放世界地圖非常大時，距離世界中心點 (0,0,0) 過遠的物件與物理運算會產生浮點數精度遺失，導致模型抖動 (Jitter) 與物理異常。
- **解決方案**：
  在匯出遊戲 (Export) 時，請確保您使用的 Godot 引擎建置版本啟用了 **Double Precision** (`double` builds)。Godot 官方有提供支援雙精度的引擎執行檔。

---

## 2. 地圖區塊化與無縫切換 (Level Streaming)

開放世界不能一次將所有物件載入記憶體。您必須將地圖切分為多個 `Chunk_X_Y.tscn`（例如 500x500 公尺的區塊）。

### 實作步驟：背景非同步加載
1. **建立 Chunk 管理器**：編寫一個全局腳本 (Autoload)，追蹤玩家當前的座標。
2. **計算相鄰區塊**：根據玩家所在的 Chunk 座標，計算出周圍九宮格的 Chunk 名稱。
3. **ResourceLoader 非同步加載**：
   ```gdscript
   # 請求背景載入
   ResourceLoader.load_threaded_request("res://Maps/Chunk_0_1.tscn")
   
   # 每幀檢查進度
   var progress = []
   var status = ResourceLoader.load_threaded_get_status("res://Maps/Chunk_0_1.tscn", progress)
   if status == ResourceLoader.THREAD_LOAD_LOADED:
       var chunk_scene = ResourceLoader.load_threaded_get("res://Maps/Chunk_0_1.tscn")
       var chunk_instance = chunk_scene.instantiate()
       get_tree().current_scene.add_child(chunk_instance)
   ```
4. **卸載遠離的區塊**：當玩家離開足夠遠的距離時，呼叫 `queue_free()` 釋放舊的 Chunk。

---

## 3. 持久化存檔 (Persistence) 的適應

COGITO 的 `CogitoSceneManager` 將整個場景的 `Persist` 物件存成單一 JSON 檔案。在開放世界中，這會導致存檔極大且載入極慢。

### 改造存檔系統：基於 Chunk 的局部存檔
1. **取消全域存檔掃描**：不要在遊戲存檔時掃描全場景，改為**當 Chunk 即將被卸載 (queue_free) 時**，觸發該 Chunk 內部 `Persist` 物件的存檔。
2. **分離 JSON 檔案**：將 `_scene_state.write_state()` 改寫為按照 Chunk 名稱儲存（例如 `user://save_slot_1/Chunk_0_1.json`）。
3. **載入 Chunk 時還原**：當非同步載入 `Chunk_0_1.tscn` 完成後，立刻讀取對應的 JSON 並還原該區塊內的掉落物與敵人狀態。

---

## 4. 地形系統 (Terrain System) 整合

Godot 4 預設沒有強大的地形編輯器，對於開放世界，強烈建議使用第三方插件：
- **推薦插件**：**Terrain3D** (由 Tokisan Games 開發)。它支援 LOD、海量植被 (Foliage) 與快速的地形雕刻。
- **與 COGITO 整合**：COGITO 的動態腳步聲系統 `FootstepSurfaceDetector` 預設是掃描 Mesh 的 `Material`。對於 Terrain3D 的無縫地形貼圖，您需要修改腳步探測器，讓它讀取 Terrain3D 的 `get_texture_id(collision_point)`，以對應播放草地或泥土的聲音。

---

## 5. 效能優化 (Optimization)

在海量的草地、樹木與 NPC 中，效能是關鍵。
1. **LOD (多層次細節)**：
   - Godot 4 會自動為匯入的 `.glb` 生成 LOD。確保遠處的樹木和建築面數自動降低。
2. **VisibilityRange (可見範圍)**：
   - 在 `MeshInstance3D` 的 Inspector 中設定 `Visibility Range`。
   - 例如：`Begin Margin` = 0, `End Margin` = 150。超過 150 公尺的物件將不會被 GPU 渲染。
3. **AI 睡眠 (AI Hibernation)**：
   - NPC 腳本 (`cogito_npc.gd`) 的 `_physics_process` 不應在玩家 200 公尺外執行。
   - 使用一個 `Timer` 每秒檢查一次玩家距離。如果距離大於 200，停止呼叫 `move_and_slide()`，甚至停止更新 `AnimationTree`。
4. **Distance Fade (距離衰減)**：
   - 對於 `OmniLight3D` 或材質，開啟 `Distance Fade`。這不僅讓物件平滑消失，還能節省光影計算。

---

## 6. 動態 NavMesh (導航網格)

在開放世界中烘焙單一巨大的 NavMesh 是不可能的。
1. **依 Chunk 切割 Region**：在每個 Chunk 內放置獨立的 `NavigationRegion3D`。
2. **無縫拼接**：Godot 4 的 Navigation Server 支援多個 `NavigationRegion3D` 的邊緣自動拼接。只要相鄰 Chunk 的 NavMesh 邊緣重合，NPC 就能跨越 Chunk 追擊。
3. **動態烘焙**：若地形有被破壞，或玩家放置了大型建築，請對該 Chunk 的 `NavigationRegion3D` 呼叫 `bake_navigation_mesh(true)`（開啟背景非同步烘焙，避免卡頓）。

## 總結
製作開放世界遊戲，您需要將 COGITO 單一場景的思維轉化為「動態載入卸載 (Streaming)」思維。首要任務是建立一套穩定的 Chunk 加載系統，並隨後將 COGITO 的 `CogitoSceneManager` 存讀檔邏輯改寫為針對單一 Chunk 運作，最後再套用 Terrain3D 處理廣大的地形與 LOD。
