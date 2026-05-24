# rl_cpp 進度流水帳

> 每次工作後 append 一句話。完整路線與 milestone 待辦見 `ROADMAP.md`。

- 2026-05-23：建立專案骨架（CMake + `include/rl` + `src` + `tests` + `demos`），
  純 C++17 標準庫、零第三方相依、純 CPU。確立學習路線（`ROADMAP.md` M1–M7，循序漸進）。
- 2026-05-23：完成 **M1 Multi-armed Bandit** —— `rl::Rng` 亂數封裝、`BanditEnv`（10 臂、
  q*~N(0,1)、獎勵~N(q*,1)）、`ValueAgent` 基底（增量式樣本平均）+ `EpsilonGreedyAgent` +
  `UCBAgent`。`rl_tests` 全綠；`bandit_demo` 重現 Sutton & Barto 圖 2.2（純貪婪卡 ~34%、
  ε=0.1 達 ~82%、UCB ~84% 最佳動作率）。

---

## 接續點（下次從這開始）

- **目前狀態**：M1 完成、可編譯可跑（見上）。M2–M7 尚未動工，使用者打算自己慢慢做。
- **下一步 = M2 Gridworld MDP + 動態規劃**（`ROADMAP.md` 的 M2 區塊有完整概念與待辦）。
  M2 的第一個動作是抽出通用 `Env` 介面（`reset()` / `step(action) -> {next_state, reward, done}`），
  這是 M1 刻意還沒做的抽象（bandit 只有單一狀態用不到）。
- **重新熟悉專案的最快路徑**：讀 `CLAUDE.md`（工作準則、建置指令）→ `ROADMAP.md`（路線與概念）
  → 跑一次 `./build/rl_tests` 與 `./build/bandit_demo` 確認環境正常。
- **動工提醒**：嚴格按 ROADMAP 順序、不跳關、不過早抽象；新增 `src/*.cpp` 要記得加進
  `CMakeLists.txt` 的 `RL_SOURCES`，新 demo 用 `add_executable`。每推進一步就回來 append 一行。
