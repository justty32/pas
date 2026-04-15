#include "IoCManager.hpp"
#include "DependencyCollection.hpp"

namespace OpenNefia::Core::IoC {

void IoCManager::InitThread() {
    if (_container != nullptr) {
        return;
    }

    _container = new DependencyCollection();
}

} // namespace OpenNefia::Core::IoC
