# 專案模板：Hailo C++ MLP 推論應用

本模板提供一個可直接使用的 C++ 專案骨架，基於 `hailo-analytics` 框架實作 MLP 推論 Stage。  
使用者僅需替換 **embedding tensor 名稱**、**MLP 維度**與**權重檔路徑**即可整合至實際流水線。

---

## 專案目錄結構

```text
hailo_mlp_inference/
├── meson.build
├── hailo_cross.ini          ← 交叉編譯設定（僅 x86 開發時需要）
├── src/
│   ├── main.cpp
│   ├── mlp.hpp              ← MLP 資料結構與推論邏輯（純 C++，零外部依賴）
│   └── mlp_stage.hpp        ← MLPInferenceStage（ThreadedStage 子類別）
└── config/
    └── medialib_config.json ← 從裝置複製或參考官方範例
```

---

## `meson.build`

```meson
project('hailo-mlp-inference', 'cpp',
    version : '1.0.0',
    default_options : ['cpp_std=c++20', 'warning_level=2'])

# hailo-analytics 的 pkg-config 已涵蓋所有傳遞依賴
# （hailo-medialib、hailo-postprocess-tools、hailort、GStreamer、OpenCV 等）
hailo_analytics_dep = dependency('hailo-analytics', method : 'pkg-config')

executable('hailo_mlp_inference',
    ['src/main.cpp'],
    dependencies : [hailo_analytics_dep],
    install : true,
)
```

---

## `hailo_cross.ini`（x86 交叉編譯用）

```ini
[binaries]
c         = 'aarch64-linux-gnu-gcc'
cpp       = 'aarch64-linux-gnu-g++'
ar        = 'aarch64-linux-gnu-ar'
strip     = 'aarch64-linux-gnu-strip'
pkgconfig = 'pkg-config'

[properties]
sys_root          = '/path/to/hailo_sdk/sysroot'
pkg_config_libdir = '/path/to/hailo_sdk/sysroot/usr/lib/pkgconfig'

[host_machine]
system     = 'linux'
cpu_family = 'aarch64'
cpu        = 'cortex-a55'
endian     = 'little'
```

---

## `src/mlp.hpp`

