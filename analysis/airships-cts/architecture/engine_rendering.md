# Airships: Conquer the Skies — 引擎與渲染層分析（為 C++ 重寫準備）

> 目的：抽出「**引擎與渲染層必須複製的行為與資料管線**」，而非逐行照抄 Java/Slick。
> 來源：CFR 反編譯原始碼 `projects/airships-cts/src/`，shader/資產來自 Steam `data/`。
> 所有主張附 `檔名.java:行號` 或 `data/路徑`。本檔僅作索引，遇實作細節請以原始碼為準。

底層技術棧：自製引擎 `catengine`（介面層）＋ `SlickEngine`（Slick2D / LWJGL2 / OpenGL 固定管線＋GLSL）實作。遊戲端 `airships` 透過 `Screen` 狀態機與 `MyDraw` 繪圖封裝運作。

---

## 1. 引擎抽象與主迴圈

### 1.1 介面契約（catengine 核心）
極小的抽象層，C++ 重寫時應原樣保留這四個介面的語意：

- `Engine`（`Engine.java:10`）：`setup(Game)`、`runUntil(Condition)`、`destroy()`、`setExceptionHandler()`。
- `Game`（`Game.java:9`）：只有兩個方法 `input(Input)` 與 `render(Frame)`。**這是整個遊戲對引擎暴露的唯一契約** —— 每幀引擎先呼叫 `input`，再呼叫 `render`。
- `Frame`（`Frame.java:11`）：本幀的繪圖目標 + 變換堆疊。提供 `rect / blit / shift / scale / rotate / resetTransforms / getWidth / getHeight / cursor / mode / fps / nativeRenderer`。
- `Input`（`Input.java:14`）：鍵盤（`keyDown`/`keyPressed`/`lastKeyPressed`/`lastInput`）、滑鼠（`cursor`/`mouseDown`/`clicked`/`clickButton`/`scrollAmount`）、`msDelta()`（本幀毫秒差）、視窗模式（`mode`/`setMode`/`modes`）、資產預載（`preload`/`preloadSounds`/`preloadMusic`）、音效（`play`/`loop`/`playMusic`/`stopMusic`/`fadeOutMusic`）、`quit()`。
- `Condition`（`Condition.java:6`）：`runUntil` 的終止條件，但實作中 `ALWAYS.satisfied()` 永遠回 `false`（`Condition.java:10`），且 `MyAppGameContainer.runUntil` 直接 `start()` 忽略條件（`SlickEngine.java:905`）。**等同無限迴圈直到使用者退出** —— C++ 端可簡化為標準遊戲主迴圈。

### 1.2 主迴圈與計時（SlickEngine）
- 啟動：`Main.java:67` `new SlickEngine("Airships", "/com/.../images/", "/.../sounds/", 60)`，目標 **60 FPS**；`setup(g)`→`runUntil(Condition.ALWAYS)`（`Main.java:79`/`94`）。
- `init()`：`setTargetFrameRate(fps)`、`setVSync(true)`、`setShowFPS(false)`（`SlickEngine.java:138-142`）。**開 VSync + 目標 60FPS**。
- 每幀由 Slick 回呼：
  - `update(gc, delta)`（`SlickEngine.java:144`）：`g.input(new MyInput(gc, delta))`，然後清掉本幀一次性輸入狀態（keyPressed record、滾輪、click、typedText）。`delta` = 自上幀經過的毫秒。
  - `render(gc, grphcs)`（`SlickEngine.java:158`）：`g.render(new MyFrame(gc, grphcs))`。
- **計時模型 = 可變步長（variable timestep）**。引擎沒有固定步累加器；每幀把實際 `delta`（毫秒）餵給遊戲，由遊戲自行決定如何推進。`MyInput.msDelta()` 直接回傳這個 delta（`SlickEngine.java:561`）。

### 1.3 與戰鬥 TICK_LENGTH 的關係
- `Combat.TICK_LENGTH = 16`（`Combat.java:113`）、`CombatIntent.TICK_LENGTH = 16`（`CombatIntent.java:21`）。**16ms ≈ 62.5 邏輯 tick/秒**，與 60FPS 渲染近似但**獨立**。
- 因此模擬是固定步（16ms 一個物理 tick），渲染是可變步。**C++ 重寫的正解：經典「固定步累加器 + 可變步渲染」**：把每幀 `delta` 累加，每滿 16ms 跑一次 `Combat` tick，剩餘餘數用於渲染插值（本作其實多半直接用 ms 累計推動動畫，見第 4 節 `ms/interval`）。

