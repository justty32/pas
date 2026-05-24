// Milestone 1 示範程式：重現 Sutton & Barto《RL: An Introduction》第 2 章
// 圖 2.2 的經典結果 —— 在 10 臂 bandit 上比較不同探索策略。
//
// 做法：每種策略各跑 RUNS 個獨立的 bandit（每個 bandit 的 q* 重新隨機生成），
// 每個 bandit 跑 STEPS 步，再把結果「跨 run 平均」，消除單一 bandit 的運氣成分。
// 觀察兩個指標隨時間的變化：
//   1. 平均獎勵 (average reward)：學得越好、拿到的獎勵越高。
//   2. 選到最佳手臂的比例 (% optimal action)：直接反映決策品質。
//
// 執行：build 後 ./bandit_demo
#include <cstdint>
#include <cstdio>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "rl/bandit.hpp"
#include "rl/bandit_agents.hpp"
#include "rl/rng.hpp"

namespace {

constexpr int K = 10;        // 手臂數
constexpr int RUNS = 2000;   // 獨立 bandit 數（用來平均掉運氣）
constexpr int STEPS = 1000;  // 每個 bandit 拉的次數

struct Result {
    std::vector<double> avg_reward;   // 每個 time step 的平均獎勵
    std::vector<double> pct_optimal;  // 每個 time step 選到最佳手臂的比例
};

using MakeAgent = std::function<std::unique_ptr<rl::ValueAgent>(int, rl::Rng&)>;

Result run_experiment(const MakeAgent& make_agent, std::uint64_t base_seed) {
    Result res;
    res.avg_reward.assign(STEPS, 0.0);
    res.pct_optimal.assign(STEPS, 0.0);

    for (int run = 0; run < RUNS; ++run) {
        rl::Rng rng(base_seed + static_cast<std::uint64_t>(run));
        rl::BanditEnv env(K, rng);
        auto agent = make_agent(K, rng);
        const int best = env.optimal_action();

        for (int t = 0; t < STEPS; ++t) {
            const int a = agent->select_action();
            const double r = env.step(a);
            agent->update(a, r);
            res.avg_reward[t] += r;
            res.pct_optimal[t] += (a == best) ? 1.0 : 0.0;
        }
    }
    for (int t = 0; t < STEPS; ++t) {
        res.avg_reward[t] /= RUNS;
        res.pct_optimal[t] /= RUNS;
    }
    return res;
}

void print_table(const char* metric,
                 const std::vector<std::string>& names,
                 const std::vector<std::vector<double>>& cols,
                 bool as_percent) {
    const int checkpoints[] = {0, 9, 49, 99, 249, 499, 999};  // 0-based step index
    std::printf("\n=== %s ===\n", metric);
    std::printf("%-8s", "step");
    for (const auto& n : names) std::printf("%14s", n.c_str());
    std::printf("\n");
    for (int cp : checkpoints) {
        std::printf("%-8d", cp + 1);
        for (const auto& col : cols) {
            if (as_percent) {
                std::printf("%13.1f%%", col[cp] * 100.0);
            } else {
                std::printf("%14.3f", col[cp]);
            }
        }
        std::printf("\n");
    }
}

}  // namespace

int main() {
    std::printf("10-armed bandit testbed: %d runs x %d steps\n", RUNS, STEPS);
    std::printf("(每個數字都是跨 %d 個隨機 bandit 的平均)\n", RUNS);

    struct Strategy {
        std::string name;
        MakeAgent make;
    };
    std::vector<Strategy> strategies = {
        {"greedy(e=0)",
         [](int k, rl::Rng& r) { return std::make_unique<rl::EpsilonGreedyAgent>(k, r, 0.0); }},
        {"e-greedy.01",
         [](int k, rl::Rng& r) { return std::make_unique<rl::EpsilonGreedyAgent>(k, r, 0.01); }},
        {"e-greedy.1",
         [](int k, rl::Rng& r) { return std::make_unique<rl::EpsilonGreedyAgent>(k, r, 0.1); }},
        {"UCB(c=2)",
         [](int k, rl::Rng& r) { return std::make_unique<rl::UCBAgent>(k, r, 2.0); }},
    };

    std::vector<std::string> names;
    std::vector<std::vector<double>> reward_cols;
    std::vector<std::vector<double>> optimal_cols;
    // 用同一組 base_seed 讓各策略面對「相同的那批 bandit」，比較才公平。
    const std::uint64_t base_seed = 1000;
    for (const auto& s : strategies) {
        Result res = run_experiment(s.make, base_seed);
        names.push_back(s.name);
        reward_cols.push_back(res.avg_reward);
        optimal_cols.push_back(res.pct_optimal);
    }

    print_table("average reward", names, reward_cols, /*as_percent=*/false);
    print_table("% optimal action", names, optimal_cols, /*as_percent=*/true);

    std::printf(
        "\n解讀：純貪婪 (e=0) 早期衝得快但很快卡住（從不探索）；\n"
        "      e=0.1 探索多、學得快但長期會被 10%% 的亂選拖住上限；\n"
        "      e=0.01 起步慢但長期最穩；UCB 通常最快逼近最佳。\n");
    return 0;
}
