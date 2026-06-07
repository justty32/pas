# session_log — gamecore-zone

- 移除死亡 include（event_bus.h、meta_data_component.h、prototype_manager.h），更新 system_ctx.h（移除 EventBus 依賴）、entity_manager.h/cpp（移除 spawn/PrototypeManager）；改寫四份測試檔，25 tests 全綠。
- GDExtension 建置通過（cmake -DZONE_BUILD_GDEXTENSION=ON）並 headless VERIFY PASSED：修三處編譯錯誤（FolderSaveStore→路徑 API、size_hint→size、version() const、string_view.c_str）；verify.gd 修 OpenNefiaCore→ZoneCore；godot-mono 4.6.3 輸出 zone core 0.0.1-alpha、60×40 地圖、save/load round-trip 全綠。
- 設計 §7 回合迴圈：時間驅動 actor poll，定案玩家控制與 Godot↔C++ 介面（純設計，尚未實作）。
- 新增 order 表模型 turn-loop-example.cpp（多角色操控版）：因玩家控制多角色、無單一 hero，§7「先 tick hero 再 exclude」作廢；定案 阻塞=玩家角色 idle 且無指令、下令順序可選(Initiative/PlayerFirst)、打斷非即時(掃到出手格才讀)；修掉環繞雙動 bug，加消費指令、waiting_actor 聚焦訊號。
- 更新 §7：頂部加 callout 標註「單 hero 作廢、改 order 表」，修訂決策定案區，真相層指向 turn-loop-example.cpp；推進與渲染解耦——core_loop 由獨立計時器(如每1秒)驅動、不綁渲染幀，example 的 frontend 拆成 render_frame/on_input/on_advance_timer 三條獨立時鐘。
- brainstorming 定案 Action 型別+時間模型：寫出 specs/2026-06-07-action-and-turn-scheduler-design.md。決策：Action=enum+param+weight、效果走可替換 ActionEffects(on_channel+on_resolve 兩條都要)、時間用 ToME4 行動值 energy(參考 analysis/t-engine)、三排程器都做(A 能量瞬發/B 能量+channel/C 純 tick remaining)可切換 mode 比較。現有 move() 邏輯搬進 on_resolve 不重寫。
- 實作純 core 排程器(計畫 plans/2026-06-07-action-and-turn-scheduler.md)：src/core/turn/{action,action_effects,turn_world,turn_scheduler,energy_instant,energy_channel,tick_remaining,make_scheduler} + components/{player_controlled,energy,ongoing_action}。pending 用 scheduler 內部 map(非 ECS component)、C 用每回合整步(非 min-jump)、advance=推進到下一批就緒或卡玩家。tests/src/test_turn_scheduler.cpp 涵蓋 §8 五情境(速度差/channel/打斷/玩家阻塞/多角色)。ctest 全綠：30 cases/114 assertions。未 commit。
- 真實效果 + ZoneWorld 接線：core/turn/zone_effects(MoveEffects 搬入移動/撞牆/攻擊擊殺/拾取，發 ZoneEvent；WaitEffects)、move_dir(方向編碼)、turn_world 加 map/events、三排程器加 reg.valid 防殺後越界。test_zone_effects 4 案(移動/撞牆/攻擊擊殺/拾取)綠。ZoneWorld 加 scheduler 路徑(additive，不動既有 move()/verify)：set_scheduler_mode/submit_hero_move/submit_hero_wait/step_scheduler/hero_is_waiting + drain_events→signal；hero 掛 PlayerControlled+Energy、NPC 掛 Energy。ctest 34案/127斷言全綠；zone_gd(GDExtension) 編譯通過(需 -DZONE_BUILD_GDEXTENSION=ON)。
- GDScript 前端接線完成：map_view.gd 走 scheduler 路徑(submit_hero_move/wait → _advance_until_wait 同步消化到英雄再次等指令)，TAB 鍵循環 A/B/C 並顯示於 UI；turn_count 改由 submit 計(每玩家指令一回合)、drain_events 只 emit world_changed。verify.gd 加三模式驗證(set_mode+submit+step 到 hero_is_waiting)。godot-mono 4.6.3 headless **VERIFY PASSED**(三模式皆綠)；ctest 仍 34/127。.so 已更新到 godot_zone/bin/。
- Timer 視覺化 + 即時打斷 + Cast：新增 CastEffects(weight>1 channel，結算對8鄰格 nova 傷害)；ZoneWorld submit_hero_cast+註冊 Cast。map_view.gd 改 Timer 驅動(_tick_sec 預設0.2，[ ]調速)，輸入只 submit+標記 _pending_input、_on_advance_tick 每步推進(英雄idle無指令則不推→世界阻塞)；C鍵詠唱(3回合)、詠唱中按移動=即時打斷。test_zone_effects 加 Cast nova+打斷(2 subcase)。ctest 35案/130斷言全綠；headless VERIFY PASSED(3模式+cast)；主場景 headless 跑通無 script error。.so 已更新。
- DoT 持續效果系統：timed_effect.h(TimedEffectsComponent: Burning/Poison/Regen)、zone_effects 加 apply_timed_effect/tick_timed_effects(回合開始扣血/過期/致死發 ActorDied)。TurnWorld 加 on_actor_turn hook，三排程器在 actor 取得回合時呼叫(+valid 重檢防 DoT 自殺越界)；B 的 step_actor 重構成先阻塞檢查再 hook。CastEffects nova 對生還者殘留 Burning(3回合)。ZoneWorld make_turn_world 設 hook=tick_timed_effects。test 加 DoT 3 案(逐回合/致死/排程器tick)。ctest 38案/138斷言全綠；headless VERIFY PASSED(3模式+cast)。.so 已更新。
- JSON 資料化(Q1 終點)：action_def.h/.cpp(ActionDef 可組合原語: do_move/nova_damage/dot/self_heal + ActionLibrary 用 cereal JSONInputArchive 載 data/actions.json，失敗 load_defaults 後備)。zone_effects 抽出 resolve_move/resolve_nova 原語供寫死 effect 與 LibraryEffects 共用；新增 ActionKind::Skill(count→6)、Action 加 def 欄位。ZoneWorld 載庫+註冊 Skill、submit_hero_skill(name)；map_view C=fireball/H=heal(JSON 技能)。data/actions.json 含 fireball/heal/smite。test 加 4 案(JSON載入/後備/library nova+燃燒/library heal)。ctest 42案/150斷言全綠；headless VERIFY PASSED(3模式+cast+skill)。.so 已更新。
- 詳細診斷 UI(使用者要測不同系統機制，資訊要詳細)：ZoneWorld get_debug_text() 逐 actor dump(排程器模式/世界時鐘ticks/回合/樓層/waiting + 每 actor: id/座標/HP/能量value+speed/進行中動作channel進度+remaining/全部持續效果)，get_hero_status/effects/get_world_clock；累計 world_clock_。CJK 字串必須用 String::utf8()(String(const char*)是Latin-1會亂碼)。heal 改為瞬補+Regen buff(可見)。map_view info_label 改顯示 get_debug_text。修 verify.gd 真 bug：submit 後 hero 仍 waiting，舊 while-not-waiting 迴圈直接跳過→指令從沒執行(假通過)；改 step-first _advance()。ctest 42/151、headless VERIFY PASSED(三模式 hero 真的移動了)。
- NPC 智能升級：core/turn/npc_brain.h/.cpp decide_chase(朝英雄移動，相鄰即撞擊攻擊；caster 相鄰放 npc_flame nova 技能)，放 core 故可 ctest。NpcAiComponent 加 is_caster；spawn 時半數設 caster。data/actions.json + load_defaults 加 smite/npc_flame。ZoneWorld npc_decide 改呼叫 decide_chase。test_npc_brain 4 案。ctest 46/159；headless VERIFY PASSED(NPC 追擊 demo: 英雄原地等待 40 回合被圍殺 hp 20→0，證實追擊+施法者運作)。
- debug trace 管線：TurnWorld.trace sink，效果/DoT/nova/技能在發生當下吐字串；ZoneWorld trace_enabled_(預設開)+trace_log_(ring300)+on_trace(即時 UtilityFunctions::print + 緩衝)+get_debug_log/set_trace_enabled/clear。map_view L 開關/K 清/螢幕顯示最近24行。eid 遮掉 version 高位(&0xFFFFF)。**修真 bug**：resolve_move/nova/DoT 致死會 destroy 任何 actor 含英雄→restart 雙重 destroy 崩潰；新增 die() 保護 PlayerControlled 不消滅(只 game over)，restart 加 valid 防護+重建 scheduler。
- 機制擴充(供測試)：ActionDef 加 radius(nova chebyshev 半徑)+dot_kind(0燃燒/1毒/2回)；resolve_nova 吃這兩參數。新技能 meteor(r2,weight4)/venom(中毒5回)；map_view M/V 鍵。NPC 速度差(caster 80/近戰 130)讓能量排程器面板看得到行動值差。ctest 49/168、headless VERIFY PASSED。
- **執行**：主場景 res://map_view.tscn（godot-mono --path godot_zone）。鍵：WASD移動/.等待/C火球H治療M隕石V毒/TAB切A·B·C排程器/[ ]調速/L開關trace/K清log。.so 在 godot_zone/bin/。未 commit。