### 1.4 輸入事件模型
- **Pull 模型 + 每幀快照**：`MyInput` 在建構時抓一次游標座標（`SlickEngine.java:469`），鍵盤狀態用反射 `Input.class.getField("KEY_"+key)` 動態查詢並快取於該幀的 `downKeys`/`pressedKeys`（`SlickEngine.java:492-520`）。
- 滑鼠 click 透過 `mouseClicked` 回呼記錄 `lastClick` + `clickButton`（`SlickEngine.java:306-310`），每幀 `update` 結尾清空（`SlickEngine.java:153`）。`mouseDown` 即時掃描按鍵 3..0（`SlickEngine.java:530`）。
- 文字輸入：`keyPressed`/`keyReleased` 累積到 `typedText` StringBuilder（`SlickEngine.java:282-304`），Mac 行為特判。
- **Hooks 命中系統**（`Hooks.java:23` `hit`）：繪圖時把矩形 + `Hook` 註冊進 `Draw.hs`，輸入階段反向遍歷（後繪先命中＝最上層優先），分 HOVER / MOUSE_n_DOWN / MOUSE_n_CLICKED 三類各取一個命中（`Hook.java:33` Type enum）。**這是「即時模式 GUI」的命中測試**：UI 不是保留樹，而是每幀重繪重註冊。C++ 端建議照搬此 immediate-mode + hook 列表模式。

> C++ 對應：用 SDL2/SFML 事件泵填一個「本幀輸入快照」結構（鍵 down/pressed 用兩個 bitset、滑鼠 click 邊緣偵測、滾輪累加、typedText），暴露 `msDelta()`。Engine 主迴圈：poll events → 填快照 → `game.input(snapshot)` → `game.render(frame)` → swap + vsync。

---

## 2. Screen 狀態機

### 2.1 Screen 介面（`Screen.java:13`）
```
void input(Input, MyDraw.State, Pt cursor, Pt click, int msDelta)
void render(MyDraw, ScreenMode, Hooks, Pt cursor)
ArrayList<String> music()          // 此畫面想播的背景音樂候選
String appearancePostfix()         // 主題後綴（見 2.3）
boolean alwaysUseAppearancePostfix()
```

### 2.2 切換與分派（AirshipGame）
- **單一「當前畫面」**，不是堆疊：`AirshipGame` 持有 `public Screen s`（`AirshipGame.java:116`，初值 `ResChooserScreen`）。切換 = 直接賦值 `this.s = new XxxScreen(this)`（如 `:404` ExitScreen、`:515`/`:990`/`:1021` MainMenu、`:737` LoadingScreen）。
- 另有 `prevScreen` / `postInputScreen`（`:160-161`）僅用於記錄上一幀畫面，非堆疊。
- **分派**：`AirshipGame.input()` 在 `:1276` 呼叫 `this.s.input(in, drawState, cursor, clk, msDelta)`；`render()` 在 `:1383` 呼叫 `this.s.render(new MyDraw(f, hs, drawState, integration), f.mode(), hs, cursor)`。
- Overlay（說明、多人聊天）以「先處理 overlay，再用 `BlankInput` 包住底層 input 吃掉事件」實作（`:1273-1274` `in = new BlankInput(in)`），而非真正的畫面堆疊。
- `music()` 由 `AirshipGame` 在 `:1031` 取得當前畫面的候選清單來決定播放。

### 2.3 appearancePostfix（主題/spritesheet 變體）
- render 開頭根據當前畫面決定要載入哪個 spritesheet 變體（`AirshipGame.java:1363-1368`）：
  - 若 `alwaysUseAppearancePostfix()` 或低畫質/無光照/shader 失敗 → `Appearance.switchSpritesheet(s.appearancePostfix())`；
  - 否則 → `switchSpritesheet("")`（用無後綴的「帶 bump 的光照版」基底）。
