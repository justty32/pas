#include "register_types.h"
#include "map_data.h"
#include "map_generator.h"
#include "terrain_mesh_builder.h"
#include "procgen_mesh_builder.h"

#include <gdextension_interface.h>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

using namespace godot;

void initialize_mapcore_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) return;
    // MapCoreMapData 必須先於 MapCoreGenerator 註冊（前者是後者 signal 的型別）
    GDREGISTER_CLASS(MapCoreMapData);
    GDREGISTER_CLASS(MapCoreGenerator);
    GDREGISTER_CLASS(MapCoreTerrainMeshBuilder);
    GDREGISTER_CLASS(MapCoreProcGenMeshBuilder);
}

void uninitialize_mapcore_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) return;
}

extern "C" {
GDExtensionBool GDE_EXPORT mapcore_godot_init(
    GDExtensionInterfaceGetProcAddress p_get_proc_address,
    const GDExtensionClassLibraryPtr p_library,
    GDExtensionInitialization *r_initialization)
{
    GDExtensionBinding::InitObject init_obj(p_get_proc_address, p_library, r_initialization);
    init_obj.register_initializer(initialize_mapcore_module);
    init_obj.register_terminator(uninitialize_mapcore_module);
    init_obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);
    return init_obj.init();
}
}
