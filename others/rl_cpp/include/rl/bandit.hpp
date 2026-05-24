#pragma once
#include <vector>

#include "rl/rng.hpp"

namespace rl {

// k 臂吃角子老虎機 (k-armed bandit)，對應 Sutton & Barto《RL: An Introduction》第 2 章。
//
// 這是最簡單的 RL 問題：只有「一個狀態」，agent 反覆從 k 個動作裡挑一個拉，
// 每個動作 a 背後有一個「真實價值」q*(a)，但 agent 看不到。每次拉動回傳的
// 獎勵取自常態分布 N(q*(a), 1)。agent 的任務是只靠觀察到的獎勵，估計出
// 哪個動作最好 —— 這就帶出 RL 的核心張力：探索 (explore) vs 利用 (exploit)。
class BanditEnv {
public:
    // 建立 k 支手臂；每支的 q*(a) 由 N(0, 1) 隨機生成。
    BanditEnv(int k, Rng& rng);

    // 拉動第 action 支手臂，回傳一次隨機獎勵 = q*(action) + N(0, 1) 雜訊。
    double step(int action);

    int num_actions() const { return k_; }

    // 真實最佳手臂（評估指標用，agent 不該偷看）。
    int optimal_action() const { return optimal_; }

    // 第 action 支手臂的真實價值 q*(action)（評估用）。
    double true_value(int action) const { return q_star_[action]; }

private:
    int k_;
    Rng& rng_;
    std::vector<double> q_star_;  // 各手臂的真實價值
    int optimal_;                 // q_star_ 的 argmax
};

}  // namespace rl
