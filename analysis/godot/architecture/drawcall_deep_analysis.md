# Draw Call 底層完整分析（2D CanvasItem 路徑）

> 對應原始碼：`scene/main/canvas_item.cpp/h`, `servers/rendering/rendering_server_default.h`, `servers/server_wrap_mt_common.h`, `servers/rendering/renderer_canvas_cull.cpp/h`, `servers/rendering/renderer_canvas_render.h`

---

## 1. 整體架構概覽

Godot 的 2D 渲染走「**命令緩衝區（Command Buffer）+ 伺服器模式**」，整個流程分為三層：

```
[場景層]  CanvasItem::draw_rect() / draw_texture() / etc.
    ↓ 透過 RenderingServer 單例（跨執行緒安全包裝）
[伺服器層] RendererCanvasCull::canvas_item_add_rect()
            → 將 CommandRect 追加到 Item 的 command 鏈結串列
    ↓ 每幀渲染時
[GPU層]   RendererCanvasRender::canvas_render_items()
            → 遍歷 command 鏈結串列，轉換成真正的 GPU draw call
```

---

## 2. 從 _draw() 到 RenderingServer 的路徑

### 2.1 queue_redraw() 的機制

`scene/main/canvas_item.cpp:472-484`

```cpp
void CanvasItem::queue_redraw() {
    if (pending_update) return;   // 防止同幀多次排隊
    pending_update = true;
    // 透過 Callable 延遲到幀末尾執行（MessageQueue）
    callable_mp(this, &CanvasItem::_redraw_callback).call_deferred();
}
```

`queue_redraw()` 並不立即畫任何東西，它只是設置 `pending_update = true` 並排隊一個延遲回調。

### 2.2 _redraw_callback() —— 實際觸發繪製

`scene/main/canvas_item.cpp:133-155`

```cpp
void CanvasItem::_redraw_callback() {
    if (draw_commands_dirty) {
        RenderingServer::get_singleton()->canvas_item_clear(get_canvas_item()); // 清除舊命令
        draw_commands_dirty = false;
    }

    if (is_visible_in_tree()) {
        drawing = true;                               // 設定 ERR_DRAW_GUARD 通行證
        current_item_drawn = this;
        notification(NOTIFICATION_DRAW);              // 觸發 C++ 的 _draw()
        emit_signal(SceneStringName(draw));           // 觸發 GDScript 連接的 draw 信號
        GDVIRTUAL_CALL(_draw);                        // 觸發 GDExtension 的 _draw()
        current_item_drawn = nullptr;
        drawing = false;
        draw_commands_dirty = true;                   // 標記下次需要清除
    }
    pending_update = false;
}
```

**三個觸發點**：notification（C++ 繼承）、signal（GDScript 連接）、GDVIRTUAL（GDExtension）。`ERR_DRAW_GUARD` 宏就是檢查 `drawing == true`，阻止在 `_draw()` 以外的地方呼叫 draw_* 函數。

### 2.3 draw_rect() 直接呼叫 RenderingServer

`scene/main/canvas_item.cpp:815-829`（簡化）

```cpp
void CanvasItem::draw_rect(const Rect2 &p_rect, const Color &p_color, ...) {
    ERR_DRAW_GUARD;   // 確保在 _draw() 內部
    // 如果是填充矩形：
    RenderingServer::get_singleton()->canvas_item_add_rect(canvas_item, rect, p_color, p_antialiased);
}
```

`canvas_item` 是一個 `RID`——這個節點在 RenderingServer 端的不透明 handle，在 `_enter_canvas()` 時由 `RenderingServer::canvas_item_create()` 分配。

---

## 3. RenderingServerDefault 的多執行緒包裝（FUNC4 宏）

`servers/rendering/rendering_server_default.h:991`

```cpp
FUNC4(canvas_item_add_rect, RID, const Rect2 &, const Color &, bool)
```

`FUNC4` 宏展開後等於（`servers/server_wrap_mt_common.h:415-424`）：