---
## 進度快照（2026-06-03 睡前）

**當前理解（一句話）**：gamecore-zone 重構已完成可跑，現在在設計「回合迴圈/玩家控制」這層，已收斂出乾淨的對稱模型，尚未動手實作。

**回合迴圈設計定案（五條）**：
1. 對稱模型：玩家/NPC 共用 tick_actor，唯一差別在 provide_next_action()（玩家回 nullopt→idle 等輸入；NPC 回 AI 決策）
2. 介面 step() / step(cmd)：繼續 vs 換行動；dt 由 C++ 算（Godot 不傳 dt）
3. 玩家恆先手：先 tick hero，再迭代 view<ActorComponent>(exclude<HeroComponent>)
4. display_chunk_ 動態可調（Godot 設）；C++ 擁規則 dt = min(行動剩餘, display_chunk_)
5. 阻塞 = snapshot.hero.idle，C++ 永不 spin；「打斷」= 覆寫 OngoingActionComponent（無佇列）；「繼續」不是 Action，是 step() 不帶 cmd

**已完成**：設計文件 §7 重寫完成（含決策定案區）；草稿 code 寫好並經使用者逐點確認對齊：`docs/superpowers/specs/2026-06-03-turn-loop-sketch.cpp`。

**剩餘待辦（下次接續）**：
- Action 型別設計（enum+param vs variant；逐 tick 效果 apply_channel vs 結算效果 resolve）← 下一塊硬骨頭
- PassTime 型別定案（浮點秒/整數毫秒/分數回合）
- Snapshot 內容（精簡 view struct vs ECS dump）
- 跨層時間轉換、NPC 累積時間上限（暫緩）

**核心上下文**：設計真相層在 `docs/superpowers/specs/2026-06-03-gamecore-zone-design.md` §7 + 同目錄 turn-loop-sketch.cpp。草稿與設計皆未 commit。
