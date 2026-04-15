#pragma once

#include <vector>
#include <string>

namespace OpenNefia::Core::UI {

struct UiKeyHint {
    std::string Text;
    // ... other fields can be added from UiKeyHint.cs
};

class IUiInput {
public:
    virtual ~IUiInput() = default;

    virtual std::vector<UiKeyHint> MakeKeyHints() = 0;
};

} // namespace OpenNefia::Core::UI