```cpp
#pragma once

#include <vector>
#include <cmath>
#include <random>
#include <fstream>
#include <stdexcept>
#include <string>

// ============================================================
// 全連接層（僅推論，不保存反向傳播狀態）
// ============================================================
struct LinearLayer {
    std::vector<float> weights; // [out_dim * in_dim]，row-major
    std::vector<float> bias;    // [out_dim]
    int in_dim  = 0;
    int out_dim = 0;

    // He 初始化（適合 ReLU 激活層）
    void init_he(int in, int out, std::mt19937& rng) {
        in_dim  = in;
        out_dim = out;
        float stddev = std::sqrt(2.0f / in_dim);
        std::normal_distribution<float> dist(0.0f, stddev);
        weights.resize(out_dim * in_dim);
        bias.assign(out_dim, 0.0f);
        for (auto& w : weights) w = dist(rng);
    }

    // Xavier 初始化（適合 Sigmoid/Tanh 激活層）
    void init_xavier(int in, int out, std::mt19937& rng) {
        in_dim  = in;
        out_dim = out;
        float limit = std::sqrt(6.0f / (in_dim + out_dim));
        std::uniform_real_distribution<float> dist(-limit, limit);
        weights.resize(out_dim * in_dim);
        bias.assign(out_dim, 0.0f);
        for (auto& w : weights) w = dist(rng);
    }

    // 前向傳播：Y = X @ W^T + b
    std::vector<float> forward(const std::vector<float>& x) const {
        std::vector<float> y(out_dim, 0.0f);
        for (int o = 0; o < out_dim; ++o) {
            for (int i = 0; i < in_dim; ++i)
                y[o] += x[i] * weights[o * in_dim + i];
            y[o] += bias[o];
        }
        return y;
    }
};

// ============================================================
// 激活函數
// ============================================================
inline float relu(float x)    { return x > 0.0f ? x : 0.0f; }
inline float sigmoid(float x) { return 1.0f / (1.0f + std::exp(-x)); }

// ============================================================
// 兩層 MLP（隱藏層 ReLU + 輸出層 Sigmoid）
// ============================================================
class MLP {
public:
    LinearLayer hidden;
    LinearLayer output;

    // 以隨機初始化建立 MLP（in_dim → hidden_dim → out_dim）
    void init(int in_dim, int hidden_dim, int out_dim, uint32_t seed = 42) {
        std::mt19937 rng(seed);
        hidden.init_he(in_dim, hidden_dim, rng);
        output.init_xavier(hidden_dim, out_dim, rng);
    }

    // 推論：回傳每個輸出節點的機率（0~1）
    std::vector<float> predict(const std::vector<float>& x) const {
        auto z1 = hidden.forward(x);
        std::vector<float> a1(z1.size());
        for (size_t i = 0; i < z1.size(); ++i) a1[i] = relu(z1[i]);

        auto z2 = output.forward(a1);
        std::vector<float> a2(z2.size());
        for (size_t i = 0; i < z2.size(); ++i) a2[i] = sigmoid(z2[i]);
        return a2;
    }

    // 從二進位檔載入權重（配合 save_weights 使用）
    void load_weights(const std::string& path) {
        std::ifstream f(path, std::ios::binary);
        if (!f) throw std::runtime_error("Cannot open weights: " + path);
        auto read_layer = [&](LinearLayer& layer) {
            f.read(reinterpret_cast<char*>(layer.weights.data()),
                   layer.weights.size() * sizeof(float));
            f.read(reinterpret_cast<char*>(layer.bias.data()),
                   layer.bias.size() * sizeof(float));
        };
        read_layer(hidden);
        read_layer(output);
    }

    // 儲存權重至二進位檔
    void save_weights(const std::string& path) const {
        std::ofstream f(path, std::ios::binary);
        if (!f) throw std::runtime_error("Cannot write weights: " + path);
        auto write_layer = [&](const LinearLayer& layer) {
            f.write(reinterpret_cast<const char*>(layer.weights.data()),
                    layer.weights.size() * sizeof(float));
            f.write(reinterpret_cast<const char*>(layer.bias.data()),
                    layer.bias.size() * sizeof(float));
        };
        write_layer(hidden);
        write_layer(output);
    }
};
```

---

## `src/mlp_stage.hpp`

