# Session Log — opennefia-cpp

- **起始時間**: 2026-06-01
- **Agent**: Claude Code (Opus 4.8)
- **源專案**: OpenNefia（C# / .NET 8.0）；**架構藍本**: medps（C++20 EnTT + cereal）
- **衍生目標（一句話）**: 用 godot-free 的純 C++20，依 medps 已驗證做法重寫 OpenNefia 引擎核心（本階段不碰前端 / Godot）。

---

- 2026-06-01: 依 create_workflow.md 初始化專案。建立 PROJECT.md（範圍：只做核心、前端暫緩；技術棧 EnTT/cereal/yaml-cpp/spdlog；完成定義）、CLAUDE.md（agent 鐵則）、docs/01_core_architecture.md（核心分層、ECS、自由函式系統、原型、序列化、服務）、docs/02_subsystem_mapping.md（OpenNefia 子系統範圍表 + 三大反射取代）、docs/03_roadmap.md（Phase 0–4 核心路線圖 + 未來前端）。src/ 尚空，下一步為 Phase 0 CMake 雙目標骨架。
- 2026-06-01: Phase 0 完成。建立 CMakeLists.txt（FetchContent：EnTT v3.16.0 / cereal v1.3.2 / spdlog v1.14.1 / doctest v2.4.11；CMAKE_POLICY_VERSION_MINIMUM=3.5 相容 CMake 4.0+；yaml-cpp 延至 Phase 2）、src/core/version.h+cpp、tests/CMakeLists.txt、tests/src/smoke_test.cpp。cmake --build 通過，ctest 1/1 綠燈。
- 2026-06-01: Phase 1 完成。建立 core/ecs/event_bus.h（void* 類型抹除定向派發 + entt::dispatcher 廣播）、core/ecs/entity_manager.h+cpp（薄封裝 + 系統 vector tick）、core/ecs/system_ctx.h、core/services/service_context.h+cpp（spdlog）、core/components/meta_data_component.h+spatial_component.h、core/util/vector2i.h+resource_path.h、tests 重構（main.cpp 入口 + test_ecs.cpp）。DOCTEST_CONFIG_USE_STD_HEADERS 修正 MSVC 2022 string_view ostream 報錯。ctest 8/8 cases, 20 assertions 全綠。
</content>
