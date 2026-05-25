# Hailo Media Library — Level 1 初始探索

## 專案定位

**hailo-media-library** 是 Hailo Technologies 為其 **Hailo-15** AI 視覺 SoC 提供的 C++ SDK，  
提供從感測器輸入到 AI 推論後處理、影像編碼與輸出的完整 Media Pipeline 管理。

- **GitHub**: hailo-ai/hailo-media-library
- **授權**: LGPLv2.1
- **依賴**: GStreamer 1.20、HailoRT 5.2.0、nlohmann/json、tl::expected、Perfetto
- **構建系統**: Meson
- **目標硬體**: Hailo-15 SoC（嵌入式 AI 視覺晶片）

---

## 倉庫頂層模組（Monorepo 結構）

```
hailo-media-library/
├── hailo-media-library/   ← 核心 Media Library（視覺前端處理 + 編碼 + OSD）
├── hailo-postprocess/     ← AI 推論後處理（YOLO、分割、OCR、Landmarks）
├── hailo-analytics/       ← 高階 Analytics Pipeline（Stage-based 並行管線）
└── tools/                 ← 示範 App 與 Host 側工具
```

---

## 技術棧

| 層級 | 技術 |
|------|------|
| 硬體介面 | v4l2（感測器）、DSP（影像處理）、HailoRT（AI 推論） |
| 媒體框架 | GStreamer 1.20 |
| 影像格式 | NV12（主要）、A420、ARGB |
| 配置格式 | JSON（nlohmann/json），支援 profile 系統 |
| 錯誤處理 | `tl::expected<T, E>` |
| 效能追蹤 | Perfetto tracing |
| 並行 | std::thread + 環形 Queue，各 Stage 獨立執行緒 |

---

## 核心模組職責（Level 2 預覽）

### 1. hailo-media-library — 視覺前端處理引擎

路徑：`hailo-media-library/hailo-media-library/media_library/`

**Frontend Pipeline 流程**：

```
感測器 (v4l2/APPSRC)
  → ISP (影像信號處理)
  → HDR (High Dynamic Range，DoL-2/3)
  → LDC (Lens Distortion Correction)
      ├─ Dewarp（魚眼鏡頭去畸變）
      ├─ DIS（Digital Image Stabilization，光流法）
      ├─ EIS（Electronic Image Stabilization，陀螺儀輔助）
      ├─ Flip / Rotation
      └─ Optical Zoom
  → Denoise（AI 降噪，HailoRT 推論，支援 Bayer/YUV 迴授網路）
  → Multi-Resize（DSP 多路縮放 + Digital Zoom + 動態偵測）
  → 多路輸出 (output_stream_id_t)
      ├─ Encoder（H.264/H.265 硬體編碼 or JPEG）
      ├─ OSD（On-Screen Display：圖片/文字/時間戳疊加）
      └─ Privacy Mask（靜態多邊形遮罩 / 動態 AI 遮罩）
```

**核心子模組**（`src/` 目錄）：

| 子模組 | 職責 |
|--------|------|
| `front_end/` | LDC mesh 計算、Dewarp、Multi-resize、動態偵測 |
| `dsp/` | DSP 影像操作（crop/resize/overlay 呼叫） |
| `dis_library/` | 數位影像穩定（光流法計算 VSM offset） |
| `eis_library/` | 電子影像穩定（陀螺儀 + IIR HPF 濾波） |
| `hailo_encoder/` | 硬體 H.264/H.265/JPEG 編碼器封裝 |
| `osd/` | OSD 疊加（FreeType 渲染文字、PNG 圖片） |
| `privacy_mask/` | 靜態多邊形遮罩 + AI 動態隱私遮罩 |
| `isp/` | ISP 控制（sensor 校準、AAA 自動演算法） |
| `hdr/` | HDR DoL 合併 |
| `config_manager/` | JSON Profile 管理與動態覆蓋（override 機制） |
| `buffer_pool/` | DMA Buffer Pool（zero-copy 共享記憶體） |
| `analytics_db/` | 時間戳索引的 Analytics 結果儲存（供 DPM 查詢） |

---

### 2. hailo-postprocess — AI 推論後處理庫

路徑：`hailo-media-library/hailo-postprocess/postprocesses/`

HailoRT 輸出 raw tensors → postprocess 解碼為結構化結果：

