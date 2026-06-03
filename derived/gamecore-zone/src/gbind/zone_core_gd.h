#pragma once
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/core/class_db.hpp>

namespace zone_gd {

class ZoneCore : public godot::RefCounted {
    GDCLASS(ZoneCore, godot::RefCounted)
protected:
    static void _bind_methods();
public:
    godot::String version() const;
};

} // namespace zone_gd
