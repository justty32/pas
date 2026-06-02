# Session Log — opennefia-cpp

- **起始時間**: 2026-06-01
- **Agent**: Claude Code (Opus 4.8)
- **源專案**: OpenNefia（C# / .NET 8.0）；**架構藍本**: medps（C++20 EnTT + cereal）
- **衍生目標（一句話）**: 用 godot-free 的純 C++20，依 medps 已驗證做法重寫 OpenNefia 引擎核心（本階段不碰前端 / Godot）。

---

- 2026-06-01: 依 create_workflow.md 初始化專案。建立 PROJECT.md（範圍：只做核心、前端暫緩；技術棧 EnTT/cereal/yaml-cpp/spdlog；完成定義）、CLAUDE.md（agent 鐵則）、docs/01_core_architecture.md（核心分層、ECS、自由函式系統、原型、序列化、服務）、docs/02_subsystem_mapping.md（OpenNefia 子系統範圍表 + 三大反射取代）、docs/03_roadmap.md（Phase 0–4 核心路線圖 + 未來前端）。src/ 尚空，下一步為 Phase 0 CMake 雙目標骨架。
- 2026-06-01: Phase 0 完成。建立 CMakeLists.txt（FetchContent：EnTT v3.16.0 / cereal v1.3.2 / spdlog v1.14.1 / doctest v2.4.11；CMAKE_POLICY_VERSION_MINIMUM=3.5 相容 CMake 4.0+；yaml-cpp 延至 Phase 2）、src/core/version.h+cpp、tests/CMakeLists.txt、tests/src/smoke_test.cpp。cmake --build 通過，ctest 1/1 綠燈。
- 2026-06-01: Phase 1 完成。建立 core/ecs/event_bus.h（void* 類型抹除定向派發 + entt::dispatcher 廣播）、core/ecs/entity_manager.h+cpp（薄封裝 + 系統 vector tick）、core/ecs/system_ctx.h、core/services/service_context.h+cpp（spdlog）、core/components/meta_data_component.h+spatial_component.h、core/util/vector2i.h+resource_path.h、tests 重構（main.cpp 入口 + test_ecs.cpp）。DOCTEST_CONFIG_USE_STD_HEADERS 修正 MSVC 2022 string_view ostream 報錯。ctest 8/8 cases, 20 assertions 全綠。
- 2026-06-01: Phase 2 完成。引入 yaml-cpp 0.8.0（CMAKE_POLICY_VERSION_MINIMUM=3.5 相容）。建立 core/prototypes/prototype_id.h+prototype.h+prototype_manager.h+cpp（零反射 ComponentLoader 顯式登錄、拓撲繼承解析、YAML::Clone 修正 detail::node 共享污染）、data/test_prototypes.yaml（3層繼承）、tests/test_prototypes.cpp（12 個原型測試）。EntityManager::spawn() 便利包裝 + forward decl。ctest 20/20 cases, 70 assertions 全綠。
- 2026-06-01: Phase 3 完成。建立 core/serialize/all_components.h+entt_cereal_archive.h+save_load.h（移植 medps 三件套）+save_store.h（SaveStore/FolderSaveStore）；SpatialComponent 換成 save/load split（entt::entity parent round-trip）；tests/test_serialize.cpp（9 個序列化測試）。坑：entt::entity==null_t 在 CHECK 中歧義需先求 bool；cereal std::string 需 cereal/types/string.hpp。ctest 29/29 cases, 95 assertions 全綠。
- 2026-06-01: Phase 4 完成。建立 core/maps/tile.h（Tile struct + WALKABLE/BLOCKS_SIGHT 旗標）+map_data.h（MapData 稠密網格 component）；AllComponents 加入 MapData；save_load.h 加入 cereal/types/vector.hpp；tests/test_phase4.cpp（7 個測試，含 Phase 4 整合測試）。36/36 cases, 139 assertions 全綠。核心階段 Phase 0–4 全部完成。
- 2026-06-02: F1 完成（GDExtension smoke test）。建立 src/gbind/（opennefia_core_gd.h+cpp + register_types.h+cpp）；godot_test/（opennefia.gdextension + project.godot + smoke_test.gd + bin/opennefia_gd.dll 1.4 MB）；cmake -DOPENNEFIA_BUILD_GDEXTENSION=ON 成功，opennefia_gd.dll 產出，工具鏈端到端打通。下一步：F2 TileMapLayer 渲染。
- 2026-06-02: F2 完成（地圖資料橋接 + Image 渲染）。新增 src/gbind/opennefia_world_gd.h+cpp（OpenNefiaWorld : Node，持有 EntityManager+ServiceContext，setup_test_world 20×15 地圖，generate_map_image 三色 Image）；register_types.cpp 加入 OpenNefiaWorld；godot_test/map_view.gd（動態建 World、Image→ImageTexture→Sprite2D、Camera2D 置中）。opennefia_gd.dll 更新至 4.9 MB。
- 2026-06-02: F3 完成（輸入 → 核心移動 → Signal 刷新 + UI）。OpenNefiaWorld 新增 move(dx,dy)/wait_turn()/get_hero_x/y/turn_count() + world_changed signal；map_view.gd 新增 _unhandled_input（WASD/arrow/numpad 8向+wait）、_on_world_changed 刷新 Sprite2D、InfoLabel 顯示座標+回合數。cmake 建置通過（5.1 MB DLL）。
</content>

