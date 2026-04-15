#pragma once

#include <vector>
#include <cstdint>

namespace OpenNefia::Core::Random {

/**
 * @brief Interface for a random number generator.
 * Ported from IRandom.cs.
 */
class IRandom {
public:
    virtual ~IRandom() = default;

    virtual float NextFloat() = 0;
    virtual float NextFloat(float minValue, float maxValue) {
        return NextFloat() * (maxValue - minValue) + minValue;
    }
    virtual float NextFloat(float maxValue) {
        return NextFloat() * maxValue;
    }

    virtual int Next() = 0;
    virtual int Next(int minValue, int maxValue) = 0;
    virtual int Next(int maxValue) = 0;
    
    virtual double NextDouble() = 0;
    
    // virtual void NextBytes(std::vector<uint8_t>& buffer) = 0;

    virtual void PushSeed(int seed) = 0;
    virtual void PopSeed() = 0;
    virtual void ClearPushedSeeds() = 0;
};

} // namespace OpenNefia::Core::Random
