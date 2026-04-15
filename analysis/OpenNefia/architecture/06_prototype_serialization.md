# 06 - 原型系統與資料序列化

## 6.1 概述

OpenNefia 的資料驅動設計核心是**原型系統（Prototype System）**。所有遊戲資料（實體、種族、職業、物品、磁磚等）都定義在 YAML 檔案中，並透過序列化系統載入為強型別的 C# 物件。

相關檔案：
- `OpenNefia.Core/Prototypes/PrototypeManager.cs` — 原型管理器（38KB）
- `OpenNefia.Core/Prototypes/EntityPrototype.cs` — 實體原型
- `OpenNefia.Core/Serialization/Manager/SerializationManager.cs` — 序列化管理器
- `OpenNefia.Core/Serialization/Manager/Attributes/` — 序列化屬性

## 6.2 Prototype（原型）基礎

原型是 YAML 資料的 C# 對應。每種原型都實作 `IPrototype` 介面：

```csharp
public interface IPrototype
{
    string ID { get; }    // 原型的唯一識別字串
}

// 常見的原型屬性
[AttributeUsage(AttributeTargets.Class)]
public class PrototypeAttribute : Attribute
{
    public string Type { get; }    // YAML 中的 type 欄位值（如 "entity"、"race"）
}
```

### PrototypeId<T> — 型別安全的原型參考

這是 OpenNefia 一個重要的設計：型別安全的原型 ID。

```csharp
// 一般的字串 ID（不安全）
string raceId = "Elona.Human";

// 型別安全的 PrototypeId（編譯時期確保型別）
PrototypeId<RacePrototype> raceId = new("Elona.Human");

// 在組件中使用
[RegisterComponent]
public class CharaComponent : Component
{
    [DataField(required: true)]
    public PrototypeId<RacePrototype> Race { get; set; } = default!;
    
    [DataField(required: true)]
    public PrototypeId<ClassPrototype> Class { get; set; } = default!;
}
```

## 6.3 EntityPrototype — 實體原型

實體原型定義了一個實體「類型」，包括它應該有哪些組件和初始值：

### YAML 格式範例
```yaml
# 一個基本的角色原型
- type: entity
  id: Elona.Warrior
  name: Warrior
  parent: BaseCharacter         # 繼承自父原型
  components:
    - type: Chara
      race: Elona.Human
      class: Elona.Warrior
      gender: Male
    - type: Skills
      HP: 100
      MaxHP: 100
      MP: 20
      MaxMP: 20
    - type: VanillaAI
      aggro: 0
```

### EntityPrototype 資料結構
```csharp
[Prototype("entity")]
public class EntityPrototype : IPrototype
{
    public string ID { get; private set; } = default!;
    
    // 父原型 ID（用於繼承）
    public string? Parent { get; private set; }
    
    // 組件定義列表
    public Dictionary<string, MappingDataNode> Components { get; } = new();
    
    // 在原型管理器中，繼承的組件資料會與父原型合併
}
```

### 原型繼承
原型支援繼承，子原型可以覆寫父原型的組件屬性：

```yaml
# 基礎角色（抽象，不直接使用）
- type: entity
  id: BaseCharacter
  abstract: true
  components:
    - type: Chara
    - type: Skills
    - type: SpatialComponent

# 具體角色（繼承自 BaseCharacter）
- type: entity
  id: Elona.Goblin
  parent: BaseCharacter
  components:
    - type: Chara
      race: Elona.Goblin        # 覆寫種族
    - type: Skills
      HP: 15
      MaxHP: 15
```

## 6.4 PrototypeManager — 原型管理器

```csharp
public sealed partial class PrototypeManager : IPrototypeManagerInternal
{
    // 所有原型的儲存（型別 → (ID → IPrototype)）
    private readonly Dictionary<Type, Dictionary<string, IPrototype>> _prototypes = new();
    
    // 原型類型的 YAML 標識符（"entity" → EntityPrototype 型別）
    private readonly Dictionary<string, Type> _prototypeVariants = new();
    
    // 繼承關係樹
    private readonly Dictionary<Type, PrototypeInheritanceTree> _inheritanceTrees = new();
}
```

### 主要操作
```csharp
// 初始化（掃描所有原型型別）
void Initialize();

// 載入目錄中的所有 YAML 原型
void LoadDirectory(ResourcePath path);

// 重新同步（處理繼承、驗證）
void Resync();

// 查詢原型
T Index<T>(PrototypeId<T> id) where T : class, IPrototype;
bool HasIndex<T>(PrototypeId<T> id);
bool TryIndex<T>(PrototypeId<T> id, out T? prototype);

// 枚舉所有原型
IEnumerable<T> EnumeratePrototypes<T>() where T : class, IPrototype;
```

### 載入流程
```csharp
// 1. 掃描目錄中的所有 .yml 檔案
// 2. 解析 YAML 為 YamlDocument
// 3. 對每個 YAML 節點：
//    - 讀取 "type" 欄位，找到對應的原型型別
//    - 用序列化系統反序列化為 C# 物件
//    - 儲存到對應的字典中
// 4. Resync() 處理繼承（合併父原型的組件資料）
```

## 6.5 SerializationManager — 序列化系統

序列化系統是一個複雜的型別映射框架（100+ 個檔案），負責在 YAML 和 C# 物件之間互相轉換。