- 範例：`StrategicScreen` 回 `"DAY"` 且 `alwaysUseAppearancePostfix()=true`（`StrategicScreen.java:7984-7990`）—— 戰略地圖一律用平塗 DAY 圖（不跑昂貴的逐像素光照）。`MainMenu` 回 `"BLUEPRINT"`（`MainMenu.java:2077`）—— 主選單背景船是藍圖風。
- `switchSpritesheet(postfix)`（`Appearance.java:105`）：只在 postfix 改變時，對所有 `SpritesheetBundle` 呼叫 `loadPostfix`，並 `++switchNum`（讓各 Appearance 下幀 lazy 重綁子圖，`:137 updateSpritesheet`）。
- 「冬季」之類季節主題：後綴對應到資產檔（`data/generated/backdropWinter*.png.tex`、`landscapeWinter*`），與 `DAY`/`DAMAGED`/`FRAGMENTS`/`BLUEPRINT` 同屬「postfix 選擇貼圖變體」機制。

> C++ 對應：`Screen` 介面照搬。用一個 `Screen* current` 指標 + `switchTo(new ...)`。主題後綴 = 一個 string，驅動「同一邏輯精靈 → 選哪張實體貼圖集」的查表（見第 4 節）。

---

## 3. 繪圖 API

### 3.1 原語（Frame → Draw → MyDraw 三層）
- **底層 `Frame`**（`SlickEngine$MyFrame`）暴露最小原語：
  - `rect(Clr, x, y, w, h, angle)`：直接 `glBegin(GL_QUADS)` 畫實心矩形，無貼圖；angle≠0 時用 `g.rotate` 繞中心旋轉（`SlickEngine.java:341-370`）。
  - `blit(Img, Clr tint, double alpha, x, y, w, h, angle)`：核心貼圖原語（`SlickEngine.java:372-409`）。w/h 為 0 時用貼圖原尺寸。**染色（tint）的混合語意很特別**：
    - tint==null：只設 alpha 後 draw。
    - tint.a==255：`image.draw(..., color)`（Slick 把顏色當乘法 modulate）。
    - tint.a<255：**畫兩遍** —— 先畫原圖（權重 `255-a`），再用 tint 色畫一遍（權重 `a`），達成「部分染色」效果（`:397-407`）。C++ 重寫要複製此兩遍混合，否則染色觀感不同。
  - 變換：`shift`(translate)、`scale`、`rotate`（繞 0,0）、`resetTransforms`（`:411-425`），對應 OpenGL 模型視圖矩陣堆疊。
- **`Draw`**（`Draw.java:18`）：在 `Frame` 上加便利多載（一堆 `blit(...)` 重載）、`rect`、**hook 註冊版多載**（畫的同時把矩形+Hook 加進 `Hooks`，`Draw.java:113-147`），以及**富文本排版** `doText`（`Draw.java:198`）。
- **`MyDraw`**（`MyDraw.java:47`，extends Draw）：遊戲級 UI 套件。大量 9-slice 面板/視窗/按鈕的圖集座標常數（`ui` 圖集，例如 `WIN_TL=new Img("ui",19,845,9,9)`，`MyDraw.java:189`），九宮格繪製 `drawWindow`/`drawPanel`/`drawShadowedWindow`（`:611`/`:700`/`:654`），木紋平鋪 `drawWoodGrain`（`:574`），進度條（`:528`），高亮箭頭（`:492`，直接用 Slick `Graphics` 畫多邊形）。持有 `State`（`:466`）。

### 3.2 富文本排版（doText, `Draw.java:198`）
重寫文字系統時必須複製的行為：
- 自動斷行（含 CJK 不可斷字元集 `UNBREAKABLE`，`Draw.java:357`）。
- 內嵌指令：`[hexcolor]` 設色（支援 `RRGGBBAA` 10 位含 alpha，`:309`）、`[bg=...]`、`[default=...]`、`{symbol}` 內嵌符號圖、`{[color]symbol}` 染色符號（`:259-334`）。
- 顏色名表 `knownColors` + `Clr.fromHex` + 具名色（`Clr.java:94`）。
- 字寬由 `Fount.getWidth(char)` 決定（逐字寬度，見第 6 節）。

