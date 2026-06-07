# 教學：新增一套聚落生成藍圖（01_add_settlement_layout）

> 目標：做一個**純資料 mod**（仿 VBGE，零 C#），讓某派系的聚落用你自製的版面與建築生成。
> 前提：你的 mod 硬相依 VFE Core（KCSG 引擎來自它）。三層模型見 `../architecture/01_kcsg_data_model.md`。

以下用「給海盜派系（`PirateBandBase`）加一座『小型瞭望站』聚落」為最小範例。實裝前未在遊戲驗證 → 標「**待實機驗證**」。

---

## 步驟 0：mod 骨架與相依
```
MyBaseMod/
├── About/About.xml
├── 1.6/Defs/MyStructures.xml
├── 1.6/Defs/MySettlements.xml
└── 1.6/Patches/MyHook.xml
```
`About/About.xml` 關鍵（照搬 VBGE 的 `About/About.xml:17-26`）：
```xml
<modDependencies>
  <li>
    <packageId>OskarPotocki.VanillaFactionsExpanded.Core</packageId>
    <displayName>Vanilla Expanded Framework</displayName>
  </li>
</modDependencies>
<loadAfter>
  <li>OskarPotocki.VanillaFactionsExpanded.Core</li>
</loadAfter>
```

---

## 步驟 1：畫建築（StructureLayoutDef）— 至少 1 棟，建議 2~3 棟同 tag

`1.6/Defs/MyStructures.xml`：
```xml
<?xml version="1.0" encoding="utf-8"?>
<Defs>
  <KCSG.StructureLayoutDef>
    <defName>My_Watchtower1</defName>
    <terrainGrid>
      <li>.,PavedTile,PavedTile,PavedTile,.</li>
      <li>PavedTile,PavedTile,PavedTile,PavedTile,PavedTile</li>
      <li>PavedTile,PavedTile,PavedTile,PavedTile,PavedTile</li>
      <li>PavedTile,PavedTile,PavedTile,PavedTile,PavedTile</li>
      <li>.,PavedTile,PavedTile,PavedTile,.</li>
    </terrainGrid>
    <layouts>
      <li>                                    <!-- 第 1 層：主結構 -->
        <li>.,Wall_BlocksGranite,Wall_BlocksGranite,Wall_BlocksGranite,.</li>
        <li>Wall_BlocksGranite,Sandbags_Cloth,.,Sandbags_Cloth,Wall_BlocksGranite</li>
        <li>Wall_BlocksGranite,.,StandingLamp,.,Wall_BlocksGranite</li>
        <li>Wall_BlocksGranite,Door_Steel,.,Door_Steel,Wall_BlocksGranite</li>
        <li>.,Wall_BlocksGranite,Wall_BlocksGranite,Wall_BlocksGranite,.</li>
      </li>
    </layouts>
    <roofGrid>
      <li>.,1,1,1,.</li>
      <li>1,1,1,1,1</li>
      <li>1,1,1,1,1</li>
      <li>1,1,1,1,1</li>
      <li>.,1,1,1,.</li>
    </roofGrid>
    <tags>
      <li>My_Watchtower</li>            <!-- 上層聚落用這個 tag 來抽我 -->
    </tags>
  </KCSG.StructureLayoutDef>

  <!-- 多畫 My_Watchtower2 / 3 都掛同一個 tag My_Watchtower，引擎就會隨機抽，聚落每次長不一樣 -->
</Defs>
```
規則回顧：`terrainGrid`/`layouts`(每個 `<li>` 一層)/`roofGrid` **同寬同高對齊**；token 直接寫原版 thing/terrain defName，`.`＝空；要旋轉寫 `defName_North/East/South/West`（如 `Cooler_South`）。範例對照 `1.6/Defs/LayoutDefs/Specialisations/VGBE_PiratesDefence.xml:3`。

---

## 步驟 2：定義聚落版面（SettlementLayoutDef）

