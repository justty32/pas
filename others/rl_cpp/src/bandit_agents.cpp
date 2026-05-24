#include "rl/bandit_agents.hpp"

#include <cmath>
#include <limits>

namespace rl {

ValueAgent::ValueAgent(int num_actions, Rng& rng)
    : num_actions_(num_actions), rng_(rng), q_(num_actions, 0.0), n_(num_actions, 0) {}

void ValueAgent::update(int action, double reward) {
    n_[action] += 1;
    // 增量式樣本平均：Q <- Q + (R - Q) / N
    q_[action] += (reward - q_[action]) / static_cast<double>(n_[action]);
    total_steps_ += 1;
}

int ValueAgent::argmax() const {
    double best = -std::numeric_limits<double>::infinity();
    int best_count = 0;  // 目前並列最高的動作數量（用於蓄水池式隨機 tie-break）
    int chosen = 0;
    for (int a = 0; a < num_actions_; ++a) {
        if (q_[a] > best) {
            best = q_[a];
            best_count = 1;
            chosen = a;
        } else if (q_[a] == best) {
            // 在所有並列最高者中以 1/best_count 的機率取代，達成均勻隨機 tie-break。
            ++best_count;
            if (rng_.uniform_int(0, best_count) == 0) {
                chosen = a;
            }
        }
    }
    return chosen;
}

EpsilonGreedyAgent::EpsilonGreedyAgent(int num_actions, Rng& rng, double epsilon)
    : ValueAgent(num_actions, rng), epsilon_(epsilon) {}

int EpsilonGreedyAgent::select_action() {
    if (rng_.uniform() < epsilon_) {
        return rng_.uniform_int(0, num_actions_);  // 探索：隨機挑一個
    }
    return argmax();  // 利用：選目前估計最高的
}

UCBAgent::UCBAgent(int num_actions, Rng& rng, double c)
    : ValueAgent(num_actions, rng), c_(c) {}

int UCBAgent::select_action() {
    // 還沒被選過的動作優先試（N(a)=0 視為信心上界無限大）。
    for (int a = 0; a < num_actions_; ++a) {
        if (n_[a] == 0) return a;
    }
    double best = -std::numeric_limits<double>::infinity();
    int best_a = 0;
    const double t = static_cast<double>(total_steps_ + 1);
    for (int a = 0; a < num_actions_; ++a) {
        const double bonus = c_ * std::sqrt(std::log(t) / static_cast<double>(n_[a]));
        const double ucb = q_[a] + bonus;
        if (ucb > best) {
            best = ucb;
            best_a = a;
        }
    }
    return best_a;
}

}  // namespace rl