### 3.3 座標系與相機
- **座標系：左上原點，Y 向下，像素單位**（Slick/OpenGL 視窗座標）。游標 `gc.getInput().getMouseX/Y`（`SlickEngine.java:454`）。
- **沒有獨立的相機物件**；世界相機 = 直接用 `Draw.shift/scale`（平移+縮放）變換矩陣堆疊來實作（在世界渲染前 push 變換，UI 用 `resetTransforms` 回螢幕座標）。`ScaledFrame`（`AirshipGame.java:1373`）是另一種固定解析度縮放路徑（先渲到 `scaleBuffer` 再放大）。
- `ScreenMode`（`ScreenMode.java`）：`width/height/fullscreen/fullscreenWindow`。

### 3.4 Img 圖集座標慣例（`Img.java`）
- `Img(src, srcX, srcY, srcWidth, srcHeight, flipped)`：**src=圖集檔名（無副檔名，載入時補 `.png`，`SlickEngine.java:227`），srcX/Y/W/H = 在圖集內的子矩形**。w/h 為 0 表示用整張圖。
- `flipped`：水平翻轉變體，key 加 `___flipped`（`Img.java:38`），SlickEngine 用 `getFlippedCopy` 快取（`:198-208`）。
- transient 快取欄位 `machineImgCache`（實際 GPU Image）、`machineWCache/HCache`（`Img.java:23`）—— **C++ 對應：Img = 不可變的「圖集 + UV 子矩形」描述，外加一個指向已上傳貼圖/atlas page 的快取指標**。
- `Img.loadMap(InputStream)`（`Img.java:49`）：從文字檔讀「名稱→子矩形」對照表（n 筆，每筆：key / src / x / y / w / h）。

> C++ 對應：`Frame` 原語層 = 一個 sprite batcher（`rect`/`blit`/變換堆疊）。`Draw`/`MyDraw` 照搬為「在 batcher 上的便利函式 + immediate-mode UI + 富文本」。tint 兩遍混合務必複製。

---

## 4. 資產管線

### 4.1 Spritesheet 組織（`SpritesheetBundle.java`）
- 一個 bundle = 一張大圖集（**正方形且邊長為 2 的次方**，size 由載入時 `sh.getWidth()` 記錄，`:120-123`；貼圖過濾 `9728`=GL_NEAREST，`:117`）。
- bundle 可帶：`bump`（法線/凹凸貼圖名）、`fragments`（碎片）。若 `bump!=null && fragments!=null`，自動建立兩個衍生 bundle：`<name>DAMAGED`（bump `<bump>DAMAGED`）與 `<name>FRAGMENTS`（`SpritesheetBundle.java:76-82`）。
- **postfix → 實際貼圖** 的兩層 map：`postfixToSheet`（Slick Image）與 `postfixToTex`（OpenGL Texture），`getTex(postfix)`/`getSheet(postfix)` 查表，找不到 fallback 到 `""`（`:42-70`）。
- `loadPostfix(postfix)`（`:108`）：載入 `<name><postfix>` 圖；遞迴載 DAMAGED（除 BLUEPRINT 外）與 FRAGMENTS（僅 `""`），並保證 `""` 基底也載入。
- `initBumps()`（`:85`）：載 bump 貼圖，**過濾設為 GL_NEAREST**（法線貼圖不可線性插值）。

### 4.2 generated/*.png.tex 的角色（預處理快取）
`SpriteUtils.loadImageFromFile`（`SpriteUtils.java:102`）揭示管線：
- 對每個 `images/<name>.png`，檢查 `generated/<name>.png.tex`。`.tex` 較新就**直接 memory-map 載入原始 RGBA 像素**（`ChanneledImageData`，`SpriteUtils.java:115`/`:327`）—— **跳過 PNG 解碼**，是預烘焙的「裸 GPU 貼圖資料」快取。
- 若無 `.tex`，從 PNG 載入後，當尺寸是 16..16384 的 2 次方（`doCacheRaw`/`:183`、`:191`）就把 `texture.getTextureData()` 寫出成 `.tex`（`:165-176`）。
- `ChanneledImageData`：buffer 容量/4 開根號得邊長，斷言必為 2 次方（`:332-340`），格式固定 RGBA。

