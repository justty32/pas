# GDExtension 教學：程序化生成材質 (Material)

本教學將介紹如何在 C++ 中動態建立與設定 Godot 的材質資源。

## 1. 目標導向
- 如何建立 `StandardMaterial3D` 實例並動態更改顏色、金屬度等屬性。
- 如何動態載入貼圖並應用到材質。
- 如何實作 `ShaderMaterial` 並傳遞參數 (Uniforms)。

## 2. 前置知識
- 已了解 Godot 的材質與著色器概念。
- 已了解 `Resource` 的基本操作。

## 3. 原始碼導航
- **標準材質**: `scene/resources/material.h` (L200+: `StandardMaterial3D`)
- **著色器材質**: `scene/resources/material.h` (L100+: `ShaderMaterial`)

## 4. 實作步驟

### 步驟 A：建立並設定 StandardMaterial3D
這是最常用的材質類型，對應編輯器中的 "New StandardMaterial3D"。

```cpp
Ref<StandardMaterial3D> MyNode3D::create_dynamic_material() {
    Ref<StandardMaterial3D> mat = memnew(StandardMaterial3D);
    
    // 1. 設定基礎屬性
    mat->set_albedo(Color(1, 0, 0)); // 紅色
    mat->set_metallic(0.8);
    mat->set_roughness(0.2);
    
    // 2. 啟動特定功能 (如透明度)
    mat->set_transparency(BaseMaterial3D::TRANSPARENCY_ALPHA);
    
    // 3. 載入並套用貼圖
    Ref<Texture2D> tex = ResourceLoader::get_singleton()->load("res://icon.svg");
    mat->set_texture(BaseMaterial3D::TEXTURE_ALBEDO, tex);
    
    return mat;
}
```

### 步驟 B：建立 ShaderMaterial 並設定 Uniforms
如果您有自定義的 Shader 檔案。

```cpp
Ref<ShaderMaterial> MyNode3D::create_shader_material() {
    Ref<ShaderMaterial> smat = memnew(ShaderMaterial);
    
    // 1. 載入 Shader 資源
    Ref<Shader> shader = ResourceLoader::get_singleton()->load("res://my_cool_shader.gdshader");
    smat->set_shader(shader);
    
    // 2. 動態傳遞參數 (對應 Shader 中的 uniform)
    smat->set_shader_parameter("my_color", Color(0, 1, 0));
    smat->set_shader_parameter("my_intensity", 5.0);
    
    return smat;
}
```

## 5. 實務提示
- **共享材質**：如果您多個物件共用同一個 `Ref<Material>`，修改其中一個會影響全部。
- **獨特性**：若要每個物件獨立，請呼叫 `mat->duplicate()`。
- **效能**：儘量避免在 `_process` 中每幀建立新的材質實例，應建立一次後透過 `set_shader_parameter` 修改。
