# 03 - 原型與序列化 (Prototypes & Serialization)

OpenNefia 的資料驅動特型極強，大部份的遊戲邏輯與物件屬性都存放在 YAML 原型中。

## 3.1 YAML 序列化 (SerializationManager)

對應 `OpenNefia.Core.Serialization`。

在 C++ 中，我們將使用 `yaml-cpp`。為了實現類似 C# `[DataField]` 的功能，我們可以：

1. **手動寫 `Deserialize` 方法**: 對每個組件實作。
2. **利用宏 (Macros)**: 減少重複性代碼。

```cpp
// 範例：組件資料定義
struct CharaComponent {
    PrototypeId<RacePrototype> race;
    PrototypeId<ClassPrototype> charaClass;
    Gender gender;

    // 定義序列化邏輯
    static void Deserialize(const YAML::Node& node, CharaComponent& comp) {
        comp.race = node["race"].as<std::string>();
        comp.charaClass = node["class"].as<std::string>();
        // ...
    }
};
```

## 3.2 原型系統 (PrototypeManager)

對應 `OpenNefia.Core.Prototypes`。

- **PrototypeId<T>**: 使用一個強型別的結構體封裝 `std::string`。
- **PrototypeManager**: 
    - 負責載入特定目錄中的所有 `.yml` 檔案。
    - 使用 `std::unordered_map` 存放不同類型的原型。
    - 支援繼承（`parent` 欄位），在 C++ 中需要在載入時手動合併內容。

```cpp
// src/core/prototypes/PrototypeManager.hpp
class PrototypeManager {
public:
    void LoadDirectory(const ResourcePath& path);
    
    template<typename T>
    const T& Index(const PrototypeId<T>& id);

private:
    std::unordered_map<std::type_index, std::unordered_map<std::string, std::shared_ptr<IPrototype>>> _prototypes;
};
```

## 3.3 原型繼承處理

在 C++ 中，我們需要在載入時建立依賴圖，並按照繼承順序進行合併。
1. 解析 YAML 檔案並建立原始節點映射。
2. 根據 `parent` 欄位排序。
3. 依序執行節點合併 (Node Merging)。
4. 最後將合併後的 YAML 節點轉換為 C++ 物件。
