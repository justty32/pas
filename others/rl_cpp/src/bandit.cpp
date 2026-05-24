#include "rl/bandit.hpp"

#include <algorithm>

namespace rl {

BanditEnv::BanditEnv(int k, Rng& rng) : k_(k), rng_(rng), q_star_(k) {
    for (int a = 0; a < k_; ++a) {
        q_star_[a] = rng_.normal(0.0, 1.0);
    }
    optimal_ = static_cast<int>(
        std::max_element(q_star_.begin(), q_star_.end()) - q_star_.begin());
}

double BanditEnv::step(int action) {
    // 獎勵 = 真實價值 + 標準常態雜訊。雜訊讓單次觀察不可靠，
    // 逼得 agent 必須多次取樣才能可靠估計 q*(action)。
    return q_star_[action] + rng_.normal(0.0, 1.0);
}

}  // namespace rl
