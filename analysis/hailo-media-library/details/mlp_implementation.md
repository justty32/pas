# 在 Hailo 框架中實現 MLP 訓練與推論

## 前提說明

Hailo-15 的 NPU 執行已編譯的 `.hef` 模型。若需在 NPU 推論結果的基礎上，以 CPU 實作輕量的 MLP 後處理（如線性分類頭、線上微調），最正確的做法是在自訂的 `ThreadedStage` 中以純 C++20 實作。

**注意**：`hailo-analytics` 的 meson.build 不包含 xtensor 依賴。若要使用 xtensor，需自行在應用程式的 meson.build 中新增 `dependency('xtensor')`，並需安裝 `xtensor-blas`（提供 `xt::linalg`）。本文優先示範零外部依賴的純 C++ 方案。

---

## 1. 純 C++ MLP 推論實作

使用 `std::vector<float>` 實作矩陣乘法，無需額外依賴。

### 1.1 MLP 資料結構與前向傳播

```cpp
#include <vector>
#include <cmath>
#include <stdexcept>

// 單一全連接層（Y = X * W^T + B，然後套激活函數）
struct LinearLayer {
    std::vector<float> weights; // 形狀：[out_dim * in_dim]，row-major
    std::vector<float> bias;    // 形狀：[out_dim]
    int in_dim;
    int out_dim;

    // Y = X @ W^T + B（X: [1, in_dim]）
    std::vector<float> forward(const std::vector<float>& x) const {
        if ((int)x.size() != in_dim)
            throw std::invalid_argument("input size mismatch");
        std::vector<float> y(out_dim, 0.0f);
        for (int o = 0; o < out_dim; ++o) {
            for (int i = 0; i < in_dim; ++i)
                y[o] += x[i] * weights[o * in_dim + i];
            y[o] += bias[o];
        }
        return y;
    }
};

inline float relu(float x) { return x > 0.0f ? x : 0.0f; }
inline float sigmoid(float x) { return 1.0f / (1.0f + std::exp(-x)); }

// 兩層 MLP（隱藏層 + 輸出層）
class MLP {
public:
    LinearLayer hidden; // in_dim -> hidden_dim, ReLU
    LinearLayer output; // hidden_dim -> out_dim, Sigmoid

    std::vector<float> forward(const std::vector<float>& x) const {
        auto h = hidden.forward(x);
        for (auto& v : h) v = relu(v);
        auto y = output.forward(h);
        for (auto& v : y) v = sigmoid(v);
        return y;
    }
};
```

### 1.2 訓練步驟（SGD 反向傳播）

以二元分類為例，實作單步 SGD 更新。

```cpp
// 計算輸出層梯度並更新權重（BCE loss，已知誤差 delta = pred - label）
void sgd_update(LinearLayer& layer, const std::vector<float>& input,
                const std::vector<float>& delta, float lr) {
    // dW[o][i] = delta[o] * input[i]
    for (int o = 0; o < layer.out_dim; ++o) {
        for (int i = 0; i < layer.in_dim; ++i)
            layer.weights[o * layer.in_dim + i] -= lr * delta[o] * input[i];
        layer.bias[o] -= lr * delta[o];
    }
}
```

---

## 2. 整合至 Hailo Analytics Pipeline

將 MLP 封裝在繼承自 `ThreadedStage` 的自訂 Stage 中。

### 2.1 Include 路徑

```cpp
// hailo-analytics 核心
#include "hailo_analytics/pipeline/core/stage.hpp"
#include "hailo_analytics/pipeline/core/buffer.hpp"
// hailo-postprocess-tools（包含 HailoROI、HailoClassification 等）
#include "hailo_postprocess_tools/objects/hailo_objects.hpp"
#include "hailo_postprocess_tools/objects/hailo_common.hpp"
```

### 2.2 自訂 MLP Stage

