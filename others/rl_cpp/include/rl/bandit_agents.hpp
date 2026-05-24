#pragma once
#include <vector>

#include "rl/rng.hpp"

namespace rl {

// 動作價值法 (action-value methods) 的共同基底。
//
// 概念：對每個動作維護一個估計值 Q(a)，代表「目前認為拉這支手臂能拿到的
// 平均獎勵」，以及它被選過的次數 N(a)。收到新獎勵後用「增量式樣本平均」更新：
//
//     N(a) <- N(a) + 1
//     Q(a) <- Q(a) + (R - Q(a)) / N(a)
//
// 這條更新式等價於「到目前為止所有獎勵的平均」，但不需要保存歷史獎勵，
// 是 RL 裡反覆出現的 "Q <- Q + step * (target - Q)" 通式的最初形態。
//
// 子類別只差在「怎麼用 Q 選動作」(select_action)，亦即探索策略不同。
class ValueAgent {
public:
    ValueAgent(int num_actions, Rng& rng);
    virtual ~ValueAgent() = default;

    // 依各自的探索策略選一個動作。
    virtual int select_action() = 0;

    // 收到 action 的獎勵 reward 後更新估計值（增量式樣本平均）。
    void update(int action, double reward);

    const std::vector<double>& q() const { return q_; }
    const std::vector<long>& counts() const { return n_; }

protected:
    int num_actions_;
    Rng& rng_;
    std::vector<double> q_;  // 估計的動作價值 Q(a)
    std::vector<long> n_;    // 各動作被選次數 N(a)
    long total_steps_ = 0;

    // 帶隨機 tie-break 的 argmax：避免平手時永遠偏好低編號動作。
    int argmax() const;
};

// ε-greedy：以機率 ε 隨機探索任一動作，否則「貪婪地」選目前估計最高的動作。
// ε 越大越愛探索；ε=0 就是純貪婪（容易卡在次佳解）。
class EpsilonGreedyAgent : public ValueAgent {
public:
    EpsilonGreedyAgent(int num_actions, Rng& rng, double epsilon);
    int select_action() override;

private:
    double epsilon_;
};

// UCB (Upper Confidence Bound)：選 Q(a) + c * sqrt(ln t / N(a)) 最大的動作。
// 第二項是「不確定性加成」—— 越少被嘗試的動作加成越大，於是 agent 會
// 系統性地去試探沒把握的動作，而非像 ε-greedy 那樣盲目亂選。c 控制探索強度。
class UCBAgent : public ValueAgent {
public:
    UCBAgent(int num_actions, Rng& rng, double c);
    int select_action() override;

private:
    double c_;
};

}  // namespace rl
