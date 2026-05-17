# Level 1: 初始探索 - Unciv

## 專案概述
- **名稱**: Unciv
- **目標**: 針對 Android 與桌面平台（Windows, Linux, macOS）的《文明帝國 V》(Civ V) 開源重製版。
- **核心理念**: 小巧、快速、高度可模組化 (moddable)，且能運行在低階設備上。
- **授權**: FOSS (Free and Open Source Software)。

## 技術棧 (Tech Stack)
- **開發語言**: 主要使用 Kotlin (基於 LibGDX 框架)。
- **遊戲引擎/框架**: [LibGDX](https://libgdx.com/) - 跨平台 Java 遊戲開發框架。
- **建置工具**: Gradle (Kotlin DSL, `build.gradle.kts`)。
- **部署平台**:
  - Android (Google Play, F-Droid)
  - Desktop (JAR, MSI, Flatpak, AUR, Brew)
  - Docker (支援在瀏覽器中透過 VNC 運行)

## 目錄結構初步觀察
專案採用 Gradle 多模組結構：
- `core/`: 遊戲核心邏輯、UI 與數據處理 (主要代碼所在地)。
- `android/`: Android 平台的適配與資源。
- `desktop/`: 桌面平台的入口與適配。
- `server/`: 可能用於多人連線或獨立伺服器功能。
- `tests/`: 單元測試與整合測試。
- `docs/`: 專案文檔。

## 接下來的分析方向 (Level 2)
- 深入 `core/` 目錄，識別入口點 (Entry Point)。
- 分析遊戲循環 (Game Loop) 與 LibGDX 的整合。
- 探索數據結構 (JSON 檔案) 與遊戲實體 (Units, Buildings, Civs) 的映射關係。
