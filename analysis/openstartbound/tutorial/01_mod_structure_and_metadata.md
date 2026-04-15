# 教學 01：Mod 結構與元數據

在 OpenStarbound 中，Mod 本質上是一個與核心 `assets` 目錄結構平行的資料夾。

## 1. Mod 資料夾佈局
假設你要製作一個名為 `MyHealingMod` 的 Mod，結構如下：
```text
MyHealingMod/
├── _metadata               (Mod 元數據，JSON 格式)
├── items/                  (存放道具定義)
│   └── healing_box.item
├── scripts/                (存放你的 Lua 腳本)
│   └── healing_logic.lua
└── objects/                (存放世界中的物件)
    └── healing_station.object.patch  (使用 Patch 修改現有物件)
```

## 2. _metadata 檔案
這告訴引擎你的 Mod 資訊：
```json
{
  "name": "MyHealingMod",
  "friendlyName": "Advanced Healing Mod",
  "description": "Adds advanced healing logic to the game.",
  "author": "SeniorEngineer",
  "version": "1.0",
  "includes": [],
  "requires": []
}
```

## 3. JSON Patching
如果你想修改原版的 `player.config`，你不需要覆蓋它，而是建立一個 `player.config.patch`：
```json
[
  {
    "op": "add",
    "path": "/defaultBlueprints/tier1/-",
    "value": { "item": "healing_box" }
  }
]
```
這種機制確保了多個 Mod 之間的兼容性。
