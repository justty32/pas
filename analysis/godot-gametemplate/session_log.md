2026-04-15: 初始化 Godot-GameTemplate 分析環境，完成 Level 1 初始探索與基礎架構分析。
2026-04-15: 完成 Level 2 核心模組職責分析，涵蓋 ResourceNode 模式、Mover 邏輯與戰鬥系統。
2026-04-15: 完成 Level 3 進階機制分析，揭示 AI 統一輸入與樹狀實體追蹤系統。
2026-04-15: 完成 Level 4 遊戲性分析，詳細解析了複合傷害計算、狀態效果與資源化物品系統。
2026-04-15: 完成 Level 5 技術架構分析，涵蓋 SaveableResource 系統與 Steam 整合機制。
2026-04-15: 完成 Level 6 視覺特效分析，解密了溶解轉場著色器與殘影系統。全階段分析 (Level 1-6) 已達成。
2026-04-15: 本次會話結束。成功完成 Godot-GameTemplate 的全流程架構分析，並產出 Level 1-6 詳細文件。
2026-04-15: 撰寫教學 01：新增自定義遠程武器，涵蓋從傷害定義到資料庫註冊的全流程。
2026-04-15: 撰寫教學 02：將 MoverTopDown2D 遷移至 GDExtension，涵蓋 C++ 邏輯轉譯與效能優化。
2026-04-15: 撰寫教學 03：Boss AI 行為與 GDExtension 優化，解析 Big Jelly 的決策循環與分裂機制。
2026-05-25: 核對全部 Level 1-6 與 3 篇教學對照當前源碼（Claude Code, Opus 4.7）；確認 Godot 4.6、autoload 名稱與入口場景皆正確。
2026-05-25: Level 1-2 修正——補腳本路徑/行號、修正 get_resource 鍵名為 "movement"、Projectile 信號名為 prepare_exit_event，並新增資源依賴流向 Mermaid 圖。
2026-05-25: Level 3 修正——波次資料實際來源為 EnemyManager.wave_queue.waves，補上 BotInput/TargetFinder/ActiveEnemy 行號與信號鏈細節。
2026-05-25: Level 4 重大修正——澄清存在兩套 DamageType 枚舉（傷害實用 DamageTypeResource）、修正傷害公式、更正 ItemResource/WeaponItemResource 欄位（無 item_name/weapon_scene）、背包序列化為 .tres 非 JSON。
2026-05-25: Level 5-6 修正——標明 Steam 後端仍為 TODO（與 FILE 同實作）、補 SaveableResource/PersistentData 行號、修正 AfterImage 由 AnimationPlayer 驅動與 dust shader 實際檔名 dust_partickle.gdshader。
2026-05-25: 教學 01 修正——更正 ProjectileSpawner 欄位 (projectile_instance_resource/projectile_angles，無 fire_rate) 與 weapon_database.tres 的 list 欄位；教學 02/03 補核對註記並修正 2.5D 補償算法 (axis_compensation = ONE/axis_multiplication)。
2026-05-25: 生成 HTML 導覽層（html/index.html、architecture.html、tutorial.html、_shared.css），複用 Cogito 既有樣式。
