# Sprite2D / AnimatedSprite2D 深度分析

> 對應原始碼：`scene/2d/sprite_2d.h/cpp`, `scene/2d/animated_sprite_2d.h/cpp`, `scene/resources/sprite_frames.h`, `scene/resources/texture.cpp`

---

## 1. Sprite2D 的資料模型

`scene/2d/sprite_2d.h:36-63`

```cpp
class Sprite2D : public Node2D {
    Ref<Texture2D> texture;     // 貼圖資源

    bool centered = true;       // 原點是否置中
    Point2 offset;              // 額外位移

    bool hflip = false;         // 水平翻轉
    bool vflip = false;         // 垂直翻轉

    bool region_enabled = false;// 是否啟用 UV 裁切區域
    Rect2 region_rect;          // 裁切區域（UV 空間，像素座標）
    bool region_filter_clip_enabled = false; // 邊緣過濾裁切

    int frame = 0;              // 當前幀索引（在整個 spritesheet 中的線性索引）
    int vframes = 1;            // 垂直方向幀數
    int hframes = 1;            // 水平方向幀數
};
```

`vframes`、`hframes` 定義了如何把一張 spritesheet（圖集）切分成多個幀，`frame` 是線性索引（0 開始）。

---

## 2. _get_rects() —— Frame 切割的核心數學

`scene/2d/sprite_2d.cpp:95-130`

這是 Sprite2D 最核心的計算：把 spritesheet 上的 `frame` 索引轉換成 UV 座標（`src_rect`）與螢幕矩形（`dst_rect`）。

```cpp
void Sprite2D::_get_rects(Rect2 &r_src_rect, Rect2 &r_dst_rect, ...) const {
    // 步驟一：決定 base_rect（整個 spritesheet 或裁切區域）
    Rect2 base_rect;
    if (region_enabled) {
        base_rect = region_rect;          // 使用者指定的 UV 裁切區域
    } else {
        base_rect = Rect2(0, 0, texture->get_width(), texture->get_height()); // 整張貼圖
    }

    // 步驟二：計算每一幀的大小（把 base_rect 均分）
    Size2 frame_size = base_rect.size / Size2(hframes, vframes);

    // 步驟三：把線性 frame 索引轉換成 (column, row) 座標
    // frame=5, hframes=4 → column = 5 % 4 = 1, row = 5 / 4 = 1
    Point2 frame_offset = Point2(frame % hframes, frame / hframes);
    frame_offset *= frame_size;  // 轉換為像素位移

    // 步驟四：算出 src_rect（貼圖 UV 座標）
    r_src_rect.size = frame_size;
    r_src_rect.position = base_rect.position + frame_offset;

    // 步驟五：算出 dst_rect（螢幕座標）
    Point2 dest_offset = offset;
    if (centered) {
        dest_offset -= frame_size / 2;  // 置中：原點往左上偏移半個幀尺寸
    }
    if (snap_pixel) {
        dest_offset = (dest_offset + Point2(0.5, 0.5)).floor(); // 像素對齊
    }
    r_dst_rect = Rect2(dest_offset, frame_size);

    // 翻轉：負尺寸 = 翻轉 UV
    if (hflip) r_dst_rect.size.x = -r_dst_rect.size.x;
    if (vflip) r_dst_rect.size.y = -r_dst_rect.size.y;
}
```

**翻轉的實作**：不是做矩陣變換，而是把 `dst_rect.size` 設為負值。RenderingServer 看到負尺寸的矩形，會自動反轉 UV 採樣方向。

---

## 3. Sprite2D 的繪製路徑

`scene/2d/sprite_2d.cpp:158-170`

```cpp
case NOTIFICATION_DRAW: {
    if (texture.is_null()) return;

    RID ci = get_canvas_item();  // 取得自己在 RenderingServer 的 RID

    Rect2 src_rect, dst_rect;
    bool filter_clip_enabled;
    _get_rects(src_rect, dst_rect, filter_clip_enabled);  // 計算 UV 與螢幕矩形

    // 委託給 Texture2D，讓貼圖自己決定如何繪製
    texture->draw_rect_region(ci, dst_rect, src_rect, Color(1,1,1), false, filter_clip_enabled);
}
```