| 後處理模組 | 功能 |
|------------|------|
| `yolo_postprocess.cpp` | YOLO 系列 BBox 解碼（anchor-based / anchor-free） |
| `yolo_hailortpp.cpp` | 使用 HailortPP 優化路徑的 YOLO |
| `nms.cpp` | Non-Maximum Suppression |
| `mediapipe_landmarks_post.cpp` | MediaPipe 臉部/姿態 Landmark 後處理 |
| `linknet.cpp` | LinkNet 語義分割後處理 |
| `ocr_post.cpp` | OCR 文字辨識後處理 |
| `tensors.cpp` | Tensor 輔助工具（dequantize、reshape） |
| `clip.cpp` / `clip_gen.cpp` | CLIP 視覺語言模型後處理 |

---

### 3. hailo-analytics — Stage-Based Analytics Pipeline

路徑：`hailo-media-library/hailo-analytics/`

提供高階抽象，將 AI 推論、後處理、追蹤、編碼、輸出組合成可配置管線。

**Stage 基礎架構**（`hailo_analytics_api/include/hailo_analytics/pipeline/core/`）：

- `Stage`：所有處理單元的抽象基類，每個 Stage 有獨立執行緒 + Queue
- `Pipeline`：管理 Stage 的生命週期（start/stop/subscribe）
- `PipelineBuilder`：JSON 配置驅動的管線建構器
- `Buffer`：跨 Stage 傳遞的資料容器

**已實作 Stage 類型**：

| 類別 | Stage |
|------|-------|
| 來源 | `FrontendStage`、`GstSourceStage`、`FileSourceStage` |
| AI 推論 | `AiStage`（HailoRT 推論） |
| 後處理 | `PostprocessStage` |
| 追蹤 | `LightweightTrackerStage`、`TrackerTrafficCtrlStage` |
| 資料聚合 | `AggregatorStage`、`SyncAggregatorStage`、`MuxerStage`、`DemuxerStage` |
| 特效 | `BboxCropStage`、`TilingStage`、`OverlayStage` |
| 流量控制 | `ValveStage`、`FreezeStage`、`TeeStage` |
| 輸出 | `EncoderStage`、`GstSinkStage`、`AppSinkStage`、`WebSocketSinkStage`、`ZmqCommStage`、`UdpStage`、`RtpConverterStage` |
| Analytics | `AnalyticsDbStage`、`AnalyticMetadataPackagerStage` |

**高階應用配方**（`hailo_analytics_api/apps/`）：
- `vision.hpp`：AI 視覺檢測管線
- `detection.hpp`：物件偵測
- `face_landmarks.hpp`：臉部關鍵點
- `dpm_analytics.hpp`：動態隱私遮罩（DPM）
- `license_plate_recognition.hpp`：車牌辨識（LPR）

---

## 配置系統

JSON Profile 機制（`config_manager/`）：

```json
{
  "version": "1.0",
  "default_profile": "default",
  "profiles": [
    {
      "name": "default",
      "config_file": "frontend_config.json"
    }
  ]
}
```

每個 profile 包含：
- `sensor_config`：感測器驅動、解析度、幀率
- `iq_settings`：ISP IQ 設定（降噪、HDR、去畸變、AAA）
- `application_settings`：縮放、旋轉、翻轉、數字變焦
- `stabilizer_settings`：DIS/EIS/陀螺儀參數
- `encoded_output_streams`：各輸出流的編碼設定 + OSD + 隱私遮罩

`is_persistent` 機制：各設定結構有靜態標誌，控制哪些欄位在 override 時保留（防止設定被意外覆蓋）。

---

## 關鍵資料型別（`media_library_types.hpp`）

| 型別 | 說明 |
|------|------|
| `frontend_config_t` | 前端完整配置（LDC + Denoise + MultiResize + HDR + ISP） |
| `ldc_config_t` | LDC 子系統配置（dewarp + DIS + EIS + flip + rotate + optical zoom） |
| `output_resolution_t` | 輸出解析度（包含 crop/resize 尺寸、stream_id、framerate） |
| `Overlay / ImageOverlay / TextOverlay / DateTimeOverlay` | OSD 疊加元素 |
| `polygon / privacy_mask_config_t` | 隱私遮罩多邊形 |
| `media_library_return` | 統一錯誤碼（tl::expected 的 E 類型） |

---

## 小結

hailo-media-library 是一套**嵌入式 AI 視覺 SoC 的完整 Media SDK**：
- **底層**：直接操作 v4l2/DSP/HailoRT 硬體
- **中層**：JSON 驅動、Profile 管理、DMA Buffer Pool
- **高層**：Stage-based 可組合 Analytics Pipeline + GStreamer 整合
- **應用**：CCTV/IPC 智慧攝影機的 AI 視覺應用（物件偵測、人臉辨識、車牌辨識、隱私遮罩）