```cpp
virtual void canvas_item_add_rect(RID p1, const Rect2& p2, const Color& p3, bool p4) override {
    WRITE_ACTION  // changes++，標記本幀需要重繪

    if (ASYNC_COND_PUSH) {
        // 從非渲染執行緒呼叫 → 推入 CommandQueueMT，渲染執行緒下次迴圈執行
        command_queue.push(server_name, &ServerName::canvas_item_add_rect, p1, p2, p3, p4);
    } else {
        // 從渲染執行緒（主執行緒）直接呼叫 → 先 flush 佇列，再直接執行
        command_queue.flush_if_pending();
        server_name->canvas_item_add_rect(p1, p2, p3, p4);
    }
}
```

其中：
- `ASYNC_COND_PUSH = (Thread::get_caller_id() != server_thread)`
- `server_name = RSG::canvas`（即 `RendererCanvasCull` 的單例）
- `CommandQueueMT` 是一個執行緒安全的 MPSC（多生產者單消費者）命令佇列

這個機制讓呼叫 `draw_rect()` 的程式碼無需知道自己是否在渲染執行緒上。

---

## 4. RendererCanvasCull —— 命令追加到鏈結串列

`servers/rendering/renderer_canvas_cull.cpp:1268-1276`

```cpp
void RendererCanvasCull::canvas_item_add_rect(RID p_item, const Rect2 &p_rect,
                                               const Color &p_color, bool p_antialiased) {
    Item *canvas_item = canvas_item_owner.get_or_null(p_item); // RID → Item*
    ERR_FAIL_NULL(canvas_item);

    Item::CommandRect *rect = canvas_item->alloc_command<Item::CommandRect>(); // 分配命令
    rect->modulate = p_color;
    rect->rect = p_rect;

    if (p_antialiased) {
        // 額外分配 4 個 CommandPrimitive 作為邊緣羽化（feather）
        // 每個 CommandPrimitive 有 4 個頂點，形成漸變透明邊界
    }
}
```

### Item 的命令儲存方式

`servers/rendering/renderer_canvas_render.h:166-196`（CommandBlock 設計）

```cpp
struct Item {
    struct CommandBlock {
        enum { MAX_SIZE = 4096 };
        uint32_t usage;
        uint8_t *memory;   // 4KB 的原始記憶體塊
    };

    struct Command {
        Command *next = nullptr;  // 鏈結串列，下一個命令
        Type type;                // TYPE_RECT, TYPE_POLYGON, TYPE_PRIMITIVE...
    };
};
```

命令用 `alloc_command<T>()` 從 `CommandBlock` 的 4KB 記憶體塊中 placement new 出來，排列在鏈結串列中：

```
Item
 └─ command_list: CommandRect → CommandPolygon → CommandRect → nullptr
                  (同一個 4KB block，連續記憶體，cache-friendly)
```

每個 `CommandBlock` 用完（4KB 滿）才新增一個。這大幅減少小物件的記憶體分配頻率。

### 所有命令型別

| 型別 | 對應 draw_*() | 資料 |
|------|-------------|------|
| `TYPE_RECT` | `draw_rect()`, `draw_texture_rect()` | Rect2, Color, RID texture |
| `TYPE_NINEPATCH` | `draw_style_box()` | 邊距 margin[4], draw_center |
| `TYPE_POLYGON` | `draw_polygon()`, `draw_colored_polygon()` | Polygon（頂點陣列） |
| `TYPE_PRIMITIVE` | `draw_line()`, 羽化邊緣 | ≤4 頂點、UV、Color |
| `TYPE_MESH` | `draw_mesh()` | RID mesh, Transform2D |
| `TYPE_MULTIMESH` | `draw_multimesh()` | RID multimesh |
| `TYPE_TRANSFORM` | `draw_set_transform()` | Transform2D |
| `TYPE_CLIP_IGNORE` | `draw_clip_ignore_push()` | bool ignore |

---

## 5. 渲染執行緒消費命令

