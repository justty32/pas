# 教學 08：新建對話種類與動態標籤

對話是讓村莊感覺「活著」的關鍵。

## 1. 對話模板
Millénaire 使用特定的標籤來實現動態文本。
- `$name`: 玩家的名字。
- `$villagername`: 說話村民的名字。
- `$culture`: 該文化的名稱。

## 2. 定義對話
在 1.21.8 中，我們應在語系檔中定義：
`src/main/resources/assets/millenaire-reborn/lang/en_us.json`
```json
{
  "millenaire.speech.norman_farmer.hello": "Greetings, $name! The harvest is good in our $culture village.",
  "millenaire.speech.norman_farmer.busy": "Excuse me, $name, but $villagername is busy working."
}
```

## 3. 在 Java 中觸發
```java
public void onInteract(MillVillager villager, PlayerEntity player) {
    String text = villager.getTranslatedSpeech("hello");
    player.sendMessage(Text.literal(text), false);
}
```

## 4. 參考原始碼位置
- `OldSource/java/org/millenaire/common/utilities/LanguageUtilities.java`
- `OldSource/todeploy/millenaire/languages/[lang]/` 對話文件。
