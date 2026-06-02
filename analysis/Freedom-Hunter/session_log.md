# Freedom-Hunter 操作日誌

| 時間 | 操作 |
|------|------|
| 2026-04-30 | Level 1+2 初始分析：讀取 README、project.godot、所有核心 .gd 腳本，撰寫完整架構概覽至 architecture/overview.md |
| 2026-04-30 | Level 3-6 深入分析：撰寫 details/ 下四份詳細文件，涵蓋 Entity/戰鬥、道具/物品欄、武器/裝備、相機/HUD/世界系統 |
| 2026-04-30 | 美術/動畫/音效分析：解析 dragon.tscn、male.tscn、grass.gdshader，撰寫怪物美術、玩家動畫操控、草地Shader三份文件 |
| 2026-04-30 | 撰寫完整分析總結：architecture/summary.md，含架構一覽、五大亮點、系統完成度表、已知問題彙整 |
| 2026-06-01 | 核對分析文件與原始碼：發現 weapon.gd:99 傳參順序錯誤（element/weapon/entity 全部位移），修正為 null, self, player；並補入 summary.md 已知問題表 |
| 2026-06-01 | 深化 entity_combat_system.md 與 weapon_equipment_system.md：補充傷害計算邊界條件、撞牆公式臨界值、異常狀態重複觸發語意、耐力恢復各狀態倍率、多人不一致窗口、blunt/sharpen 溢出邏輯、Authority 缺失問題、銳利度加乘實作分析、BoneAttachment 線性搜尋效能問題 |
| 2026-06-01 | 深化 item_inventory_system.md 與 camera_ui_world_system.md：涵蓋堆疊邊界、商店定價 bug（量不乘價）、Barrel 連鎖延遲範圍（0.1~0.5s）、CannonBall 所有權與消耗機制、快捷列 wrapi 環繞、deferred 拖放恢復、Lerp 跨360°同步重置、縮放無穿牆防護、互動UI視錐處理、通知佇列無上限、跨欄拖曳 dragging 引用語義 |
| 2026-06-01 | 深化 monster_art_animation.md 與 grass_shader.md：補充 NavigationAgent 5 單位邊界震盪分析、RayCast 1000ms 冷卻機制與快速進出行為、感嘆號逃脫條件與 combat 重置路徑、died() 各子節點狀態與 monster drop.gd 接管流程、fire 粒子精確時序（t=0 開/t=3.5 關）及 loop_wrap 無效原因、TIME float32 精度邊界（194天/2.3小時）、Worley 54,000 sin/幀成本分析、wind_direction 零向量 NaN 風險、GrassFactory UV2.y 設定原始碼核對、INSTANCE_CUSTOM 四通道格式對照（含 x×y 雙乘邏輯） |
| 2026-06-01 | 深化 multiplayer_network_system.md 與 player_art_animation_controls.md：補入 transform RPC 注解根本原因（無接收端函式）、遠端位置完全不更新的後果、廣播流程 Mermaid 時序圖、斷線廣播機制說明、武器 _on_body_entered Authority 缺失的雙重傷害風險、怪物客戶端位置凍結但 HP 仍扣的矛盾行為、lobby.gd Godot4 移植完成但呼叫端仍有 yield 殘留、register_player 五項安全漏洞（ID 偽造/Username 注入/Transform 傳送攻擊）、attack() 忽略參數的靜默失敗分析、連按攻擊 lock 機制、AnimationsWithSounds 換模型音效重設手冊、BoxShape 尖角側向碰撞問題 |
| 2026-06-01 | 生成 HTML 導覽層至 html/：_shared.css + index/architecture/combat/items/world/multiplayer/animation/shader 共 9 個檔案，涵蓋所有深化分析與已知 Bug 彙整 |
