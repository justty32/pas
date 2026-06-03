#include "zone_core_gd.h"
#include <core/version.h>
#include <string>

void zone_gd::ZoneCore::_bind_methods() {
    godot::ClassDB::bind_method(
        godot::D_METHOD("version"), &ZoneCore::version);
}

godot::String zone_gd::ZoneCore::version() const {
    auto sv = zone::version();
    return godot::String(std::string(sv).c_str());
}