### 4.3 DAY / DAMAGED / FRAGMENTS / bump / BLUEPRINT 變體（命名規律）
從 `data/generated/` 實測（共 203 個 .tex）歸納：對基底名 `X`：
- `X.png.tex`：**基底彩色圖**（給帶光照 shader 用，需搭配 bump）。
- `XDAY.png.tex`：**日間平塗版**（不需逐像素光照，戰略圖/低畫質用，對應 `appearancePostfix()=="DAY"`）。
- `XDAMAGED*.png.tex`：受損外觀；又分 `XDAMAGED.png.tex`（光照版）+`XDAMAGEDDAY.png.tex`（平塗版）。
- `XFRAGMENTS.png.tex`：船體碎裂後的碎片圖。
- `X_bump.png.tex`：**法線/凹凸貼圖**（紅綠通道 = 表面朝向 x/y，藍通道 = 「亮度/shiny」強度；見第 5 節 shader 解讀）。也有 `X_bumpDAMAGED`/`X_bumpFRAGMENTS`。
- 季節：`backdropWinter*` / `landscapeWinter*` 對應冬季主題。
- 帆有獨立的 `sail`/`bumpsail`/`flippedsail`/`flippedbumpsail` 系列（含 DAMAGED/FRAGMENTS）。

**關鍵理解**：同一個邏輯精靈在不同情境（晝夜光照 vs 平塗、完好 vs 受損 vs 碎片、藍圖預覽）會切到不同實體貼圖；bump 圖與彩色圖一一對應，餵給光照 shader。C++ 重寫要把「邏輯精靈 ID」與「(postfix, damage-state) → 實體 atlas + UV」分離。

### 4.4 動畫定義
兩套並存：

**(A) Appearance 逐幀序列**（`Appearance.java`）：
- `frames: ArrayList<Frame>` + `interval`（毫秒，預設 300，`Appearance.java:60`）。
- 取幀：`frames.get(ms / interval % frames.size())`（如 `:272`/`:325`/`:437`/`:184`）—— **以累計毫秒除以 interval 取模**。這就是把可變步 ms 轉成幀號的方式，C++ 直接照抄。
- 翻轉幀 `flippedFrames` lazy 建立（`:149-153`）。`checksum()`（`:76`）用於資產比對。

**(B) AnimationBundle / AnimationAppearance 骨架動畫**（船員、生物、龍）：
- `AnimationBundle`（`AnimationBundle.java`）：`width/height` + `BodyPlan`（部位清單）+ `EnumMap<AnimationType, Animation>`。`AnimationType` 有 34 種狀態（`AnimationType.java`：STANDING/WALK/CLIMB/SHOOT/FLY/DEAD…）。
- `Animation`（`:37`）：`length`（0=LOOPING）、`side`、`parts[]`。
- `Part`（`:56`）：每部位的 `x,y` + **程序化動畫參數**：旋轉 `cOff/cPeriod/cW/cH`（rotationOffset/Period/Width/Height）、波動 `wOff/wPeriod/wStart/wEnd`（waveOffset/Period/StartAngle/EndAngle）、`holdsResource`。即「正弦驅動的部位平移/旋轉」程序動畫，非逐幀（見 `data/AnimationBundle/bee.json`：wing 用 `wPeriod:20, wStart:0.5, wEnd:-2.5` 拍翅）。
- `AnimationAppearance`（`AnimationAppearance.java`）：把 bundle 綁到具體 spritesheet，`EnumMap<Side, Img[]>` 存每部位的子圖，外加 `emitters`/`deadEmitters`（粒子發射器：type/freq/x/y/scale，`:86`）。亦支援純逐幀 `frameAnimations`（`CrewFrameAnimation`，`:30-39`）。
- **武器槍管動畫**（題目指定範例）：`WeaponAppearance`（`WeaponAppearance.java`）有 `barrelAnimation`/`externalBarrelAnimation`/`flipped*`（`:36-39`），`BarrelAnimation` 含 `frames` 列表，`shotAnimationInterval`（預設 150ms，`:29`）、`barrelLoadStages[]`（分階段裝填圖）、`recoil`（後座位移，`:42`）。開火時依 ms 推進槍管幀。

### 4.5 字型 fontmetrics（`Fount.java`）
- `Fount.fromStream`（`Fount.java:56`）解析 `data/fontmetrics/*.txt`：每兩行一組 = 字元 / `x y w h`（圖集子矩形）；特殊行 `letterSpacing N` / `letterXOffset N`。lineHeight = 最大 h。
- 字元 <256 存陣列 `imgs[256]`，其餘存 `extended` HashMap（CJK），並支援 `subFounts` 串接（基底拉丁 + CJK 子字型 + symbols 子字型，見 `fatfledermaus18.txt` + `.chi`/`.jpn`/`.kor`/`.symbols`）。
- 每字一張圖集子圖；`get(c)`/`getWidth(c)` 查表（`:85`/`:101`）。**這是 bitmap 圖集字型**，非 TTF。`AGame.FOUNT = GUISetting.getFount("libmono12","libmono12.txt")`（`AGame.java:39`）。

