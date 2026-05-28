shader_type canvas_item;

uniform sampler2D material_tex : hint_default_white;
uniform float material_strength : hint_range(0.0, 1.0) = 1.0;
uniform int blend_mode : hint_range(0, 2) = 0;
uniform vec4 tint : source_color = vec4(1.0);

void fragment() {
	vec4 base = texture(TEXTURE, UV);
	vec4 mat = texture(material_tex, UV) * tint;
	float k = material_strength * mat.a;

	vec3 result;
	if (blend_mode == 0) {
		result = base.rgb * mix(vec3(1.0), mat.rgb, k);
	} else if (blend_mode == 1) {
		result = base.rgb + mat.rgb * k;
	} else {
		result = vec3(1.0) - (vec3(1.0) - base.rgb) * (vec3(1.0) - mat.rgb * k);
	}
	COLOR = vec4(result, base.a) * COLOR;
}