每幀渲染時，`RendererCanvasCull::render_canvas_items_in_order()` 遍歷場景樹中所有 CanvasItem，將它們的 `Item*` 按深度排序後，送給 `RendererCanvasRender::canvas_render_items()`：

```
RendererViewport::draw_viewport()
  └─ RendererCanvasCull::render_canvas_items_in_order(sorted_items[])
       └─ for each Item*:
            RendererCanvasRender::canvas_render_items(item)
              └─ for each Command* in item->command_list:
                   switch (cmd->type):
                     case TYPE_RECT:    → 提交矩形 mesh + texture 到 GPU batch
                     case TYPE_POLYGON: → 提交多邊形頂點 buffer
                     case TYPE_PRIMITIVE: → 提交 line/quad 到批次
                     ...
```

`RendererCanvasRender` 是抽象介面，實際由 `RendererCanvasRenderRD`（Vulkan/Metal/D3D12 後端）或 `RendererCanvasRenderGL`（OpenGL 後端）實作。

---

## 6. 批次合併（Batching）

`RendererCanvasRenderRD` 會嘗試將連續的同類型命令（相同 texture、相同 shader 參數）合併成一個 GPU draw call：

```
命令序列：RectA(tex1) → RectB(tex1) → RectC(tex2) → RectD(tex1)
合併後 draw call：
  DrawCall 1: [RectA, RectB]  texture=tex1  (合併，1次 draw)
  DrawCall 2: [RectC]         texture=tex2  (無法合併，1次 draw)
  DrawCall 3: [RectD]         texture=tex1  (無法合併，1次 draw)
```

**批次中斷條件**：更換 texture、更換 material/shader、有 `TYPE_TRANSFORM`（矩陣更換）、有 `TYPE_CLIP_IGNORE`。

---

## 7. 完整呼叫鏈一覽

```
使用者程式碼
  queue_redraw()
    └─ [延遲] _redraw_callback()
         ├─ canvas_item_clear(RID)  ← 清除舊 CommandList
         ├─ notification(NOTIFICATION_DRAW)
         │    └─ CanvasItem::_draw() 或 Sprite2D::_draw()
         │         ├─ draw_rect(rect, color)
         │         │    └─ RenderingServer::canvas_item_add_rect(canvas_item_RID, ...)
         │         │         └─ [FUNC4 宏]
         │         │              ├─ [非渲染執行緒] → CommandQueueMT::push()
         │         │              └─ [渲染執行緒]   → RendererCanvasCull::canvas_item_add_rect()
         │         │                                    └─ Item::alloc_command<CommandRect>()
         │         │                                         → 追加到 Item.command_list 鏈結串列
         │         └─ draw_texture(tex, pos)
         │              └─ 同上，生成 CommandRect（帶 texture RID）
         └─ emit_signal("draw")  ← GDScript 連接的額外繪製

每幀渲染
  RendererViewport::draw_viewport()
    └─ RendererCanvasCull::render_canvas_items_in_order()
         └─ RendererCanvasRenderRD::canvas_render_items()
              └─ 遍歷 command_list → 批次合併 → GPU draw call
                   → Vulkan vkCmdDrawIndexed / OpenGL glDrawElements
```

---

## 8. 設計重點

| 設計 | 效果 |
|------|------|
| 命令鏈結串列 + 4KB CommandBlock | `_draw()` 期間零 heap 分配，cache-friendly |
| RID 取代指標 | 場景執行緒與渲染執行緒完全隔離 |
| FUNC4 宏的雙路分派 | 呼叫方無需知道執行緒身份，自動路由 |
| `pending_update` 旗標 | 同幀多次 `queue_redraw()` 只觸發一次重繪 |
| `draw_commands_dirty` | 每幀開始重建命令（避免累積舊命令） |
| 批次合併 | 相同 texture 的 draw call 自動合併，降低 GPU 狀態切換 |

---

*原始碼版本：Godot Engine 4.7.dev*
*分析日期：2026-05-22*