```cpp
#pragma once

#include "mlp.hpp"

#include <string>
#include <vector>
#include <stdexcept>
#include <algorithm>  // std::max, std::min

// hailo-analytics 核心
#include "hailo_analytics/pipeline/core/stage.hpp"
#include "hailo_analytics/pipeline/core/buffer.hpp"
// hailo-postprocess-tools（HailoROI、HailoClassification 等）
#include "hailo_postprocess_tools/objects/hailo_objects.hpp"

// ============================================================
// MLPInferenceStage
//
// 從 ROI 的 NPU 輸出 tensor 取得 embedding，送入 MLP 推論，
// 將結果以 HailoClassification 附回 ROI 並傳遞給下游 Stage。
//
// 使用方式：
//   1. 建構時指定 embedding tensor 名稱、MLP 維度
//   2. 呼叫 load_weights() 載入訓練好的權重
//   3. 加入 PipelineBuilder 即可
// ============================================================
class MLPInferenceStage : public hailo_analytics::pipeline::ThreadedStage
{
public:
    // tensor_name  : NPU 輸出的 tensor 名稱（需與 .hef 模型輸出名稱一致）
    // in_dim       : embedding 維度（必須與模型輸出一致）
    // hidden_dim   : MLP 隱藏層維度
    // out_dim      : 輸出類別數（二元分類=1）
    // queue_size   : 此 Stage 的輸入佇列大小
    MLPInferenceStage(std::string name,
                      std::string tensor_name,
                      int in_dim, int hidden_dim, int out_dim,
                      size_t queue_size = 4)
        : hailo_analytics::pipeline::ThreadedStage(name, queue_size),
          m_tensor_name(std::move(tensor_name))
    {
        m_mlp.init(in_dim, hidden_dim, out_dim);
    }

    // 載入訓練好的權重（在 Pipeline 啟動前呼叫）
    void load_weights(const std::string& path) {
        m_mlp.load_weights(path);
    }

    hailo_analytics::pipeline::AppStatus process(
        hailo_analytics::pipeline::BufferPtr data) override
    {
        HailoROIPtr roi = data->get_roi();

        // 安全取得 NPU tensor（get_tensor 找不到時拋例外，不回傳 nullptr）
        HailoTensorPtr tensor;
        try {
            tensor = roi->get_tensor(m_tensor_name);
        } catch (const std::invalid_argument&) {
            // 此幀沒有目標 tensor，直接傳遞給下游
            send_to_subscribers(data);
            return hailo_analytics::pipeline::AppStatus::SUCCESS;
        }

        // 將量化 uint8 tensor 反量化為 float embedding
        std::vector<float> embedding(tensor->size());
        for (uint32_t i = 0; i < tensor->size(); ++i)
            embedding[i] = tensor->fix_scale(tensor->data()[i]);

        // MLP 推論
        auto pred = m_mlp.predict(embedding);

        // 將每個輸出節點的結果附回 ROI
        // confidence 必須在 [0, 1]（HailoClassification 內部會呼叫 assure_normal）
        for (int o = 0; o < static_cast<int>(pred.size()); ++o) {
            float confidence = std::max(0.0f, std::min(1.0f, pred[o]));
            roi->add_object(std::make_shared<HailoClassification>(
                "mlp_output",                        // classification_type
                o,                                   // class_id
                "class_" + std::to_string(o),        // label
                confidence                           // confidence，必須 0~1
            ));
        }

        send_to_subscribers(data);
        return hailo_analytics::pipeline::AppStatus::SUCCESS;
    }

private:
    MLP         m_mlp;
    std::string m_tensor_name;
};
```

---

## `src/main.cpp`