### Texture2D::draw_rect_region() 的實作

`scene/resources/texture.cpp:78-83`

```cpp
void Texture2D::draw_rect_region(RID p_canvas_item, const Rect2 &p_rect,
                                  const Rect2 &p_src_rect, const Color &p_modulate,
                                  bool p_transpose, bool p_clip_uv) const {
    // 先問子類有沒有覆寫（例如 AtlasTexture 有特殊邏輯）
    if (GDVIRTUAL_CALL(_draw_rect_region, ...)) return;

    // 預設路徑：直接呼叫 RenderingServer
    RenderingServer::get_singleton()->canvas_item_add_texture_rect_region(
        p_canvas_item, p_rect, get_rid(), p_src_rect, p_modulate, p_transpose, p_clip_uv
    );
}
```

`Texture2D` 是抽象基底。`ImageTexture`、`AtlasTexture`、`CompressedTexture2D` 等子類可以覆寫 `_draw_rect_region` 來做特殊處理（例如 `AtlasTexture` 會在 src_rect 基礎上再做一層偏移）。

---

## 4. 完整繪製呼叫鏈（Sprite2D）

```
_draw() 被觸發（NOTIFICATION_DRAW）
  └─ Sprite2D::_notification(NOTIFICATION_DRAW)
       └─ _get_rects(src_rect, dst_rect, ...)    ← frame 索引 → UV 矩形
            └─ texture->draw_rect_region(ci, dst_rect, src_rect, ...)
                 └─ [GDVIRTUAL_CALL 未覆寫]
                 └─ RenderingServer::canvas_item_add_texture_rect_region(
                        canvas_item_RID,
                        dst_rect,        // 螢幕位置與大小（負值=翻轉）
                        texture_RID,     // GPU 端的貼圖資源
                        src_rect,        // UV 裁切區域
                        Color(1,1,1),    // modulate
                        ...
                    )
                    └─ [FUNC7 宏] → RendererCanvasCull::canvas_item_add_texture_rect_region()
                         └─ alloc_command<Item::CommandRect>()  ← 追加到命令串列
```

每幀繪製只產生**一個 `CommandRect`**（帶 texture RID 和 src_rect），由渲染執行緒在 `canvas_render_items()` 時轉成 GPU draw call。

---

## 5. SpriteFrames 資源的資料結構

`scene/resources/sprite_frames.h:37-51`

```cpp
class SpriteFrames : public Resource {
    struct Frame {
        Ref<Texture2D> texture;  // 這一幀的貼圖（可以是不同圖片！）
        float duration = 1.0;    // 相對持續時間（不是秒，是比例）
    };

    struct Anim {
        double speed = 5.0;      // 基礎 FPS（幀/秒）
        bool loop = true;
        Vector<Frame> frames;    // 所有幀的有序序列
    };

    HashMap<StringName, Anim> animations;  // key = 動畫名稱（如 "idle", "run"）
};
```

**關鍵**：每幀可以有不同的 `Texture2D`（不限於同一張 spritesheet），這讓 AnimatedSprite2D 比 Sprite2D 靈活得多。

`duration` 是**相對值**，不是秒。例如一個幀 `duration=2.0`，另一幀 `duration=1.0`，代表第一幀顯示時間是第二幀的兩倍。

---

## 6. AnimatedSprite2D 的時間累積與幀切換

`scene/2d/animated_sprite_2d.h:44-51`

```cpp
float frame_speed_scale = 1.0;   // = 1.0 / frame.duration，每幀不同
real_t frame_progress = 0.0;     // 當前幀的播放進度（0.0 ~ 1.0）
```

`_calc_frame_speed_scale()` 在切換幀時呼叫（`scene/2d/animated_sprite_2d.cpp:549-551`）：

```cpp
void AnimatedSprite2D::_calc_frame_speed_scale() {
    frame_speed_scale = 1.0 / _get_frame_duration();  // duration=2.0 → scale=0.5（走得慢）
}
```

### NOTIFICATION_INTERNAL_PROCESS —— 時間累積邏輯

