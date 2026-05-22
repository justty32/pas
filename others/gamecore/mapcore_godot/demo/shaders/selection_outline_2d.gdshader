// 2D 選取描邊 Shader（canvas_item）
// 原理：對每個透明像素採樣 8 個鄰近像素；
//       若鄰近有不透明像素則填入描邊色，否則保持透明。
//       不透明像素直接 pass-through（正常渲染原始 sprite）。
// 使用：設為 Sprite2D / AnimatedSprite2D 的 material 屬性。

shader_type canvas_item;

uniform vec4  outline_color : source_color = vec4(1.0, 0.85, 0.0, 1.0);
// 描邊寬度（像素），1.5 = 懸停細線，3.0 = 選取粗線
uniform float outline_width : hint_range(0.0, 8.0) = 2.0;

void fragment() {
	vec4 col = texture(TEXTURE, UV);

	// 不透明像素：pass-through（保留原始 sprite 顏色）
	if (col.a > 0.01) {
		COLOR = col;
		return;
	}

	// 透明像素：採樣 8 個鄰近像素，判斷是否在描邊區域內
	vec2 px = TEXTURE_PIXEL_SIZE * outline_width;
	float na = 0.0;  // neighbor alpha max
	na = max(na, texture(TEXTURE, UV + vec2( px.x,  0.0 )).a);
	na = max(na, texture(TEXTURE, UV + vec2(-px.x,  0.0 )).a);
	na = max(na, texture(TEXTURE, UV + vec2( 0.0,   px.y)).a);
	na = max(na, texture(TEXTURE, UV + vec2( 0.0,  -px.y)).a);
	na = max(na, texture(TEXTURE, UV + vec2( px.x,  px.y)).a);
	na = max(na, texture(TEXTURE, UV + vec2(-px.x,  px.y)).a);
	na = max(na, texture(TEXTURE, UV + vec2( px.x, -px.y)).a);
	na = max(na, texture(TEXTURE, UV + vec2(-px.x, -px.y)).a);

	// 若鄰近有不透明像素，輸出描邊色
	COLOR = (na > 0.5)
		? vec4(outline_color.rgb, outline_color.a)
		: vec4(0.0);
}
