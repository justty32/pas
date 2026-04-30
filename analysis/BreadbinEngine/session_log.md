# BreadbinEngine Session Log

## 2026-04-30

- Level 1 初始探索：讀取 README、project.godot，確認為 Godot 4 Action RPG 框架，仿 Dark Souls 風格。
- Level 2 核心模組職責：閱讀全部 25 個 GDScript 檔案，理解 ActorBase/PlayerActor/AIActor 繼承體系、AttackTable CSV 驅動系統、WeaponBase 招式陣列、Hitbox 碰撞層設計。
- 建立 `analysis/BreadbinEngine/` 目錄結構（architecture、tutorial、answers、details、others、gemini_temp）。
- 撰寫 `architecture/overview.md`：涵蓋技術棧、目錄結構、Autoload、Class 繼承、物理層、隊伍矩陣、輸入對照、儲存系統。
- 撰寫 `architecture/combat_system.md`：攻擊表設計、連擊 Pipeline、Hitbox 激活流程、傷害倍率系統、動畫雙軌架構。
- 撰寫 `architecture/ai_system.md`：Tier 系統、三層攻擊機率、Inspector 可調參數、已知問題。
