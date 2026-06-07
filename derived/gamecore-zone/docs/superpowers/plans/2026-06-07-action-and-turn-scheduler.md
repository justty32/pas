# Action 與可切換回合排程器 — 實作計畫

> **For agentic workers:** 依 superpowers:executing-plans 逐任務實作。本計畫聚焦**純 core 可測試交付物**（不接 Godot）：Action 詞彙 + 三排程器 + ctest。ZoneWorld 接線與真實 Move/Attack 效果列為後續。

**Goal:** 把 spec（`specs/2026-06-07-action-and-turn-scheduler-design.md`）的共用詞彙與 A/B/C 三排程器實作成 godot-free 的 `zone_core` 程式碼，並以 doctest 驗證 §8 行為矩陣。

**Architecture:** 共用 `Action`/`ActionEffects`/`TurnWorld`/`TurnScheduler` 介面；三個 scheduler 子類各自實作 `advance()`；`make_scheduler(mode)` 工廠切換。Scheduler 不碰地圖，只呼叫 effect 與 npc_decide，故可離線測。

**Tech Stack:** C++20、EnTT v3.16、doctest、cereal（serialize 慣例）。`zone_core` 自動 glob `src/**`，測試自動 glob `tests/src/*.cpp`，無需改 CMake。

**與 spec 的刻意偏差（記錄）：**
1. 指令收件匣用 scheduler 內部 `unordered_map<entity,Action>`（非 `PendingCommandComponent`）——自足、易測；ECS 版之後接 ZoneWorld 時再評估。
2. C（TickRemaining）用**每回合整步**推進（非 min-remaining 跳躍）——決定性、與 B 的 channel 對齊；速度差仍由 weight 表達（短動作更頻繁取新指令）。
3. A/B 的 `advance()` = 「tick 能量直到至少一個 actor 就緒，處理該批就緒者，或卡玩家」——避免逐一處理造成能量分配失真，speed ratio 乾淨。

---

## File Structure

- `src/core/turn/action.h` — `ActionKind` enum、`Action{kind,param,weight}`
- `src/core/turn/action_effects.h` — `ActionEffects` 介面、`EffectRegistry`
- `src/core/turn/turn_world.h` — `TurnConfig`、`NpcDecider`、`TurnWorld`
- `src/core/turn/turn_scheduler.h` — `TurnScheduler` 介面、`SchedulerMode`、`make_scheduler` 宣告、`SchedulerBase`
- `src/core/components/{player_controlled,energy,ongoing_action}_component.h` — 共用 components
- `src/core/turn/energy_instant_scheduler.{h,cpp}` — A
- `src/core/turn/energy_channel_scheduler.{h,cpp}` — B
- `src/core/turn/tick_remaining_scheduler.{h,cpp}` — C
- `src/core/turn/make_scheduler.cpp` — 工廠
- `tests/src/test_turn_scheduler.cpp` — §8 行為矩陣

## Tasks（高層；逐檔實作後一次 build+ctest）

1. 共用型別：action.h / action_effects.h / turn_world.h / 三個 component。
2. scheduler 介面 + SchedulerBase（pending map + waiting_actor + 玩家判定 helper）。
3. A EnergyInstant。
4. B EnergyChannel（channel + 打斷）。
5. C TickRemaining（每回合整步）。
6. make_scheduler 工廠。
7. test_turn_scheduler.cpp：速度差(A,B)、channel 完成(B,C)、打斷(B,C)、玩家阻塞(A,B,C)、多角色(A,B,C)。
8. cmake build + ctest，綠燈。

## 驗收

`ctest` 全綠，涵蓋 §8 五類情境 × 對應排程器。
