// 2D Sprite outline：透明像素若鄰近有不透明像素則上描邊色。
// 與 mapcore demo 版差異：多 sample_pattern 開關（4 邊 / 4 角 / 8 點），
// 以及 pulse_strength 脈動色（接 TIME，給「選取中」呼吸感）。

shader_type canvas_item;

uniform vec4 outline_color : source_color = vec4(1.0, 0.85, 0.0, 1.0);
uniform float outline_width : hint_range(0.0, 8.0) = 2.0;
// 0 = 4 邊（窄）、1 = 4 角（粗）、2 = 8 點（圓整，預設）
uniform int sample_pattern : hint_range(0, 2) = 2;
// 脈動：0 = 關，0.3 = 微脈動，1.0 = 全 0~outline_color 範圍
uniform float pulse_strength : hint_range(0.0, 1.0) = 0.0;
uniform float pulse_speed : hint_range(0.1, 10.0) = 3.0;

void fragment() {
	vec4 col = texture(TEXTURE, UV);
	if (col.a > 0.01) {
		COLOR = col * COLOR;
		return;
	}

	vec2 px = TEXTURE_PIXEL_SIZE * outline_width;
	float na = 0.0;

	if (sample_pattern == 0 || sample_pattern == 2) {
		na = max(na, texture(TEXTURE, UV + vec2(px.x, 0.0)).a);
		na = max(na, texture(TEXTURE, UV + vec2(-px.x, 0.0)).a);
		na = max(na, texture(TEXTURE, UV + vec2(0.0, px.y)).a);
		na = max(na, texture(TEXTURE, UV + vec2(0.0, -px.y)).a);
	}
	if (sample_pattern == 1 || sample_pattern == 2) {
		na = max(na, texture(TEXTURE, UV + vec2(px.x, px.y)).a);
		na = max(na, texture(TEXTURE, UV + vec2(-px.x, px.y)).a);
		na = max(na, texture(TEXTURE, UV + vec2(px.x, -px.y)).a);
		na = max(na, texture(TEXTURE, UV + vec2(-px.x, -px.y)).a);
	}

	if (na > 0.5) {
		float k = 1.0;
		if (pulse_strength > 0.0) {
			float pulse = 0.5 + 0.5 * sin(TIME * pulse_speed);
			k = mix(1.0 - pulse_strength, 1.0, pulse);
		}
		COLOR = vec4(outline_color.rgb, outline_color.a) * k * COLOR;
	} else {
		COLOR = vec4(0.0);
	}
}