```cpp
#include <iostream>
#include <fstream>
#include <stdexcept>
#include <mutex>
#include <condition_variable>
#include <chrono>

#include <tl/expected.hpp>
#include <cxxopts/cxxopts.hpp>

#include "media_library/signal_utils.hpp"
#include "hailo_analytics/analytics/vision.hpp"
#include "hailo_analytics/analytics/detection.hpp"
#include "hailo_analytics/analytics/overlay.hpp"
#include "hailo_analytics/logger/hailo_analytics_logger.hpp"
#include "hailo_analytics/pipeline/core/pipeline_builder.hpp"

#include "mlp_stage.hpp"

// ============================================================
// 使用者設定區：依實際情況修改以下常數
// ============================================================
#define APP_NAME          "hailo_mlp_inference"
#define VISION_PIPELINE   "vision_pipeline"
#define DETECTION_PIPELINE "detection_pipeline"
#define MLP_STAGE_NAME    "mlp_stage"
#define OVERLAY_PIPELINE  "overlay_pipeline"
#define VISION_SINK       "sink0"

// NPU 模型輸出的 embedding tensor 名稱（與 .hef 輸出層名稱一致）
#define EMBEDDING_TENSOR_NAME "output_layer"

// MLP 維度（需與訓練時一致）
constexpr int MLP_IN_DIM     = 512;
constexpr int MLP_HIDDEN_DIM = 128;
constexpr int MLP_OUT_DIM    = 1;   // 二元分類

// 預設路徑
#define DEFAULT_MEDIALIB_CONFIG "/etc/imaging/cfg/medialib_configs/case_studies/detection_medialib_config.json"
#define DEFAULT_WEIGHTS_PATH    "/home/root/mlp_weights.bin"
#define DEFAULT_HOST_IP         "10.0.0.2"
// ============================================================

struct AppResources {
    std::shared_ptr<MediaLibrary>                  media_library;
    hailo_analytics::pipeline::PipelinePtr         pipeline;
    std::shared_ptr<MLPInferenceStage>             mlp_stage;
    std::string medialib_config_path = DEFAULT_MEDIALIB_CONFIG;
    std::string weights_path         = DEFAULT_WEIGHTS_PATH;
    std::string host_ip              = DEFAULT_HOST_IP;
};

static std::string read_file(const std::string& path) {
    std::ifstream f(path);
    if (!f) throw std::runtime_error("Cannot open file: " + path);
    return {std::istreambuf_iterator<char>(f), {}};
}

void configure_media_library(std::shared_ptr<AppResources> res) {
    auto expected = MediaLibrary::create();
    if (!expected.has_value())
        throw std::runtime_error("Failed to create MediaLibrary");
    res->media_library = expected.value();

    auto config_str = read_file(res->medialib_config_path);
    if (res->media_library->initialize(config_str) != media_library_return::MEDIA_LIBRARY_SUCCESS)
        throw std::runtime_error("Failed to initialize MediaLibrary");
}

void create_pipeline(std::shared_ptr<AppResources> res) {
    // Vision pipeline（ISP + 攝影機輸入）
    hailo_analytics::analytics::vision::vision_config_t vision_cfg;
    auto vision_result = hailo_analytics::analytics::vision::generate_vision_pipeline(
        *res->media_library, VISION_PIPELINE, vision_cfg);
    if (!vision_result.has_value())
        throw std::runtime_error("Failed to create vision pipeline");

    // Detection pipeline（NPU 推論，產生 embedding tensor）
    auto detection_result = hailo_analytics::analytics::detection::generate_detection_pipeline(
        DETECTION_PIPELINE);
    if (!detection_result.has_value())
        throw std::runtime_error("Failed to create detection pipeline");

    // MLP Inference Stage
    res->mlp_stage = std::make_shared<MLPInferenceStage>(
        MLP_STAGE_NAME,
        EMBEDDING_TENSOR_NAME,
        MLP_IN_DIM, MLP_HIDDEN_DIM, MLP_OUT_DIM);

    // 嘗試載入已訓練的權重（若不存在則使用隨機初始化）
    try {
        res->mlp_stage->load_weights(res->weights_path);
        std::cout << "[main] Loaded MLP weights from: " << res->weights_path << "\n";
    } catch (const std::exception& e) {
        std::cout << "[main] No weights found (" << e.what() << "), using random init.\n";
    }

    // Overlay pipeline（結果視覺化輸出）
    auto overlay_result = hailo_analytics::analytics::overlay::generate_overlay_pipeline(
        res->media_library->m_encoders[VISION_SINK], OVERLAY_PIPELINE);
    if (!overlay_result.has_value())
        throw std::runtime_error("Failed to create overlay pipeline");

    // 組裝 Pipeline
    hailo_analytics::pipeline::PipelineBuilder builder;
    builder.add_stage(vision_result.value(),    hailo_analytics::pipeline::StageType::SOURCE)
           .add_stage(detection_result.value())
           .add_stage(res->mlp_stage)
           .add_stage(overlay_result.value(),   hailo_analytics::pipeline::StageType::SINK);

    builder.connect_frontend(VISION_PIPELINE, VISION_SINK, DETECTION_PIPELINE);
    builder.connect(DETECTION_PIPELINE, MLP_STAGE_NAME);
    builder.connect(MLP_STAGE_NAME,     OVERLAY_PIPELINE);

    res->pipeline = builder.build(APP_NAME, true);
}

std::mutex              g_stop_mutex;
std::condition_variable g_stop_cv;

int main(int argc, char* argv[]) {
    // 命令列參數解析
    cxxopts::Options opts(APP_NAME);
    opts.add_options()
        ("h,help",    "Show help")
        ("t,timeout", "Run duration (seconds)", cxxopts::value<int>()->default_value("60"))
        ("c,config",  "MediaLibrary config path",
            cxxopts::value<std::string>()->default_value(DEFAULT_MEDIALIB_CONFIG))
        ("w,weights", "MLP weights binary path",
            cxxopts::value<std::string>()->default_value(DEFAULT_WEIGHTS_PATH))
        ("o,host-ip", "UDP output host IP",
            cxxopts::value<std::string>()->default_value(DEFAULT_HOST_IP));

    auto result = opts.parse(argc, argv);
    if (result.count("help")) { std::cout << opts.help(); return 0; }

    auto res = std::make_shared<AppResources>();
    res->medialib_config_path = result["config"].as<std::string>();
    res->weights_path         = result["weights"].as<std::string>();
    res->host_ip              = result["host-ip"].as<std::string>();
    int timeout               = result["timeout"].as<int>();

    // SIGINT 處理
    signal_utils::SignalHandler sig(false);
    sig.register_signal_handler([]([[maybe_unused]] int) {
        g_stop_cv.notify_all();
    });

    try {
        configure_media_library(res);
        create_pipeline(res);

        std::cout << "[main] Starting pipeline...\n";
        res->pipeline->start();

        std::unique_lock<std::mutex> lk(g_stop_mutex);
        g_stop_cv.wait_for(lk, std::chrono::seconds(timeout));

        std::cout << "[main] Stopping pipeline...\n";
        res->pipeline->stop();
    } catch (const std::exception& e) {
        std::cerr << "[main] Fatal error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
```

