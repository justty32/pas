# rl_cpp

從零手刻的強化學習 (Reinforcement Learning) 學習專案。**純 C++17 標準庫、純 CPU、零第三方相依**——
連神經網路與自動微分都自己寫。重點是**理解每個演算法怎麼運作**，不是效能或生產化。

完整學習路線見 [`ROADMAP.md`](ROADMAP.md)。

## 建置與執行

需要 CMake (≥3.17) 與支援 C++17 的編譯器（g++ / clang++）。

```bash
cmake -B build
cmake --build build -j

./build/rl_tests      # 跑單元測試
./build/bandit_demo   # 跑 Milestone 1 示範
```

## 目前進度

| Milestone | 主題 | 狀態 |
|-----------|------|------|
| M1 | Multi-armed Bandit（ε-greedy / UCB） | ✅ 完成 |
| M2 | Gridworld MDP + 動態規劃 | ⬜ 待做 |
| M3 | 表格式 Q-learning / SARSA | ⬜ 待做 |
| M4 | 線性函數近似 | ⬜ 待做 |
| M5 | 手刻神經網路 + 自動微分 | ⬜ 待做 |
| M6 | DQN | ⬜ 待做 |
| M7 | Policy Gradient / Actor-Critic | ⬜ 待做 |

## 目錄結構

```
rl_cpp/
├── CMakeLists.txt
├── ROADMAP.md          # 學習路線圖（進度真相來源）
├── progress.md         # 工作流水帳
├── include/rl/         # 公開標頭
│   ├── rng.hpp         # 統一亂數來源（可重現實驗）
│   ├── bandit.hpp      # M1: k 臂 bandit 環境
│   └── bandit_agents.hpp
├── src/                # 實作
│   ├── bandit.cpp
│   └── bandit_agents.cpp
├── tests/main.cpp      # 單元測試（無框架）
└── demos/              # 每個 milestone 一支示範程式
    └── bandit_demo.cpp # 重現 Sutton & Barto 圖 2.2
```

## 參考教材

主要對照 Sutton & Barto《Reinforcement Learning: An Introduction》(2nd ed.)，
各 milestone 對應章節見 `ROADMAP.md`。