- 2026-06-02: NPC AI 完成。新增 core/components/npc_ai_component.h（空 struct，已加入 AllComponents）、core/systems/npc_ai_system.h+cpp（wander AI，固定種子 RNG，4 方向試探）；OpenNefiaWorld 新增 EventBus + advance_turn()（tick EM + emit world_changed）；setup_test_world 生成 3 隻 NPC（帶 NpcAiComponent）；generate_map_image 四色（牆/地板/NPC紅/英雄黃）；修復 entity_manager.h emplace 回傳型別（decltype(auto)，EnTT 空型別 emplace 回傳 void）。36/36 tests 仍全綠，DLL 更新完成。

- 2026-06-02: FOV + NPC chase + 碰撞信號 + F4 音效框架完成。新增 fov_system.h+cpp（Bresenham LOS 射線 FOV，radius=8）；map_data.h 加 visible/explored 陣列 + split save/load；npc_ai_system 改為距離 8 格以內追蹤英雄（大 delta 軸優先），否則 wander；OpenNefiaWorld 加 hero_bumped_wall / hero_bumped_npc 信號 + recompute_fov()；generate_map_image 改三層 FOV 渲染（未探索/暗/原色）；map_view.gd 接收碰撞信號 + AudioStreamPlayer 音效框架（plug-in .ogg 即可啟用）。36 tests 仍全綠。

- 2026-06-02: 戰鬥系統完成。新增 health_component.h（hp/max_hp，cereal serialize）；AllComponents 加入 HealthComponent；Hero 20/20 HP、NPC 10/10 HP；hero 撞 NPC → 扣 3 HP（致死則 destroy 實體 + emit npc_died，否則 emit hero_bumped_npc）；npc_ai_system 在 Chebyshev==1 時改為攻擊 hero（扣 2 HP）而非移動；advance_turn 後偵測 hero HP ≤ 0 → emit game_over + 鎖定輸入；InfoLabel 顯示 HP；map_view.gd 接 npc_died / game_over 信號。Build 成功，DLL 更新。

- 2026-06-02: BSP 地城生成完成。新增 core/maps/map_gen.h+cpp（BSP 地下城：遞迴分割、葉節點挖房間、L 形走廊連接、回傳 Room 列表）；地圖升級 60×40；hero 放第一房間中心、NPC 依序放後續房間（最多 5 隻）；GDScript 鏡頭跟隨英雄；InfoLabel 加 Enemies 計數；get_npc_count() 暴露給 GDScript。3 個 subagent 並行開發，build 成功。

- 2026-06-02: 多樓層完成。tile.h 加 TILE_STAIR_DOWN + is_stair_down()；setup_map() 抽出（可重複呼叫）；setup_test_world 改用 systems_ready_ 防止重複 add_system；末尾房間放樓梯（金黃渲染）；next_floor() 銷毀舊 NPC+地圖重生成英雄保留 HP；restart() 完整重置；move() 踩樓梯觸發 next_floor；floor_changed 信號；NPC 隨層數加血（10 + (floor-1)*2），數量上限 min(4+floor, 8)；GDScript 接 floor_changed + R 重置 + InfoLabel 顯示層數。Build 成功。

- 2026-06-02: 物品/拾取完成。新增 item_component.h（ItemType::health_potion, value）；AllComponents 加 ItemComponent；setup_map 末尾房間（跳過英雄房與樓梯房）60% 機率生成回血藥（heal 隨層數增加）；物品銷毀納入 setup_map 清理流程；move() 踩到物品自動拾取回 HP（capped at max_hp），emit item_picked_up；generate_map_image 加綠點渲染（層級 tiles→items→NPC→hero）；GDScript 接 item_picked_up 信號。Build 成功。