`scene/2d/animated_sprite_2d.cpp:192-266`

```cpp
case NOTIFICATION_INTERNAL_PROCESS: {
    double remaining = get_process_delta_time();  // 本幀 delta

    while (remaining > 0) {
        // 實際速度 = 基礎FPS × 全域縮放 × 自訂縮放 × 幀持續縮放
        double speed = frames->get_animation_speed(animation)  // 基礎 FPS（如 8.0）
                     * speed_scale          // AnimatedSprite2D.speed_scale
                     * custom_speed_scale   // play() 的 p_custom_scale
                     * frame_speed_scale;   // 1/duration（幀特有）

        // 計算本幀剩餘進度能消耗多少時間
        // (1.0 - frame_progress) / abs_speed = 還需多少秒才完成這一幀
        double to_process = MIN((1.0 - frame_progress) / abs_speed, remaining);
        frame_progress += to_process * abs_speed;
        remaining -= to_process;

        if (frame_progress >= 1.0) {
            // 這一幀完成，切換下一幀
            frame++;
            frame_progress = 0.0;
            _calc_frame_speed_scale();  // 更新新幀的 speed_scale
            queue_redraw();
            emit_signal("frame_changed");

            if (frame > last_frame) {
                if (loop) { frame = 0; emit_signal("animation_looped"); }
                else      { pause(); emit_signal("animation_finished"); return; }
            }
        }
    }
}
```

**設計要點**：`while (remaining > 0)` 迴圈允許單幀 delta 跨越多個動畫幀（例如 delta=0.1s，每幀只需 0.02s，這一幀就會連跳 5 幀）。避免了低 FPS 時動畫卡頓。

---

## 7. Sprite2D vs AnimatedSprite2D 對比

| 特性 | Sprite2D | AnimatedSprite2D |
|------|---------|-----------------|
| 貼圖來源 | 單一 `Ref<Texture2D>` | `SpriteFrames` 資源（可多張不同貼圖） |
| 幀切割方式 | 數學切割（hframes × vframes grid） | 每幀獨立 `Texture2D + duration` |
| 動畫播放 | 需自行在 `_process` 中改 `frame` | 內建計時器（INTERNAL_PROCESS） |
| 多動畫支援 | 無（只有一個 frame 整數） | 有（`HashMap<StringName, Anim>`） |
| 每幀不同速度 | 無 | 有（`Frame.duration` 控制） |
| 繪製命令 | 1 個 CommandRect | 1 個 CommandRect（每幀從 SpriteFrames 取出 Texture2D） |

---

## 8. 像素對齊（Pixel Snap）

兩個類別都有相同的邏輯（`scene/2d/sprite_2d.cpp:118-120`）：

```cpp
if (get_viewport()->is_snap_2d_transforms_to_pixel_enabled()) {
    dest_offset = (dest_offset + Point2(0.5, 0.5)).floor();
}
```

`+0.5` 再 `floor()` 相當於四捨五入到最近整數像素。這確保精靈不會落在半像素位置（避免次像素模糊）。

---

## 9. set_texture() 的副作用

`scene/2d/sprite_2d.cpp:174`（簡化）

```cpp
void Sprite2D::set_texture(const Ref<Texture2D> &p_texture) {
    if (p_texture == texture) return;

    if (texture.is_valid()) {
        // 斷開舊貼圖的 changed 信號
        texture->disconnect(CoreStringName(changed), callable_mp(this, &Sprite2D::_texture_changed));
    }
    texture = p_texture;
    if (texture.is_valid()) {
        // 連接新貼圖的 changed 信號
        texture->connect(CoreStringName(changed), callable_mp(this, &Sprite2D::_texture_changed));
    }
    queue_redraw();
    emit_signal(SceneStringName(texture_changed));
}
```

Sprite2D 監聽 `Texture2D` 的 `changed` 信號，當貼圖內容被修改（如從磁碟重新載入）時，自動呼叫 `queue_redraw()` 重繪。這也是為什麼編輯器中修改貼圖檔案後，視口會即時更新。

---

*原始碼版本：Godot Engine 4.7.dev*
*分析日期：2026-05-22*