`1.6/Defs/MySettlements.xml`：
```xml
<?xml version="1.0" encoding="utf-8"?>
<Defs>
  <KCSG.SettlementLayoutDef>
    <defName>My_PirateWatchpost</defName>
    <settlementSize>50,50</settlementSize>
    <avoidBridgeable>true</avoidBridgeable>
    <centerBuildings>
      <centerSize>40,40</centerSize>
      <spaceAround>1</spaceAround>
      <allowedStructures>
        <li><count>1~2</count><tag>My_Watchtower</tag></li>   <!-- 抽我步驟1的塔 -->
        <li><count>1~1</count><tag>GenericKitchen</tag></li>  <!-- 復用 VBGE 既有通用房 -->
        <li><count>1~3</count><tag>GenericStockpile</tag></li>
        <li><count>1~2</count><tag>GenericBedroom</tag></li>
        <li><count>1~2</count><tag>GenericPower</tag></li>
      </allowedStructures>
    </centerBuildings>
    <defenseOptions>
      <pawnGroupMultiplier>1.5</pawnGroupMultiplier>
    </defenseOptions>
    <stockpileOptions>
      <fillStorageBuildings>true</fillStorageBuildings>
      <fillWithDefs>
        <li>Gun_Revolver</li>
        <li>Silver</li>
      </fillWithDefs>
    </stockpileOptions>
  </KCSG.SettlementLayoutDef>
</Defs>
```
注意：`GenericKitchen`/`GenericStockpile`/`GenericBedroom`/`GenericPower` 是 **VBGE 已提供的通用 tag**——你直接 `allowedStructures` 引用就能複用上百棟現成房。對照 `1.6/Defs/SettlementDefs/Pirates.xml:3`。

---

## 步驟 3：（選用）自製符號 SymbolDef

只有在要「屍體/奴隸/帶旗標單位」時才需要。複用既有的（`VESSlave`、`VBGE_Corpse_Elk`）通常就夠。要新增：
```xml
<KCSG.SymbolDef>
  <defName>My_Corpse_Muffalo</defName>
  <pawnKindDef>Muffalo</pawnKindDef>
  <numberToSpawn>1</numberToSpawn>
  <spawnDead>true</spawnDead>
</KCSG.SymbolDef>
```
然後在步驟 1 的 grid 某格寫 `My_Corpse_Muffalo`。對照 `1.6/Defs/LayoutDefs/GenericLayouts/GenericKitchen.xml:405`。

---

## 步驟 4：掛到派系（Patch）

`1.6/Patches/MyHook.xml`：
```xml
<?xml version="1.0" encoding="utf-8"?>
<Patch>
  <Operation Class="PatchOperationAddModExtension">
    <xpath>/Defs/FactionDef[@Name="PirateBandBase"]</xpath>
    <value>
      <li Class="KCSG.CustomGenOption">
        <chooseFromSettlements>
          <li>My_PirateWatchpost</li>          <!-- 你的聚落版面 -->
        </chooseFromSettlements>
        <preventBridgeable>true</preventBridgeable>
      </li>
    </value>
  </Operation>
</Patch>
```
- 掛到原版/DLC 派系的對應 xpath（部落 `@Name="TribeBase"`、野民 `@Name="OutlanderFactionBase"`、海盜 `@Name="PirateBandBase"`、帝國 `[defName="Empire"]` 且要包 `PatchOperationFindMod` 判斷 Royalty）。對照 `1.6/Patches/Settlements.xml:25-77`。
- 掛到**你自訂的 FactionDef**：xpath 改成你的 `[defName="..."]` 即可，機制相同。

---

## 步驟 5：驗證（待實機驗證）
1. 啟用 VFE Core 與本 mod（本 mod 在後）。
2. 開發者模式 → 找一個該派系的世界聚落 → 帶商隊攻打/進入 → 檢查地圖是否鋪出 `My_Watchtower` + 通用房。
3. 看 log：grid token 若拼錯 defName，KCSG 通常會報「找不到 def」之類紅字 → 回去校 token 拼字與 grid 對齊。

常見坑：
- grid 三張表（terrain/layouts/roof）**行數或列數不一致**會錯位 → 嚴格對齊。
- tag 在聚落 `allowedStructures` 引用了，但沒有任何 StructureLayoutDef 帶該 tag → 那棟抽不到（可能空缺或報錯，**待驗證**）。
- 忘了 `loadAfter` VFE Core → KCSG 類別還沒載入，def 反序列化失敗。
