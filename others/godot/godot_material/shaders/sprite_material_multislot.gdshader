shader_type canvas_item;

uniform sampler2D mask_tex : hint_default_black;
uniform sampler2D slot_r_tex : hint_default_white;
uniform sampler2D slot_g_tex : hint_default_white;
uniform sampler2D slot_b_tex : hint_default_white;
uniform vec4 slot_r_tint : source_color = vec4(1.0);
uniform vec4 slot_g_tint : source_color = vec4(1.0);
uniform vec4 slot_b_tint : source_color = vec4(1.0);
uniform float slot_r_strength : hint_range(0.0, 1.0) = 1.0;
uniform float slot_g_strength : hint_range(0.0, 1.0) = 1.0;
uniform float slot_b_strength : hint_range(0.0, 1.0) = 1.0;

void fragment() {
	vec4 base = texture(TEXTURE, UV);
	vec4 mask = texture(mask_tex, UV);
	vec3 col = base.rgb;

	vec3 mr = texture(slot_r_tex, UV).rgb * slot_r_tint.rgb;
	vec3 mg = texture(slot_g_tex, UV).rgb * slot_g_tint.rgb;
	vec3 mb = texture(slot_b_tex, UV).rgb * slot_b_tint.rgb;

	col = mix(col, col * mr, mask.r * slot_r_strength);
	col = mix(col, col * mg, mask.g * slot_g_strength);
	col = mix(col, col * mb, mask.b * slot_b_strength);

	COLOR = vec4(col, base.a) * COLOR;
}
