# 教學 10：新建完整文化種類 (Full Cultures)

當你準備好要整合以上所有內容時，這就是你建立完整文化的指南。

## 1. 資料夾結構 (參考 `OldSource`)
一個完整的文化目錄應包含：
- `/villages/`: 定義不同的村莊佈局 (Town Hall, Hamlet)。
- `/lonebuildings/`: 獨立建築。
- `/villagerconfig/`: 所有村民種類的詳細屬性。
- `/quests/`: 該文化專屬的任務集。

## 2. 文化註冊
在未來的 `CultureRegistry` 中，你需要登記該文化：
```java
public static Culture MY_CULT = new Culture("my_culture")
    .setNativeName("My Kingdom")
    .setLanguageCode("my_lang");
```

## 3. 資源整合
確保你的 `assets` 目錄下有對應文化的：
- 紋理 (Textures)
- 模型 (Models)
- 對話翻譯 (Language JSON)

## 4. 參考路徑
- `OldSource/java/org/millenaire/common/culture/Culture.java`
- 所有的 `OldSource/todeploy/millenaire/cultures/` 資料夾。
