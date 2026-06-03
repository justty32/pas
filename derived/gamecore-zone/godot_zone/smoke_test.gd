extends Node

func _ready() -> void:
    var core := OpenNefiaCore.new()
    var v := core.version()
    print("zone core version: ", v)
    assert(v != "", "version() must return a non-empty string")
    print("smoke test PASSED")
