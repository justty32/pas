#pragma once

#include "IRandom.hpp"
#include <random>
#include <stack>

namespace OpenNefia::Core::Random {

/**
 * @brief Default implementation of IRandom using std::mt19937.
 * Ported from SysRandom.cs.
 */
class SysRandom : public IRandom {
private:
    std::mt19937 _rng;
    std::stack<std::mt19937> _seedStack;

public:
    SysRandom() : _rng(std::random_device{}()) {}
    SysRandom(int seed) : _rng(seed) {}

    float NextFloat() override {
        std::uniform_real_distribution<float> dist(0.0f, 1.0f);
        return dist(_rng);
    }

    int Next() override {
        std::uniform_int_distribution<int> dist;
        return dist(_rng);
    }

    int Next(int minValue, int maxValue) override {
        if (minValue >= maxValue) return minValue;
        std::uniform_int_distribution<int> dist(minValue, maxValue - 1);
        return dist(_rng);
    }

    int Next(int maxValue) override {
        return Next(0, maxValue);
    }

    double NextDouble() override {
        std::uniform_real_distribution<double> dist(0.0, 1.0);
        return dist(_rng);
    }

    void PushSeed(int seed) override {
        _seedStack.push(_rng);
        _rng.seed(seed);
    }

    void PopSeed() override {
        if (!_seedStack.empty()) {
            _rng = _seedStack.top();
            _seedStack.pop();
        }
    }

    void ClearPushedSeeds() override {
        while (!_seedStack.empty()) _seedStack.pop();
    }
};

} // namespace OpenNefia::Core::Random