---

## 5. Shader 清單（`data/*.frag` / `*.vert`）

### 5.1 光照模型核心概念（litfrag 系列）
全域有 **4 張「方向光」貼圖**（lightFromLeft/Top/Right/Bottom），是螢幕空間的低解析度光照緩衝（`/ lightSize / 4.0` 採樣，`litfrag.frag`），記錄場景中各方向的入射光。逐像素：
1. 從 **bump 貼圖**取 `bumpLookup`：`.x`=上下朝向、`.y`=左右朝向、`.z`=shiny/強度（`litfrag.frag:18`，註解 bly 是左右、blx 是上下）。
2. 由朝向算出朝四個方向的反射係數 `leftM/rightM/topM/bottomM = max(face-0.3,0)*2*shiny*strength`。
3. 用 `gl_FragCoord` 反查四張方向光貼圖，乘以對應係數累加。
4. 套用**飽和度矩陣** `satur`（由 `ambientSaturation` 控制去飽和，黃昏/陰天用）+ `ambient` 環境色乘法 + `ambientMult`（由 bump.z 微調 0.85~1.1）。
5. `flipped` 時左右光源互換。
- Uniforms：`tex, bump, lightFromLeft/Top/Right/Bottom, lightSize(vec2), screenHeight, ambient(vec4), ambientSaturation, texSize`。
- 頂點屬性：`flipped, strength, tint`（litfrag.vert）。
- **重要**：所有 `texture2D(tex, floor(uv)/texSize)` —— **手動 nearest（floor）採樣**，因像素風格不可線性插值。`texSize`=圖集邊長。
- 綁定流程見 `Appearance.lockShader`（`Appearance.java:469`）/`draw`（`:560`）：bump→TU1，4 張光→TU2-5，主圖→TU0，全用 `GL13.glActiveTexture`+`GL11.glBindTexture`，並 `enableVertexAttribute("flipped"/"tint"/"strength")`，最後 `glBegin(GL_QUADS)` 批次。

### 5.2 各 shader 用途與「重寫需支援的特效清單」
| Shader | 用途 | 關鍵 uniform/attr | 重寫特效 |
|---|---|---|---|
| `frag.frag` + `passthrough.vert` | 基礎貼圖 + tint，nearest 採樣（`switchSpritesheet("")` 無光照路徑） | `tex, texSize`; attr `tint` | 像素貼圖批繪 |
| `litfrag.*` | **2D 法線光照**（主力，船體模組） | 見 5.1 | 多方向螢幕空間光 + bump + 飽和/環境 |
| `bevelled_litfrag.*` | litfrag + **斜面立體邊**（模組相鄰邊緣依 `bevel` vec4 與 16px 格內局部座標調整朝向，產生凸起感） | + attr `bevel`(top/bottom/left/right) | bevel 邊緣法線改寫 |
| `masked.*` | **遮罩裁切** + paint 染漆 | `mask, texSize`; attr `maskOffsetAndEnabled, globalTexCoord, paint, tint` | alpha 遮罩剔除 + 油漆色混合 |
| `bevelled_masked_litfrag.*` | 光照+bevel+遮罩+maskBump+9 區塊邊緣剔除+paint（最複雜，模組拼接邊界） | 上述總和 + `maskBump, vt/vm/vb` 9 鄰接旗標 | 全功能模組渲染 |
| `sub_litfrag.*` / `sub_frag.frag` | litfrag + **顏色替換**（把接近 srcA 的像素換成 trgA，用於陣營配色/heraldry） | attr `srcA(vec3), trgA(vec4)`; `refTex` | 調色板色替換 |
| `rotated_litfrag.*` / `rotated_sub_litfrag.frag` | 可任意旋轉物件的光照（依 `angle` 旋轉四方向光的權重混合，螺旋槳/輪子） | attr `angle` | 隨物件角度旋轉的法線光 |
| `flag.*` / `litflag.frag` | **旗幟波動變形**（依 `wind/t/yShift` 用 cos 扭曲 UV，超出範圍 alpha=0） | attr `flagSize, texOffset, awind, at, ayShift` | 頂點/UV 風致變形 |
| `pennant.*` / `litpennant.frag` | 三角燕尾旗變形（同上但裁切成三角） | 同 flag + `acoord` | 同上 |
| `flagmap.frag` | 旗幟貼圖 + arms 紋章合成（依 map 的 alpha 混 arms 色） | `tex, map, arms` | 紋章貼花合成 |
| `outline.frag` | **外框描邊**（取 8 鄰 alpha，邊界像素輸出 `gl_Color`） | `tex, texSize` | 選取輪廓 |
| `redoutline.frag` | 純紅實心剪影（alpha>0→紅） | `tex, texSize` | 紅色高亮剪影 |
| `retone.frag` | **三階色調分離**（亮度分 darkest/dark/light 三段重新著色） | `darkest/dark/light(vec3)` | 風格化重著色 |
| `blueprint.frag` | **藍圖風**（亮度→白色線稿 alpha，主選單/設計模式 `appearancePostfix=="BLUEPRINT"`） | `intensity, texSize` | 藍圖預覽 |
| `color.frag` | 純色填充 | — | 實心多邊形 |
| `smoothfrag.*` / `prettyscale.*` | **線性採樣**版貼圖（不 floor，用於背景/縮放，UI buffer 放大） | `tex` | 平滑縮放 blit |

