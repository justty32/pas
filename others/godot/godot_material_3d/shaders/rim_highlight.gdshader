shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert, specular_disabled;

uniform vec4 albedo : source_color = vec4(0.8, 0.8, 0.8, 1.0);
uniform vec4 rim_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float rim_power : hint_range(0.1, 8.0) = 2.0;
uniform float rim_strength : hint_range(0.0, 4.0) = 1.0;

void fragment() {
	ALBEDO = albedo.rgb;

	float rim = 1.0 - dot(normalize(NORMAL), normalize(VIEW));
	rim = pow(clamp(rim, 0.0, 1.0), rim_power) * rim_strength;
	EMISSION = rim_color.rgb * rim;
}
