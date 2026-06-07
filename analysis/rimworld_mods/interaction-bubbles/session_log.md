# Interaction Bubbles 分析 session log

- 辨識：Jaxe.Bubbles（1516158345，作者 © Jaxe，組件名 Bubbles v4.2，.NET 4.7.2）；社交互動對話泡泡純 UI mod。
- 來源：projects/rimworld_mods/interaction-bubbles/decompiled/Bubbles.decompiled.cs（單檔 1116 行）。
- 結構：Bubbles(Mod/Settings)、Bubbles.Core(Bubble/Bubbler/Compatibility/Textures)、Bubbles.Configuration(設定UI)、Bubbles.Access(Reflection+4 patch)。
- 核心：唯一捕獲點＝PlayLog.Add 的 Harmony Postfix(:1100)→Bubbler.Add；繪製＝MapInterfaceOnGUI_BeforeMainTabs Postfix(:1060)→Bubbler.Draw，包 try/catch 出錯自我停用。
- 文字直接用原版 Entry.ToGameStringFromPOV(pawn)；泡泡 9-slice atlas(Inner/Outer 兩貼圖)；依 tick 淡出。
- 反射讀私有欄位 initiator/recipient/CameraDriver.rootSize（最脆弱相依）。設定系統反射驅動 Setting<T> where T:struct，~25 項。
- 相容：Widgets/GUI BeginGroup 擇一、CameraPlus LerpRootSize。
- 結論：零 Def/零 XML 資料層，純 XML 只能換貼圖+翻譯；行為全須 C#。
- create 價值＝三範式：A PlayLog.Add 通用互動捕獲點（自動吃 SpeakUp 等他 mod 文字）／B 小人頭上跟隨浮動 UI(LabelDrawPosFor+rootSize+9-slice)／C 反射零樣板 ModSettings。
- 與 SpeakUp 經原版 PlayLog/LogEntry 解耦：要更聰明對話改 SpeakUp（文字來源）不改 Bubbles（顯示層）。
- 已對 Workshop 安裝核對（…/294100/1516158345/）：唯一相依 brrainz.harmony；LoadFolders 按版本路由(1.6 主 DLL+Legacy/1.3-1.5)；3 張 PNG 貼圖；翻譯面＝Languages/English/Keyed/Bubbles.xml 31 鍵；確認無 Defs/無 Patches。OffsetDirections="Down|Left|Up|Right" 對應 :1021 Split。
- 產出 architecture/00_overview.md、details/extension_points.md。
