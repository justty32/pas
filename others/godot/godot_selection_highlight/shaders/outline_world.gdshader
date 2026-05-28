// 世界空間 outline：寬度跟隨鏡頭距離縮放（拉遠時視覺變細）。
// 用 material_overlay 套用，不需要 mesh 有第二個 surface。

shader_type spatial;
render_mode cull_front, unshaded, depth_draw_always;

uniform vec4 outline_color : source_color = vec4(1.0, 0.85, 0.0, 1.0);
uniform float outline_width : hint_range(0.0, 0.2) = 0.025;

void vertex() {
	VERTEX += NORMAL * outline_width;
}

void fragment() {
	ALBEDO = outline_color.rgb;
}