> C++ 重寫渲染特效清單（最小完整集）：① 像素 nearest 批繪 + tint；② 2D 多方向法線光照（4 張螢幕空間光緩衝 + bump RG=法線/B=shiny + ambient + 去飽和矩陣）；③ bevel 邊緣法線調整；④ alpha 遮罩 + 9 鄰接邊緣剔除；⑤ 旋轉物件的光照權重混合；⑥ 顏色替換（陣營/紋章調色板）；⑦ 旗幟/燕尾旗 UV 風致變形；⑧ 描邊/紅剪影；⑨ 三階 retone；⑩ 藍圖；⑪ 線性平滑縮放。光照緩衝的「生成」（把光源畫進 lightFrom* 貼圖）需另查光源渲染程式碼，但 shader 端只是採樣它們。

---

## 6. C++ 重寫建議

### 6.1 引擎選型
- **渲染後端建議 bgfx 或 raylib + 自寫 batcher**；若要最貼近原行為，**OpenGL 3.3 core + 自寫 sprite batcher** 最直接（原作就是 OpenGL 固定管線 + GLSL，shader 幾乎可直接移植，只需把 `gl_TexCoord[0]`/`gl_Color`/`gl_ModelViewProjectionMatrix` 改成 in/out + uniform MVP）。SDL2 負責視窗/輸入/音訊。SFML 亦可但要繞過其 sprite 抽象。
- **不要用引擎內建場景圖**：本作是即時模式 + 手動批次，保留之。

### 6.2 架構對應表
| Java/Slick | C++ 對應 |
|---|---|
| `Engine.runUntil` 主迴圈 | SDL 主迴圈：poll→input snapshot→`game.input`→`game.render`→swap(vsync) |
| `Game.input/render` | 同名兩方法的抽象基類 |
| `Frame`（rect/blit/變換堆疊） | Sprite batcher + `glm::mat3/4` 變換堆疊（push/pop） |
| `Draw`/`MyDraw` | batcher 上的便利層 + immediate-mode UI（9-slice/富文本/hooks） |
| `Input`（每幀快照、反射查鍵） | 輸入快照結構，鍵名→keycode 用 `unordered_map` 取代反射 |
| `Hooks`（矩形+回呼，反向命中） | `vector<pair<Rect,function>>`，render 階段 push，input 階段反向掃描 |
| `Img`（src+子矩形+flipped+快取） | `struct Sprite{atlasId; UVRect; bool flipped; TexHandle cache;}` |
| `Clr`（tint 兩遍混合） | RGBA8 struct，複製兩遍 alpha 混合語意 |
| `Fount`（bitmap 圖集字型 + subFounts） | 圖集字型，char→glyph rect，subfont 串接（CJK） |
| `SpritesheetBundle`（postfix→tex/bump） | `unordered_map<string, Atlas>` + bump 對應 |
| `Appearance`（frames + ms/interval + shader 綁定） | 動畫元件（幀序列）+ shader 管理器 |
| `AnimationBundle/Part`（程序骨架動畫） | 部位變換用正弦參數驅動（cOff/cPeriod/wStart/wEnd） |
| `Screen` 狀態機 | `class Screen` 介面 + `Screen* current` 指標切換 |
| `.png.tex` 快取 | 自訂二進位裸 RGBA 快取（mmap 載入，跳過 PNG 解碼） |

