#pragma once
#include <cstdint>
#include <random>

namespace rl {

// 統一的亂數來源：包一層 std::mt19937_64，提供 RL 常用的幾種分布。
//
// 為什麼要集中管理亂數？
//   RL 實驗高度依賴隨機性 —— 探索策略、環境雜訊、權重初始化都用得到。
//   只有把 seed 固定下來，才能在「同樣的隨機條件」下公平比較不同演算法，
//   debug 時也能重現一模一樣的執行序列。每支實驗程式都應該明確指定 seed。
class Rng {
public:
    explicit Rng(std::uint64_t seed = 42) : gen_(seed) {}

    // [0, 1) 均勻分布實數
    double uniform() { return uniform_real_(gen_); }

    // [lo, hi) 均勻整數：含 lo、不含 hi（和容器索引語意一致）
    int uniform_int(int lo, int hi) {
        std::uniform_int_distribution<int> d(lo, hi - 1);
        return d(gen_);
    }

    // 常態分布 N(mean, stddev)
    double normal(double mean = 0.0, double stddev = 1.0) {
        std::normal_distribution<double> d(mean, stddev);
        return d(gen_);
    }

    std::mt19937_64& engine() { return gen_; }

private:
    std::mt19937_64 gen_;
    std::uniform_real_distribution<double> uniform_real_{0.0, 1.0};
};

}  // namespace rl
