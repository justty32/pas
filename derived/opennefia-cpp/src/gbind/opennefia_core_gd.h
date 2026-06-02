#pragma once
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/string.hpp>

namespace opennefia_gd {

// 薄殼 facade：讓 GDScript 能 new() 並呼叫。
// 目前只做 smoke test（version()），未來逐步橋接核心狀態。
class OpenNefiaCore : public godot::RefCounted {
    GDCLASS(OpenNefiaCore, godot::RefCounted)

protected:
    static void _bind_methods();

public:
    godot::String version() const;
};

} // namespace opennefia_gd