### 6.3 計時/迴圈
- 渲染：可變步 + vsync 60FPS。模擬：**固定 16ms tick（`Combat.TICK_LENGTH`）** 用累加器分離。動畫一律 `accumulatedMs / interval % frameCount` 取幀（與固定步無關），照抄。

### 6.4 貼圖/圖集載入
- atlas 必為 2 次方正方形、**GL_NEAREST 過濾**（像素風格 + shader 內 floor 採樣的前提）。bump 也是 GL_NEAREST。
- 實作 `.png.tex` 等價的「裸 RGBA mmap 快取」可大幅加速啟動（原作對所有 2^n 圖都這樣做）。
- postfix/damage-state → atlas 的查表分離（4.3）。

### 6.5 移植風險
1. **tint 兩遍混合**（`SlickEngine.java:397-407`）：Slick 的 `Image.draw(...,color)` 是乘法 modulate；alpha<255 時畫兩遍。直接用單遍 modulate 會讓「半染色」物件外觀錯誤。
2. **光照系統的 4 張螢幕空間光緩衝**：本檔只解出 shader 採樣端；**光源如何被畫進 lightFrom* 緩衝、lightSize/strength 來源** 需再追 `Appearance.lockShader` 的呼叫端與光源渲染（未涵蓋，列為後續 Level）。
3. **bump 通道語意**：RG=表面朝向(0.5 中性)、B=shiny/強度、並非標準切線空間法線；retone/blueprint 等用亮度。複製公式時注意 `floor(uv)/texSize` nearest 與 `0.3/0.7` 的硬閾值。
4. **bevelled_masked_litfrag 的 16px 格座標 + 9 鄰接剔除**：依賴模組以 16px 為網格、相鄰旗標 `vt/vm/vb`。重寫模組拼接時必須提供同樣的鄰接資訊與 maskBump。
5. **reflection 查鍵**（`KEY_+name`）：C++ 改用靜態 map；注意 Slick 鍵名集合與 SDL keycode 的對應差異。
6. **單一 Screen + BlankInput overlay**：沒有真正堆疊；overlay 靠「吃掉輸入」實作，照搬即可，但別誤改成 push/pop 堆疊而改變焦點語意。
7. **Hooks 每幀清空 + 反向命中**：UI 完全 immediate-mode，不能引入保留式 widget 樹否則命中順序/焦點會變。
8. CFR 反編譯偽影（`finally` 內 `is.close()` 可能 NPE、`WARNING - Removed try catching itself`）不影響語意理解，但別照抄錯誤的 null 處理。

---

## 附：關鍵檔案索引
- 引擎介面：`catengine/{Engine,Game,Frame,Input,Img,Loop,Hook,Hooks,Condition}.java`
- 引擎實作：`catengine/SlickEngine.java`（迴圈 `:144/158`、blit `:372`、輸入 `:458`）
- 繪圖：`catengine/Draw.java`（doText `:198`）、`airships/MyDraw.java`（UI 套件 + State `:1497`）
- 字型：`catengine/Fount.java`、`data/fontmetrics/*.txt`
- 狀態機：`airships/Screen.java`、`airships/AirshipGame.java`（`s` 欄位 `:116`、分派 `:1276/:1383`、postfix 切換 `:1363`）
- 資產：`airships/SpritesheetBundle.java`、`airships/SpriteUtils.java`（`.tex` `:102`）、`airships/Appearance.java`（shader 綁定 `:469/:560`、動畫 frames/interval）
- 動畫：`airships/{AnimationBundle,AnimationAppearance,AnimationType}.java`、`airships/WeaponAppearance.java`（barrelAnimation `:36`）
- Shader：`data/*.frag`、`data/*.vert`
- 啟動：`airships/Main.java:67`（60FPS）；tick：`airships/Combat.java:113`（TICK_LENGTH=16）
