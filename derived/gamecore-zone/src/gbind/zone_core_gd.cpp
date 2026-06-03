#include "zone_core_gd.h"
#include <core/version.h>

void zone_gd::ZoneCore::_bind_methods() {
    godot::ClassDB::bind_method(
        godot::D_METHOD("version"), &ZoneCore::version);
}

godot::String zone_gd::ZoneCore::version() {
    return godot::String(zone::version().c_str());
}
