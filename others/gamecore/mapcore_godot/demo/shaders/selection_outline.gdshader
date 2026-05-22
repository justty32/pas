// 兩 Pass 描邊 Shader（Low Poly 策略遊戲版）
// render_mode cull_front：只畫背面，正面看起來只露出外圍一圈
// depth_draw_always：確保描邊在被其他物件遮擋時仍然繪製（如要被遮住可改 depth_draw_opaque_prepass）
// unshaded：描邊不受燈光影響，顏色純粹

shader_type spatial;
render_mode cull_front, unshaded, depth_draw_always;

uniform vec4  outline_color : source_color = vec4(1.0, 0.85, 0.0, 1.0);
// 世界空間寬度（單位：公尺）。鏡頭縮放時視覺粗細會跟著變；
// 若需螢幕空間恆定粗細，改用 VIEW 空間縮放（較複雜）。
uniform float outline_width : hint_range(0.0, 0.1) = 0.025;

void vertex() {
	// 沿法線方向膨脹頂點，使背面從正面看只露出外圍一圈
	// Low Poly 的共享頂點（hard edge）可能在尖銳邊緣出現缺口；
	// 解法是預先計算 smooth normal 存入 UV2，這裡暫不實作。
	VERTEX += NORMAL * outline_width;
}

void fragment() {
	ALBEDO = outline_color.rgb;
}
