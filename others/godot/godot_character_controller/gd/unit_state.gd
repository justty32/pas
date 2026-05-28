class_name UnitState extends RefCounted

# 集中定義 controller 的狀態 enum 與 helper。
# 2D / 3D 兩版 controller 共用此 enum，視覺層也訂閱同樣的狀態值。

enum State { IDLE, MOVING, ATTACKING, HURT, DEAD }


static func name_of(state: int) -> String:
	match state:
		State.IDLE: return "idle"
		State.MOVING: return "moving"
		State.ATTACKING: return "attacking"
		State.HURT: return "hurt"
		State.DEAD: return "dead"
		_: return "unknown"


# 視覺層用：把 controller state 映射到 AnimationTree 狀態名。
# 預設映射假設 AnimationTree 使用 lower_snake_case 命名；
# 專案命名不同時自訂這個 dictionary 即可。
const DEFAULT_ANIM_MAP := {
	State.IDLE:      "idle",
	State.MOVING:    "walk",
	State.ATTACKING: "attack",
	State.HURT:      "hurt",
	State.DEAD:      "dead",
}


static func anim_state(state: int, map: Dictionary = DEFAULT_ANIM_MAP) -> StringName:
	return StringName(map.get(state, "idle"))
