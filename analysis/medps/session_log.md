# Session Log — medps 分析

- 2026-06-01: 建立 analysis/medps 結構。閱讀核心源碼（zone_key.h、global_manager.h/.cpp、serialize/{all_components,zone_io,entt_cereal_archive,zone_store,chunked_zone_store}.h、chunk_key.h、systems/movement.h、components/*、util/mydef.h、CMakeLists.txt、work/design/zone_layers.md），完成 Level 1（總覽）與 Level 2（核心設計模式）分析。聚焦純 C++ 核心 `gcore/`；godot 前端 `gbind/` 依使用者指示暫不深入。
