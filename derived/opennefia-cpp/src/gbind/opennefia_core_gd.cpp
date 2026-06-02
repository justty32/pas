#include "opennefia_core_gd.h"
#include "core/version.h"

using namespace godot;

void opennefia_gd::OpenNefiaCore::_bind_methods() {
    ClassDB::bind_method(D_METHOD("version"), &OpenNefiaCore::version);
}

String opennefia_gd::OpenNefiaCore::version() const {
    auto sv = opennefia::version();
    return String(std::string(sv).c_str());
}
