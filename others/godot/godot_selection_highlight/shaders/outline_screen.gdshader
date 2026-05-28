// 螢幕空間 outline：寬度以畫素為單位，zoom 變化時視覺粗細不變。
// 落實 CONCEPT 待決事項「螢幕空間恆定粗細」。
//
// 原理：把 NORMAL 從 model space 推到 clip space 後做寬度膨脹，
// 除以 w 分量讓近處與遠處的膨脹倍率自動隨投影距離倒數縮放，
// 視覺呈現為恆定的螢幕邊長。

shader_type spatial;
render_mode cull_front, unshaded, depth_draw_always;

uniform vec4 outline_color : source_color = vec4(1.0, 0.85, 0.0, 1.0);
// 像素寬度（以 1080p 高度為基準，其他解析度需依比例調整或自行 multiplier）。
uniform float outline_pixel_width : hint_range(0.0, 12.0) = 3.0;

void vertex() {
	// model → clip space
	vec4 clip_pos = PROJECTION_MATRIX * MODELVIEW_MATRIX * vec4(VERTEX, 1.0);
	// 法線推到 view space 後投影到 clip space 的方向
	vec3 view_normal = normalize((MODELVIEW_MATRIX * vec4(NORMAL, 0.0)).xyz);
	vec3 clip_normal = normalize((PROJECTION_MATRIX * vec4(view_normal, 0.0)).xyz);

	// 螢幕高度的像素轉成 NDC 倍率（NDC y 範圍 -1~1 = 2 個單位）
	float ndc_per_pixel = 2.0 / 1080.0;
	float offset = outline_pixel_width * ndc_per_pixel * clip_pos.w;

	clip_pos.xy += clip_normal.xy * offset;
	POSITION = clip_pos;
}

void fragment() {
	ALBEDO = outline_color.rgb;
}
