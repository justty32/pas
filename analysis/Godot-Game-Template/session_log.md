# Godot-Game-Template 分析操作日誌

- **起始時間**：2026-05-25
- **作業系統**：Windows 11（PowerShell / bash）
- **Agent**：Claude Code (Opus 4.7, 1M context)
- **專案根路徑**：`C:\code\mine\pas\projects\Godot-Game-Template`
- **專案性質**：Maaack's Godot Game Template（GDScript / Godot 4.6，向下相容 4.3+），UI 選單與無障礙框架，2D/3D 通用
- **注意**：與工作區內 `Godot-GameTemplate`（俯視角射擊框架）為**不同**專案，勿混淆

---

## 操作紀錄

- 讀取 `analysis_workflow.md`、Cogito 既有 Level 1/2 範例，確立格式與深度基準。
- 探索 `project.godot`、README、頂層與 `addons/maaacks_game_template/` 目錄結構，確認核心邏輯全部位於 `base/`（核心）、`extras/`（擴充）、`examples/`（範例繼承場景）三層。
- 讀取全部 base autoload 與設定持久化腳本（`app_config.gd`、`app_settings.gd`、`player_config.gd`、`scene_loader.gd`、`global_state.gd`、`music_controller.gd`、`ui_sound_controller.gd`）。
- 讀取選單系統腳本（`main_menu.gd`、`option_control.gd`、各 options menu、輸入重綁定 list/tree/key_assignment、`overlaid_window.gd`、`pause_menu_controller.gd`、`loading_screen.gd`、`opening.gd`）。
- 讀取 extras 的 `level_manager.gd`、`level_loader.gd` 與頂層 `game_state.gd`、`level_and_state_manager.gd`。
- 建立分析目錄結構與本日誌。
- 撰寫 `architecture/level1_overview.md`（專案資訊、目錄/三層架構、autoload、入口流程、構建執行）。
- 撰寫 `architecture/level2_core_modules.md`（設定持久化資料流、選項控件、場景載入、音訊控制器、選單與覆蓋窗、關卡/狀態管理）。
- 撰寫 `architecture/level3_input_remapping.md`（輸入重綁定子系統深入）。
- 撰寫 `architecture/level3_settings_persistence.md`（設定儲存/載入機制深入）。
- 撰寫 `architecture/level3_scene_loading.md`（場景載入與轉場子系統深入）。
- 撰寫 `tutorial/howto_integrate_menus_into_existing_project.md`（接入既有專案教學）。
- 撰寫 `tutorial/howto_add_custom_option_page.md`（新增自訂選項頁教學）。
