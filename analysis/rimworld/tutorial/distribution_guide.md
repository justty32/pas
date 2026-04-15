# 打包與發布：讓全世界使用你的 Mod (Distribution)

將你的代碼編譯並發布的標準流程。

## 1. 檔案目錄結構
```text
/MyMod/
  /About/
    About.xml (關鍵！包含作者、名稱與描述)
    Preview.png (640x360, Steam 封面圖)
  /Assemblies/
    MyMod.dll (編譯後的 C#)
    0Harmony.dll (Harmony 的 DLL)
  /Defs/
    (所有 XML 數據)
  /Textures/
    (所有 PNG 資源)
```

## 2. About.xml 關鍵標籤
```xml
<ModMetaData>
  <name>我的第一個 Mod</name>
  <author>作者名</author>
  <supportedVersions>
    <li>1.4</li>
    <li>1.5</li>
  </supportedVersions>
  <packageId>AuthorName.MyFirstMod</packageId>
  <description>這個 Mod 讓莓果產量翻倍。</description>
</ModMetaData>
```

## 3. 多版本支援 (Versioning)
如果你的 Mod 支援多個版本（如 1.4 和 1.5），建議在 `Assemblies/` 下建立 `/1.4/` 和 `/1.5/` 子目錄，並分別放入對應版本的 DLL。

## 4. 發布建議
*   **保持更新**: 遊戲版本更新（如 1.5 升級）時，檢查 DLL 是否報錯。
*   **依賴宣告**: 如果你的 Mod 需要 Harmony，請在 `About.xml` 中宣告依賴。

---
*由 Gemini CLI 分析 RimWorld Mod 加載機制生成。*