```cpp
class MLPInferenceStage : public hailo_analytics::pipeline::ThreadedStage
{
public:
    MLPInferenceStage(std::string name, size_t queue_size)
        : hailo_analytics::pipeline::ThreadedStage(name, queue_size)
    {
        // 初始化權重（實際使用時應從檔案載入）
        m_mlp.hidden = {
            .weights = std::vector<float>(128 * 512, 0.01f), // 512 -> 128
            .bias    = std::vector<float>(128, 0.0f),
            .in_dim  = 512,
            .out_dim = 128
        };
        m_mlp.output = {
            .weights = std::vector<float>(1 * 128, 0.01f), // 128 -> 1
            .bias    = std::vector<float>(1, 0.0f),
            .in_dim  = 128,
            .out_dim = 1
        };
    }

    hailo_analytics::pipeline::AppStatus process(
        hailo_analytics::pipeline::BufferPtr data) override
    {
        HailoROIPtr roi = data->get_roi();

        // 安全取得 NPU 輸出 tensor（必須用 try/catch，get_tensor 不存在時拋例外）
        HailoTensorPtr npu_tensor;
        try {
            npu_tensor = roi->get_tensor("my_npu_embedding");
        } catch (const std::invalid_argument&) {
            // 沒有此 tensor，直接傳遞
            send_to_subscribers(data);
            return hailo_analytics::pipeline::AppStatus::SUCCESS;
        }

        // 將 uint8_t tensor 資料轉為 float（含反量化）
        std::vector<float> embedding(npu_tensor->size());
        for (uint32_t i = 0; i < npu_tensor->size(); ++i) {
            embedding[i] = npu_tensor->fix_scale(npu_tensor->data()[i]);
        }

        // MLP 推論
        auto pred = m_mlp.forward(embedding);
        float confidence = pred[0]; // 0~1

        // (可選) 線上訓練：需要 label 來源
        if (m_training_mode && m_label_source) {
            float label = m_label_source();
            // delta = pred - label（BCE 輸出層梯度），傳入 sgd_update 更新權重
            (void)label; // 完整反向傳播見 sgd_update，此處為示意
        }

        // 寫回推論結果
        roi->add_object(std::make_shared<HailoClassification>(
            "mlp_output",    // classification_type
            0,               // class_id
            "mlp_pred",      // label
            confidence       // confidence（必須在 0~1 之間）
        ));

        send_to_subscribers(data);
        return hailo_analytics::pipeline::AppStatus::SUCCESS;
    }

private:
    MLP m_mlp;
    bool m_training_mode = false;
    std::function<float()> m_label_source; // 外部標籤來源
};
```

### 2.3 Pipeline 組裝

```cpp
// 在 create_pipeline() 中加入自訂 Stage
auto mlp_stage = std::make_shared<MLPInferenceStage>("mlp_stage", 2);

pip_builder.add_stage(vision_pipeline, hailo_analytics::pipeline::StageType::SOURCE)
    .add_stage(npu_inference_pipeline)
    .add_stage(mlp_stage)
    .add_stage(overlay_pipeline, hailo_analytics::pipeline::StageType::SINK);

pip_builder.connect_frontend(VISION_PIPELINE, VISION_SINK, NPU_PIPELINE);
pip_builder.connect(NPU_PIPELINE, "mlp_stage");
pip_builder.connect("mlp_stage", OVERLAY_PIPELINE);
```

---

## 3. 關鍵 API 正誤對照表

| 項目 | ❌ 錯誤用法 | ✅ 正確用法 |
|------|-----------|-----------|
| tensor 取得 | `auto t = roi->get_tensor("x"); if (!t) ...` | `try { auto t = roi->get_tensor("x"); } catch (std::invalid_argument&) { ... }` |
| xtensor linalg | `xt::linalg::dot(a, b)` (需 xtensor-blas) | 純 C++ 矩陣乘法，或在 meson.build 手動加 xtensor-blas 依賴 |
| HailoClassification | `HailoClassification("t", 0.9f)` | `HailoClassification(type, label, confidence)` 或 `(type, class_id, label, confidence)` |
| confidence 範圍 | 任意 float | **必須 0.0~1.0**，否則 `assure_normal()` 拋例外 |

---

## 4. 儲存與載入權重

```cpp
// 以二進位格式儲存（float array）
void save_weights(const std::string& path, const LinearLayer& layer) {
    std::ofstream f(path, std::ios::binary);
    f.write(reinterpret_cast<const char*>(layer.weights.data()),
            layer.weights.size() * sizeof(float));
    f.write(reinterpret_cast<const char*>(layer.bias.data()),
            layer.bias.size() * sizeof(float));
}

void load_weights(const std::string& path, LinearLayer& layer) {
    std::ifstream f(path, std::ios::binary);
    f.read(reinterpret_cast<char*>(layer.weights.data()),
           layer.weights.size() * sizeof(float));
    f.read(reinterpret_cast<char*>(layer.bias.data()),
           layer.bias.size() * sizeof(float));
}
```
