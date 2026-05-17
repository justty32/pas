# 教學：建立 Hailo C++ MLP 獨立應用程式（Meson 建置）

**重要修正**：hailo-media-library 整個生態系統使用 **Meson** 建置系統，原 CMake 教學內容完全不適用。

---

## 前提說明

`hailo-analytics` 的 case_studies 範例（如 `custom_stage`）是**在專案樹內**編譯的，使用內部 meson 變數 `libhailo_analytics_dep`。若要建立**獨立的 standalone 應用程式**（在 hailo-analytics 原始碼樹之外），需透過安裝後的 **pkg-config** 找到依賴庫。

---

## 1. 專案結構

```text
hailo_mlp_app/
├── meson.build         ← 建置描述
├── main.cpp            ← 主程式（包含自訂 MLPInferenceStage）
└── config/
    └── medialib_config.json   ← 從 case_studies 複製並修改
```

---

## 2. meson.build

```meson
project('hailo-mlp-app', 'cpp',
    version : '1.0.0',
    default_options : ['cpp_std=c++20', 'warning_level=2'])

# hailo-analytics 的 pkg-config 已涵蓋所有傳遞依賴
# （hailo-medialib、hailo-postprocess-tools、hailort、GStreamer、OpenCV 等）
hailo_analytics_dep = dependency('hailo-analytics', method : 'pkg-config')

executable('hailo_mlp_app',
    'main.cpp',
    dependencies : [hailo_analytics_dep],
    install : true,
)
```

`hailo-analytics` 的 pkg-config（安裝後位於 `/usr/lib/pkgconfig/hailo-analytics.pc`）已涵蓋所有 transitive 依賴，單一 `dependency()` 宣告即可。

---

## 3. 情境 A：在 Hailo 目標裝置上直接編譯（最簡單）

### 3.1 前提（在裝置上確認）

```bash
# 確認 hailo-analytics 已安裝
pkg-config --modversion hailo-analytics
# 預期輸出：1.11.0（或對應版本）

# 確認 meson 與 ninja 已安裝
meson --version    # >= 0.55
ninja --version
```

### 3.2 建置步驟

```bash
# 在裝置上的終端機
cd hailo_mlp_app/

# 設定建置目錄
meson setup builddir

# 編譯
ninja -C builddir

# 執行
./builddir/hailo_mlp_app --config-file-path config/medialib_config.json
```

---

## 4. 情境 B：從 x86 PC 交叉編譯（Cross-compilation）

### 4.1 準備交叉編譯工具鏈

需要：
- `aarch64-linux-gnu-g++`（Ubuntu: `sudo apt install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu`）
- Hailo SDK 的 sysroot（包含目標裝置上已安裝的 pkg-config 檔案）

### 4.2 建立 Meson 交叉編譯設定檔 `hailo_cross.ini`

```ini
[binaries]
c       = 'aarch64-linux-gnu-gcc'
cpp     = 'aarch64-linux-gnu-g++'
ar      = 'aarch64-linux-gnu-ar'
strip   = 'aarch64-linux-gnu-strip'
pkgconfig = 'pkg-config'

[properties]
# 指向 Hailo SDK 中目標裝置的 sysroot
sys_root = '/path/to/hailo_sdk/sysroot'

# pkg-config 搜尋路徑（目標裝置 sysroot 中的 pkgconfig 資料夾）
pkg_config_libdir = '/path/to/hailo_sdk/sysroot/usr/lib/pkgconfig'

[host_machine]
system     = 'linux'
cpu_family = 'aarch64'
cpu        = 'cortex-a55'
endian     = 'little'
```

### 4.3 交叉編譯

```bash
# 在 x86 PC 上
cd hailo_mlp_app/

meson setup builddir --cross-file hailo_cross.ini
ninja -C builddir

# 確認產出為 AArch64 格式
file builddir/hailo_mlp_app
# 應顯示：ELF 64-bit LSB executable, ARM aarch64
```

### 4.4 部署到目標裝置

```bash
scp builddir/hailo_mlp_app root@hailo-device.local:/home/root/
scp -r config/ root@hailo-device.local:/home/root/

# 在裝置上執行
ssh root@hailo-device.local
./hailo_mlp_app --config-file-path /home/root/config/medialib_config.json
```

---

## 5. 情境 C：在 hailo-analytics 專案樹內編譯（適合快速驗證）

將你的應用放入 `hailo-analytics/apps/` 下，仿照 case_studies 的模式：

```text
hailo-analytics/apps/my_mlp/
├── meson.build
└── main.cpp
```

`apps/my_mlp/meson.build`：
```meson
my_mlp_app_src = ['main.cpp']

executable('hailo_mlp_app',
    my_mlp_app_src,
    cpp_args : hailo_lib_args,
    dependencies : libhailo_analytics_dep,  # 直接使用樹內變數，無需 pkg-config
    gnu_symbol_visibility : 'default',
    install : true,
)
```

在 `hailo-analytics/apps/meson.build` 最後加入：
```meson
subdir('my_mlp')
```

然後從 `hailo-analytics/` 根目錄重新 `meson setup` 即可一同編譯。

---

## 6. 取得 medialib_config.json

可從 case_studies 複製現成的設定檔作為起點：

```bash
# 在目標裝置上
cp /etc/imaging/cfg/medialib_configs/case_studies/detection_medialib_config.json \
   ~/config/medialib_config.json
```

---

## 7. 總結

| 情境 | 優點 | 適用時機 |
|------|------|---------|
| A：裝置上直接編譯 | 最簡單，無需設定 sysroot | 裝置資源充足時 |
| B：x86 交叉編譯 | 開發速度快，編輯器補全完整 | 日常開發主流程 |
| C：樹內編譯 | 無需 pkg-config，直接使用內部依賴 | 快速驗證原型 |

**建置系統關鍵重點**：
- 使用 `meson setup` + `ninja`，不使用 cmake / make
- 獨立 app 透過 `dependency('hailo-analytics', method: 'pkg-config')` 取得所有依賴
- 樹內 app 使用 `libhailo_analytics_dep` 內部變數
- C++20 標準（`cpp_std=c++20`）
