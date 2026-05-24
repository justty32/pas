// rl_cpp 單元測試。刻意不引入測試框架（符合工作空間「最少相依」原則），
// 用一個 CHECK 巨集累計失敗數，全部跑完回傳非零代表有測試失敗。
#include <cmath>
#include <cstdio>
#include <vector>

#include "rl/bandit.hpp"
#include "rl/bandit_agents.hpp"
#include "rl/rng.hpp"

static int g_failures = 0;

#define CHECK(cond, msg)                            \
    do {                                            \
        if (cond) {                                 \
            std::printf("  [ ok ] %s\n", msg);      \
        } else {                                    \
            std::printf("  [FAIL] %s\n", msg);      \
            ++g_failures;                           \
        }                                           \
    } while (0)

static void test_rng_reproducible() {
    std::printf("test_rng_reproducible\n");
    rl::Rng a(123), b(123);
    bool same = true;
    for (int i = 0; i < 100; ++i) {
        if (a.normal() != b.normal()) same = false;
    }
    CHECK(same, "same seed -> identical sequence");

    rl::Rng c(123), d(999);
    bool differs = false;
    for (int i = 0; i < 100; ++i) {
        if (c.normal() != d.normal()) differs = true;
    }
    CHECK(differs, "different seed -> different sequence");
}

static void test_bandit_optimal_is_argmax() {
    std::printf("test_bandit_optimal_is_argmax\n");
    rl::Rng rng(7);
    rl::BanditEnv env(10, rng);
    int opt = env.optimal_action();
    bool is_max = true;
    for (int a = 0; a < env.num_actions(); ++a) {
        if (env.true_value(a) > env.true_value(opt)) is_max = false;
    }
    CHECK(is_max, "optimal_action() == argmax of true values");
}

static void test_incremental_average() {
    // ValueAgent::update 的增量平均應等於直接算的樣本平均。
    std::printf("test_incremental_average\n");
    rl::Rng rng(1);
    rl::EpsilonGreedyAgent agent(1, rng, 0.0);  // 單一動作，方便驗證
    const std::vector<double> rewards = {1.0, 2.0, 3.0, 4.0, 10.0};
    double sum = 0.0;
    for (double r : rewards) {
        agent.update(0, r);
        sum += r;
    }
    const double mean = sum / static_cast<double>(rewards.size());
    CHECK(std::abs(agent.q()[0] - mean) < 1e-9, "incremental update == sample mean");
    CHECK(agent.counts()[0] == static_cast<long>(rewards.size()), "count tracked correctly");
}

static void test_epsilon_greedy_learns() {
    // 在固定的 10 臂 bandit 上跑久一點，agent 估計最高的動作
    // 應該收斂到真實最佳動作。固定 seed 保證此「統計性質」可重現。
    std::printf("test_epsilon_greedy_learns\n");
    rl::Rng rng(2024);
    rl::BanditEnv env(10, rng);
    rl::EpsilonGreedyAgent agent(10, rng, 0.1);
    for (int t = 0; t < 5000; ++t) {
        int a = agent.select_action();
        agent.update(a, env.step(a));
    }
    const auto& q = agent.q();
    int est_best = 0;
    for (int a = 1; a < 10; ++a) {
        if (q[a] > q[est_best]) est_best = a;
    }
    CHECK(est_best == env.optimal_action(),
          "estimated-best action == true optimal after 5000 steps");
}

int main() {
    test_rng_reproducible();
    test_bandit_optimal_is_argmax();
    test_incremental_average();
    test_epsilon_greedy_learns();

    std::printf("\n");
    if (g_failures == 0) {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("%d CHECK(S) FAILED\n", g_failures);
    return 1;
}
