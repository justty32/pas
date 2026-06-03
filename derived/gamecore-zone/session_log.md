# session_log — gamecore-zone

- 移除死亡 include（event_bus.h、meta_data_component.h、prototype_manager.h），更新 system_ctx.h（移除 EventBus 依賴）、entity_manager.h/cpp（移除 spawn/PrototypeManager）；改寫四份測試檔，25 tests 全綠。
- GDExtension 建置通過（cmake -DZONE_BUILD_GDEXTENSION=ON）並 headless VERIFY PASSED：修三處編譯錯誤（FolderSaveStore→路徑 API、size_hint→size、version() const、string_view.c_str）；verify.gd 修 OpenNefiaCore→ZoneCore；godot-mono 4.6.3 輸出 zone core 0.0.1-alpha、60×40 地圖、save/load round-trip 全綠。
- 設計 §7 回合迴圈：時間驅動 actor poll，定案玩家控制與 Godot↔C++ 介面（純設計，尚未實作）。

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
