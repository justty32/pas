// Rim Glow Effect Shader
// 用途：選取高亮、特殊單位邊緣發光
//
// 使用方式（GDScript）：
//   var shader := preload("res://scenes/shaders/rim_glow.gdshader")
//   unit.material_override = MaterialLibrary.make_rim(shader, Color(0.2, 0.5, 0.9))
//
// rim_power  ：越小 rim 越寬（建議 1.5~4.0）
// rim_strength：rim 覆蓋強度 0~1（0 = 純 albedo，1 = 純 rim_color）

shader_type spatial;
render_mode unshaded, cull_back;

uniform vec4  albedo       : source_color = vec4(0.2, 0.5, 0.9, 1.0);
uniform vec4  rim_color    : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float rim_power    = 2.0;
uniform float rim_strength = 0.8;

void fragment() {
	float rim = 1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	rim = pow(rim, rim_power) * rim_strength;
	ALBEDO = mix(albedo.rgb, rim_color.rgb, rim);
	ALPHA  = albedo.a;
}
