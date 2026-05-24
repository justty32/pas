# rl_cpp 學習路線圖 (Roadmap)

> 目標：**用純 C++ 標準庫、從零手刻**強化學習，循序漸進把整條路走完。
> 純 CPU、零第三方相依（連神經網路與自動微分都自己寫）。重點是**理解**，不是效能。

## 設計原則

- **每個 milestone 都能獨立跑、能看到結果**：每完成一個階段就有一支 `demos/*_demo.cpp`，
  跑出能對照課本/直覺的數字或曲線。看不到學習發生 = 還沒完成。
- **概念先於程式碼**：每階段先想清楚「要學的核心概念是什麼」，再決定資料結構。
- **不要過早抽象**（KISS）：bandit 不需要完整 MDP 介面。等到 M2 真的需要狀態轉移，
  再引入 `Env` 介面。介面是被需求逼出來的，不是預先設計的。
- **共用基礎設施逐步沉澱**：`rl/rng.hpp`（亂數）已抽出；之後可能再抽出 `Env` 介面、
  神經網路層、replay buffer 等，但都等到第二個使用者出現才抽。

---

## Milestones

### ✅ M1 — Multi-armed Bandit（多臂吃角子老虎機）
**對應**：Sutton & Barto 第 2 章
**核心概念**：探索 vs 利用 (explore/exploit)、動作價值估計 Q(a)、增量式樣本平均、
ε-greedy、UCB、用「平均獎勵 / %最佳動作」評估策略。
**為什麼從這裡開始**：bandit 是「只有一個狀態」的退化 MDP，沒有狀態轉移、沒有
delayed reward，可以單獨把「從雜訊中估計價值 + 平衡探索」這件事學透。

- [x] `BanditEnv`（`include/rl/bandit.hpp`, `src/bandit.cpp`）
- [x] `ValueAgent` 基底 + `EpsilonGreedyAgent` + `UCBAgent`（`include/rl/bandit_agents.hpp`）
- [x] `demos/bandit_demo.cpp` 重現圖 2.2
- [x] 單元測試（`tests/main.cpp`）

**延伸練習（選做）**：樂觀初始值 (optimistic initial values)、非平穩 bandit（用固定步長
α 取代 1/N）、梯度 bandit (gradient bandit / softmax preference)。

---

### ⬜ M2 — Gridworld MDP + 動態規劃 (Dynamic Programming)
**對應**：Sutton & Barto 第 3、4 章
**核心概念**：馬可夫決策過程 (MDP)、狀態/動作/轉移/獎勵、回報 (return) 與折扣 γ、
狀態價值 V(s) 與動作價值 Q(s,a)、**Bellman 方程式**、策略評估 (policy evaluation)、
策略改進 (policy improvement)、value iteration / policy iteration。
**為什麼是這裡**：DP 假設「環境模型已知」，可以在沒有學習雜訊的情況下，先把
Bellman 更新與 V/Q/π 的關係算清楚。這是後面所有 model-free 方法的地基。

- [ ] 抽出通用 `Env` 介面（`reset()`、`step(action) -> {next_state, reward, done}`）
- [ ] `GridWorld`：格子地圖、牆、終點、可選的風/陷阱
- [ ] `policy_iteration` / `value_iteration` 解出最佳策略
- [ ] demo：印出收斂後的 V(s) 熱圖與最佳動作箭頭（ASCII）

---

### ⬜ M3 — 表格式無模型學習 (Tabular Model-Free: MC & TD)
**對應**：Sutton & Barto 第 5、6 章
**核心概念**：蒙地卡羅 (Monte Carlo) 控制、時間差分 (Temporal Difference)、
**Q-learning**（off-policy）、**SARSA**（on-policy）、TD 目標 `R + γ max Q(s',a')`、
on-policy vs off-policy 的差異（用 Cliff Walking 看 Q-learning 走險路、SARSA 走安全路）。
**為什麼是這裡**：拔掉「已知模型」的假設，agent 只能靠互動學。這是 RL 真正的起點。

- [ ] `QLearningAgent` / `SarsaAgent`（表格 Q(s,a) = `std::vector` 或 `unordered_map`）
- [ ] Cliff Walking 環境（經典對照 Q-learning vs SARSA）
- [ ] demo：學習曲線 + 收斂後的路徑視覺化

---

### ⬜ M4 — 函數近似 (Function Approximation, 線性)
**對應**：Sutton & Barto 第 9、10 章
**核心概念**：狀態太多/連續時表格爆炸 → 用特徵向量 + 線性權重逼近 Q。
tile coding / 特徵工程、semi-gradient 更新、Mountain Car 之類的連續狀態問題。
**為什麼是這裡**：這是「表格 → 神經網路」之間的橋。先用線性模型把
「梯度更新逼近價值函數」搞懂，再換成 NN 時就只是把線性模型換掉而已。

- [ ] tile coding 特徵
- [ ] 線性 semi-gradient SARSA / Q-learning
- [ ] Mountain Car 環境（自己寫物理）
- [ ] demo：學習曲線

---

### ⬜ M5 — 手刻神經網路與自動微分 (Mini Autodiff + MLP)
**對應**：不在 Sutton & Barto，是 deep RL 的前置工程
**核心概念**：反向傳播 (backpropagation)、計算圖、為什麼需要 autodiff、
全連接層 (Dense)、激活函數 (ReLU/tanh)、損失函數、SGD/Adam。
**為什麼是這裡**：deep RL 的「deep」就靠這層。**先在 RL 之外**把 NN 訓練好
（例如擬合函數、MNIST 子集或 XOR），確認前向/反向/optimizer 都對，
再拿去當 DQN 的 Q 網路 —— 否則 deRL debug 時分不清是 RL 錯還是 NN 錯。

- [ ] mini autodiff（純 std；先做 scalar 反向傳播理解原理，再決定要不要上 tensor）
- [ ] `Dense` 層 + ReLU/tanh + MSE/交叉熵 + SGD/Adam
- [ ] 獨立 sanity check：擬合 y=sin(x) 或 XOR，確認會收斂

---

### ⬜ M6 — DQN (Deep Q-Network)
**對應**：Mnih et al. 2015（DQN 論文）
**核心概念**：用 M5 的 NN 取代表格 Q、**經驗回放 (experience replay)**、
**目標網路 (target network)**、ε 衰減、為什麼這兩個技巧能穩定訓練。
**為什麼是這裡**：把 M3（Q-learning）+ M5（NN）合體。CartPole 是 deep RL 的「hello world」。

- [ ] CartPole 環境（自己寫物理：連續狀態、離散動作）
- [ ] replay buffer
- [ ] DQN agent（policy net + target net + ε 衰減）
- [ ] demo：每 episode 的存活步數曲線（應從 ~20 爬到 ~200+）

---

### ⬜ M7 — 策略梯度 (Policy Gradient: REINFORCE → Actor-Critic)
**對應**：Sutton & Barto 第 13 章
**核心概念**：直接參數化策略 π(a|s)、policy gradient 定理、REINFORCE、
baseline 降變異、Actor-Critic（A2C）、value-based 與 policy-based 的根本差異。
**為什麼是壓軸**：補上 RL 的另一大家族。學完這個，主流演算法的兩條主幹都摸過了。

- [ ] REINFORCE（蒙地卡羅策略梯度）
- [ ] 加 baseline（用一個 value net）
- [ ] Actor-Critic
- [ ] demo：在 CartPole 上對照 DQN 與 policy gradient

---

## 之後可以再走的方向（超出基礎，先列著）
PPO、連續動作（DDPG/SAC）、多執行緒平行收集經驗、把某個 env 換成真正的遊戲。