### 核心屬性

```csharp
// 標記此類別可以被序列化
[DataDefinition]
public class SomeClass
{
    // 標記此欄位可以被序列化（必填）
    [DataField("fieldName", required: true)]
    public string RequiredField { get; set; } = default!;
    
    // 標記此欄位可以被序列化（選填，有預設值）
    [DataField("optionalField")]
    public int OptionalField { get; set; } = 0;
    
    // 不帶名稱（使用屬性名稱的小寫駝峰）
    [DataField]
    public float AnotherField { get; set; }
}

// 繼承此屬性的子類別也可以被序列化
[ImplicitDataDefinitionForInheritors]
public abstract class BaseClass { }
```

### 組件欄位序列化
組件使用 `[DataField]` 標記可序列化的欄位：

```csharp
[RegisterComponent]
public class SkillsComponent : Component
{
    [DataField] public int HP { get; set; }
    [DataField] public Stat<int> DV { get; set; } = new(0);
    [DataField] public Dictionary<PrototypeId<SkillPrototype>, LevelAndPotential> Skills { get; } = new();
}
```

### 自訂序列化器
可以為特定型別實作自訂序列化邏輯：

```csharp
// 實作 ITypeSerializer<T> 來自訂序列化
[TypeSerializer]
public class PrototypeIdSerializer<T> : ITypeSerializer<PrototypeId<T>>
    where T : class, IPrototype
{
    public DeserializationResult Read(ISerializationManager manager, 
                                      YamlNode node, ...)
    {
        var id = ((YamlScalarNode)node).Value;
        return new DeserializedValue<PrototypeId<T>>(new PrototypeId<T>(id));
    }
    
    public DataNode Write(ISerializationManager manager, 
                          PrototypeId<T> value, ...)
    {
        return new ValueDataNode(value.ID);
    }
}
```

### 資料節點類型
YAML 資料被解析為以下幾種節點類型：

```csharp
// 純量值節點（字串、數字、布林）
class ValueDataNode : DataNode
{
    public string Value { get; }
}

// 映射節點（鍵值對）
class MappingDataNode : DataNode
{
    public Dictionary<DataNode, DataNode> Children { get; }
}

// 序列節點（列表）
class SequenceDataNode : DataNode
{
    public List<DataNode> Sequence { get; }
}
```

## 6.6 常見原型類型

### EntityPrototype（實體原型）
- YAML type: `entity`
- 定義遊戲中可被生成的實體（角色、物品、建築等）

### RacePrototype（種族原型）
- YAML type: `race`
- 定義角色種族（人類、精靈、矮人等）

```yaml
- type: race
  id: Elona.Human
  name: Human
  baseStats:
    strength: 10
    constitution: 10
    # ...
```

### ClassPrototype（職業原型）
- YAML type: `class`
- 定義角色職業（戰士、法師等）

### SkillPrototype（技能原型）
- YAML type: `skill`
- 定義技能（近戰、魔法等）

### AssetPrototype（資源原型）
- YAML type: `asset`
- 定義遊戲資源（精靈圖、音效等）

```yaml
- type: asset
  id: Elona.CharaSheet
  path: "/Elona/Asset/chara_sheet.png"
  regions:
    - name: "default"
      region: [0, 0, 48, 48]
```

### MusicPrototype（音樂原型）
```yaml
- type: music
  id: Elona.Town1
  path: "/Elona/Music/gm_town1.ogg"
```

### SoundPrototype（音效原型）
```yaml
- type: sound
  id: Elona.AttackMelee
  path: "/Elona/Sound/attack_melee.ogg"
```

### LanguagePrototype（語言原型）
```yaml
- type: language
  id: JaJP    # 日文
  isFullwidth: true
```

## 6.7 Stat<T> — 帶修正值的屬性

`Stat<T>` 是一個通用的屬性包裝器，支援基礎值和修正值：

```csharp
public class Stat<T>
{
    public T Base { get; set; }      // 基礎值
    public T Buffed { get; set; }    // 帶增益的值
    
    // 常見用法
    public Stat<int> DV = new(0);   // DV 基礎值 0
}
```

## 6.8 LevelAndPotential — 技能等級與潛力

技能系統使用的資料結構：

```csharp
public class LevelAndPotential
{
    public int Level { get; set; }        // 當前等級
    public int Potential { get; set; }    // 成長潛力（百分比）
    public int Experience { get; set; }   // 當前經驗值
}
```

## 6.9 序列化驗證系統

序列化系統包含 YAML 驗證，在 `Serialization/Markdown/Validation/` 目錄下：

```csharp
// 驗證節點是否符合預期格式
class ValidationContext
{
    List<ErrorNode> Errors { get; }
    
    void AddError(string message, DataNode node);
}
```

在開發模式下，任何 YAML 格式錯誤都會在日誌中報告，方便 Mod 作者除錯。

## 6.10 YAML 資源載入路徑

原型 YAML 存放在以下位置（透過虛擬檔案系統存取）：

```
/Prototypes/         ← 引擎核心原型
    Entity/
    Race/
    Class/
    Skill/
    ...
    
/Elona/Prototypes/   ← Elona 內容原型（在 OpenNefia.Content 中）
    Entity/
    Race/
    Class/
    ...
```