---

## `config/medialib_config.json`（佔位符，需替換為裝置實際設定）

```json
{
    "version": "2.0.0",
    "metadata": {
        "architecture": "hailo15h",
        "description": "MLP inference template config"
    },
    "backup_folder_path": "",
    "default_profile": "Daylight",
    "profiles": [
        {
            "config_file": "/usr/bin/profile/profile.json",
            "name": "Daylight"
        }
    ]
}
```

> **注意**：實際部署時，請從 Hailo 裝置的 `/etc/imaging/cfg/` 複製對應的設定檔，本 JSON 僅作格式示意。

---

## 建置與執行

### 情境 A：在 Hailo 裝置上直接編譯

```bash
cd hailo_mlp_inference/
meson setup builddir
ninja -C builddir
./builddir/hailo_mlp_inference --config config/medialib_config.json \
                               --weights /home/root/mlp_weights.bin \
                               --timeout 120
```

### 情境 B：x86 PC 交叉編譯

```bash
cd hailo_mlp_inference/
meson setup builddir --cross-file hailo_cross.ini
ninja -C builddir

# 部署
scp builddir/hailo_mlp_inference root@hailo-device.local:/home/root/
scp -r config/ root@hailo-device.local:/home/root/
```

---

## 使用者必須修改的地方

| 位置 | 常數/參數 | 說明 |
|------|-----------|------|
| `main.cpp` | `EMBEDDING_TENSOR_NAME` | NPU 模型輸出 tensor 名稱，需與 `.hef` 一致 |
| `main.cpp` | `MLP_IN_DIM` | 必須等於 NPU embedding 的元素數量 |
| `main.cpp` | `MLP_HIDDEN_DIM` | 依訓練時設定調整 |
| `main.cpp` | `MLP_OUT_DIM` | 二元分類=1，多類分類=N |
| `main.cpp` | `DEFAULT_WEIGHTS_PATH` | 訓練好的權重檔路徑 |
| `main.cpp` | `DEFAULT_MEDIALIB_CONFIG` | 裝置實際設定檔路徑 |
| `mlp_stage.hpp` | `"class_" + to_string(o)` | 替換為實際的類別標籤名稱 |
