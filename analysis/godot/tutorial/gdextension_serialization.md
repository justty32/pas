# GDExtension 教學：序列化與反序列化 (存檔系統)

本教學將介紹如何在 C++ 中使用 Godot 的資源系統進行資料的儲存與讀取。

## 1. 目標導向
- 如何將自定義類別的資料儲存到磁碟檔案。
- 如何從檔案載入資料並還原為物件。
- 如何利用 Godot 內建的 `ResourceSaver` 與 `ResourceLoader`。

## 2. 前置知識
- 已完成「自定義資源 (Resources)」教學。
- 了解 `Ref<T>` 智慧指標。

## 3. 原始碼導航
- **資源儲存**: `core/io/resource_saver.h` (L100: `ResourceSaver::save`)
- **資源載入**: `core/io/resource_loader.h` (L100: `ResourceLoader::load`)

## 4. 實作步驟

### 步驟 A：利用資源系統儲存 (自動序列化)
這是最推薦的做法。只要您的資源類別正確使用 `ADD_PROPERTY` 綁定，Godot 就會自動處理序列化。

```cpp
void MyNode3D::save_game_data(String p_path) {
    // 1. 建立資源實例並填充資料
    Ref<MyDataResource> data = memnew(MyDataResource);
    data->set_player_name("Player1");
    data->set_level(10);

    // 2. 呼叫 ResourceSaver
    // 副檔名決定格式：.tres (文字), .res (二進制)
    Error err = ResourceSaver::get_singleton()->save(data, p_path);
    
    if (err != OK) {
        UtilityFunctions::print("儲存失敗！");
    }
}
```

### 步驟 B：利用資源系統載入 (反序列化)
```cpp
void MyNode3D::load_game_data(String p_path) {
    // 1. 呼叫 ResourceLoader
    Ref<Resource> res = ResourceLoader::get_singleton()->load(p_path);
    
    if (res.is_null()) {
        UtilityFunctions::print("載入失敗：檔案不存在或格式錯誤");
        return;
    }

    // 2. 轉型回您的自定義類別
    Ref<MyDataResource> data = Object::cast_to<MyDataResource>(res.ptr());
    if (data.is_valid()) {
        UtilityFunctions::print("歡迎回來，", data->get_player_name());
    }
}
```

### 步驟 C：手動 Variant 序列化 (低階)
如果您不想使用 `Resource` 系統，可以直接處理 `Variant`。

```cpp
void MyNode3D::manual_save(String p_path) {
    Dictionary save_dict;
    save_game_data["health"] = 100;
    save_game_data["pos"] = get_position();

    // 轉為 JSON 或文字
    String json_str = JSON::stringify(save_dict);
    
    Ref<FileAccess> file = FileAccess::open(p_path, FileAccess::WRITE);
    file->store_string(json_str);
}
```

## 5. 進階：序列化整個場景
您可以將動態生成的節點樹存為 `.tscn`。

```cpp
void MyNode3D::save_current_scene(String p_path) {
    Ref<PackedScene> packed_scene = memnew(PackedScene);
    // 將當前節點（及其子節點）打包
    packed_scene->pack(this);
    
    ResourceSaver::get_singleton()->save(packed_scene, p_path);
}
```

## 6. 實務提示
- **安全性**：在載入使用者生成的存檔時，請注意 `cast_to` 的安全檢查。
- **路徑**：建議使用 `user://` 路徑儲存遊戲資料，`res://` 在匯出後的遊戲中通常是唯讀的。
- **版本相容性**：若修改了 C++ 類別的屬性名稱，舊的 `.tres` 檔案可能無法正確讀取。
