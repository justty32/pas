# 教學：在 Hailo Pipeline 中實作 MLP 完整訓練流程

本文說明如何在 `hailo-analytics` 的 `ThreadedStage` 框架內，以純 C++20 實作一個具備完整反向傳播與 mini-batch 訓練能力的 MLP，並整合至影像串流 Pipeline 中進行線上（online）學習。

---

## 1. 問題設定

典型場景：Hailo NPU 的影像模型（如 MobileNet）輸出一個特徵向量（embedding），我們在其後接上一個可訓練的 MLP 分類頭，讓它學習識別特定類別（例如：依廠區特性訓練的異常偵測器）。

```
Camera
  │
  ▼
ISP (Frontend)
  │
  ▼
NPU Inference Stage        ← 產生 embedding tensor（固定，不訓練）
  │
  ▼
MLP Training/Inference Stage  ← 本文實作的目標
  │
  ▼
Output / Overlay
```

---

## 2. 數學原理（2 層 MLP）

### 前向傳播

```
z₁ = X · W₁ᵀ + b₁        （輸入層 → 隱藏層，維度：[1, hidden_dim]）
a₁ = ReLU(z₁)
z₂ = a₁ · W₂ᵀ + b₂       （隱藏層 → 輸出層，維度：[1, out_dim]）
a₂ = Sigmoid(z₂)          （輸出為機率）
```

### 損失函數（二元交叉熵，BCE）

```
L = -y · log(a₂) - (1-y) · log(1-a₂)
```

### 反向傳播（Chain Rule）

```
δ₂ = a₂ - y                        （sigmoid + BCE 合併後的輸出層梯度）
∂L/∂W₂ = δ₂ᵀ · a₁
∂L/∂b₂ = δ₂

δ₁ = (W₂ᵀ · δ₂) ⊙ ReLU'(z₁)       （傳回隱藏層，⊙ 為逐元素乘）
∂L/∂W₁ = δ₁ᵀ · X
∂L/∂b₁ = δ₁
```

### SGD 更新規則

```
W ← W - lr · ∂L/∂W
b ← b - lr · ∂L/∂b
```

---

## 3. C++ 完整實作

### 3.1 必要 Include

```cpp
#include <vector>
#include <cmath>
#include <random>
#include <fstream>
#include <stdexcept>
#include <numeric>
#include <algorithm>
#include <mutex>
#include <functional>  // std::function
#include <optional>    // std::optional
#include <iostream>    // std::cout（可替換為 spdlog）
```

### 3.2 LinearLayer：含反向傳播狀態

```cpp
struct LinearLayer {
    // 參數（row-major：weights[o * in_dim + i] 為第 o 個輸出神經元對第 i 個輸入的權重）
    std::vector<float> weights; // [out_dim * in_dim]
    std::vector<float> bias;    // [out_dim]
    int in_dim;
    int out_dim;

    // 反向傳播中間值（每次 forward 後保存，供 backward 使用）
    std::vector<float> last_input;  // [in_dim]
    std::vector<float> last_z;      // [out_dim]，線性輸出（激活前）

    // Xavier 初始化（適合 Sigmoid/Tanh），He 初始化（適合 ReLU）
    void init_xavier(std::mt19937& rng) {
        float limit = std::sqrt(6.0f / (in_dim + out_dim));
        std::uniform_real_distribution<float> dist(-limit, limit);
        weights.resize(out_dim * in_dim);
        bias.resize(out_dim, 0.0f);
        for (auto& w : weights) w = dist(rng);
    }

    void init_he(std::mt19937& rng) {
        float stddev = std::sqrt(2.0f / in_dim);
        std::normal_distribution<float> dist(0.0f, stddev);
        weights.resize(out_dim * in_dim);
        bias.resize(out_dim, 0.0f);
        for (auto& w : weights) w = dist(rng);
    }

    // 前向傳播（保存中間值以備反向傳播）
    std::vector<float> forward(const std::vector<float>& x) {
        last_input = x;
        last_z.assign(out_dim, 0.0f);
        for (int o = 0; o < out_dim; ++o) {
            for (int i = 0; i < in_dim; ++i)
                last_z[o] += x[i] * weights[o * in_dim + i];
            last_z[o] += bias[o];
        }
        return last_z;
    }

    // 反向傳播：接收輸出端傳回的梯度 delta（[out_dim]），回傳傳向輸入端的梯度（[in_dim]）
    std::vector<float> backward(const std::vector<float>& delta, float lr) {
        // 計算傳回上一層的梯度：∂L/∂x = Wᵀ · delta
        std::vector<float> grad_input(in_dim, 0.0f);
        for (int i = 0; i < in_dim; ++i)
            for (int o = 0; o < out_dim; ++o)
                grad_input[i] += weights[o * in_dim + i] * delta[o];

        // 更新權重：W -= lr * delta · xᵀ
        for (int o = 0; o < out_dim; ++o) {
            for (int i = 0; i < in_dim; ++i)
                weights[o * in_dim + i] -= lr * delta[o] * last_input[i];
            bias[o] -= lr * delta[o];
        }
        return grad_input;
    }
};
```

### 3.3 MLP：完整兩層網路

```cpp
inline float relu(float x)    { return x > 0.0f ? x : 0.0f; }
inline float relu_d(float x)  { return x > 0.0f ? 1.0f : 0.0f; } // ReLU 導數
inline float sigmoid(float x) { return 1.0f / (1.0f + std::exp(-x)); }

class MLP {
public:
    LinearLayer hidden; // 隱藏層
    LinearLayer output; // 輸出層

    // 以給定 seed 初始化（hidden 用 He，output 用 Xavier）
    void init(int in_dim, int hidden_dim, int out_dim, uint32_t seed = 42) {
        std::mt19937 rng(seed);
        hidden.in_dim  = in_dim;
        hidden.out_dim = hidden_dim;
        hidden.init_he(rng);

        output.in_dim  = hidden_dim;
        output.out_dim = out_dim;
        output.init_xavier(rng);
    }

    // 前向傳播（僅推論，不保存中間值）
    std::vector<float> predict(const std::vector<float>& x) const {
        // 隱藏層
        std::vector<float> z1(hidden.out_dim, 0.0f);
        for (int o = 0; o < hidden.out_dim; ++o) {
            for (int i = 0; i < hidden.in_dim; ++i)
                z1[o] += x[i] * hidden.weights[o * hidden.in_dim + i];
            z1[o] += hidden.bias[o];
        }
        std::vector<float> a1(hidden.out_dim);
        for (int o = 0; o < hidden.out_dim; ++o) a1[o] = relu(z1[o]);

        // 輸出層
        std::vector<float> z2(output.out_dim, 0.0f);
        for (int o = 0; o < output.out_dim; ++o) {
            for (int i = 0; i < output.in_dim; ++i)
                z2[o] += a1[i] * output.weights[o * output.in_dim + i];
            z2[o] += output.bias[o];
        }
        std::vector<float> a2(output.out_dim);
        for (int o = 0; o < output.out_dim; ++o) a2[o] = sigmoid(z2[o]);
        return a2;
    }

    // 訓練步（前向 + 反向 + 更新），回傳該樣本的 BCE loss
    float train_step(const std::vector<float>& x, const std::vector<float>& y_true, float lr) {
        // === 前向傳播 ===
        auto z1 = hidden.forward(x);
        std::vector<float> a1(z1.size());
        for (size_t i = 0; i < z1.size(); ++i) a1[i] = relu(z1[i]);

        auto z2 = output.forward(a1);
        std::vector<float> a2(z2.size());
        for (size_t i = 0; i < z2.size(); ++i) a2[i] = sigmoid(z2[i]);

        // === 計算 BCE loss ===
        float loss = 0.0f;
        const float eps = 1e-7f; // 避免 log(0)
        for (size_t i = 0; i < a2.size(); ++i)
            loss -= y_true[i] * std::log(a2[i] + eps) +
                    (1.0f - y_true[i]) * std::log(1.0f - a2[i] + eps);

        // === 反向傳播 ===
        // 輸出層梯度（sigmoid + BCE 合併）：δ₂ = a₂ - y
        std::vector<float> delta2(a2.size());
        for (size_t i = 0; i < a2.size(); ++i)
            delta2[i] = a2[i] - y_true[i];

        // 更新輸出層，取得傳回隱藏層的梯度
        auto grad_hidden = output.backward(delta2, lr);

        // 隱藏層梯度：乘以 ReLU 導數（∂L/∂z₁ = grad · ReLU'(z₁)）
        std::vector<float> delta1(grad_hidden.size());
        for (size_t i = 0; i < delta1.size(); ++i)
            delta1[i] = grad_hidden[i] * relu_d(z1[i]);

        // 更新隱藏層
        hidden.backward(delta1, lr);

        return loss;
    }
};
```

---

## 4. 訓練緩衝區（Mini-batch 支援）

線上訓練時，每幀資料立刻更新一次（batch_size=1）可能讓梯度過於嘈雜。使用緩衝區累積若干樣本後再批次更新。

```cpp
struct TrainingSample {
    std::vector<float> embedding; // NPU 輸出特徵向量
    std::vector<float> label;     // 訓練標籤（例如：{1.0f} 或 {0.0f}）
};

class TrainingBuffer {
public:
    explicit TrainingBuffer(size_t capacity) : m_capacity(capacity) {}

    void push(TrainingSample sample) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_buffer.push_back(std::move(sample));
        // 超出容量時丟棄最舊的樣本
        if (m_buffer.size() > m_capacity)
            m_buffer.erase(m_buffer.begin());
    }

    // 取出所有樣本並清空緩衝區（原子操作）
    std::vector<TrainingSample> drain() {
        std::lock_guard<std::mutex> lock(m_mutex);
        std::vector<TrainingSample> out;
        out.swap(m_buffer);
        return out;
    }

    size_t size() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_buffer.size();
    }

private:
    size_t m_capacity;
    mutable std::mutex m_mutex;
    std::vector<TrainingSample> m_buffer;
};
```

---

## 5. 整合至 Hailo Pipeline

### 5.1 MLPTrainingStage

```cpp
#include "hailo_analytics/pipeline/core/stage.hpp"
#include "hailo_analytics/pipeline/core/buffer.hpp"
#include "hailo_postprocess_tools/objects/hailo_objects.hpp"

class MLPTrainingStage : public hailo_analytics::pipeline::ThreadedStage
{
public:
    // train_every_n_samples：緩衝滿 N 個樣本後觸發一次 mini-batch 訓練
    MLPTrainingStage(std::string name, size_t queue_size,
                     int in_dim, int hidden_dim, int out_dim,
                     float lr = 0.001f, size_t train_every_n = 16)
        : hailo_analytics::pipeline::ThreadedStage(name, queue_size),
          m_buffer(train_every_n * 4), // 緩衝容量為觸發閾值的 4 倍（宣告順序在前，故初始化在前）
          m_lr(lr),
          m_train_threshold(train_every_n)
    {
        m_mlp.init(in_dim, hidden_dim, out_dim);
    }

    // 設定外部標籤來源（回呼函數，返回該 ROI 對應的 label vector）
    void set_label_provider(std::function<std::optional<std::vector<float>>(HailoROIPtr)> fn) {
        m_label_provider = std::move(fn);
    }

    hailo_analytics::pipeline::AppStatus process(
        hailo_analytics::pipeline::BufferPtr data) override
    {
        HailoROIPtr roi = data->get_roi();

        // 取得 NPU embedding tensor
        HailoTensorPtr tensor;
        try {
            tensor = roi->get_tensor("npu_embedding");
        } catch (const std::invalid_argument&) {
            send_to_subscribers(data);
            return hailo_analytics::pipeline::AppStatus::SUCCESS;
        }

        // 反量化為 float
        std::vector<float> embedding(tensor->size());
        for (uint32_t i = 0; i < tensor->size(); ++i)
            embedding[i] = tensor->fix_scale(tensor->data()[i]);

        // 推論（不論是否在訓練模式，都輸出預測結果）
        auto pred = m_mlp.predict(embedding);
        float confidence = std::max(0.0f, std::min(1.0f, pred[0]));
        roi->add_object(std::make_shared<HailoClassification>(
            "mlp_output", 0, "pred", confidence));

        // 若有標籤提供者，收集訓練樣本
        if (m_label_provider) {
            auto label_opt = m_label_provider(roi);
            if (label_opt.has_value()) {
                m_buffer.push({embedding, label_opt.value()});
            }
        }

        // 達到訓練閾值時執行 mini-batch 訓練
        if (m_buffer.size() >= m_train_threshold)
            run_training_batch();

        send_to_subscribers(data);
        return hailo_analytics::pipeline::AppStatus::SUCCESS;
    }

    // 主動觸發訓練（可在外部呼叫，用於收集完一輪資料後的批次訓練）
    void run_training_batch() {
        auto samples = m_buffer.drain();
        if (samples.empty()) return;

        float total_loss = 0.0f;
        int correct = 0;
        for (auto& s : samples) {
            float loss = m_mlp.train_step(s.embedding, s.label, m_lr);
            total_loss += loss;
            auto pred = m_mlp.predict(s.embedding);
            if ((pred[0] >= 0.5f) == (s.label[0] >= 0.5f)) ++correct;
        }

        float avg_loss = total_loss / samples.size();
        float acc = (float)correct / samples.size();
        m_epoch_loss = avg_loss;
        m_epoch_acc  = acc;

        // 可替換為 spdlog 等 logger
        std::cout << "[MLPTrainingStage] batch=" << samples.size()
                  << " loss=" << avg_loss << " acc=" << acc << "\n";
    }

    // 儲存權重
    void save_weights(const std::string& path) const {
        std::ofstream f(path, std::ios::binary);
        auto write_layer = [&](const LinearLayer& layer) {
            f.write(reinterpret_cast<const char*>(layer.weights.data()),
                    layer.weights.size() * sizeof(float));
            f.write(reinterpret_cast<const char*>(layer.bias.data()),
                    layer.bias.size() * sizeof(float));
        };
        write_layer(m_mlp.hidden);
        write_layer(m_mlp.output);
    }

    // 載入權重
    void load_weights(const std::string& path) {
        std::ifstream f(path, std::ios::binary);
        if (!f) throw std::runtime_error("Cannot open weights file: " + path);
        auto read_layer = [&](LinearLayer& layer) {
            f.read(reinterpret_cast<char*>(layer.weights.data()),
                   layer.weights.size() * sizeof(float));
            f.read(reinterpret_cast<char*>(layer.bias.data()),
                   layer.bias.size() * sizeof(float));
        };
        read_layer(m_mlp.hidden);
        read_layer(m_mlp.output);
    }

    float get_last_loss() const { return m_epoch_loss; }
    float get_last_acc()  const { return m_epoch_acc; }

private:
    MLP            m_mlp;
    TrainingBuffer m_buffer;          // 宣告順序決定初始化順序，必須在 m_lr 之前
    float          m_lr;
    size_t         m_train_threshold;
    float          m_epoch_loss = 0.0f;
    float          m_epoch_acc  = 0.0f;
    std::function<std::optional<std::vector<float>>(HailoROIPtr)> m_label_provider;
};
```

### 5.2 Pipeline 組裝範例

```cpp
void create_pipeline(std::shared_ptr<AppResources> res) {
    // ... vision_pipeline 與 npu_pipeline 建立省略（見 custom_stage 範例）

    // 建立 MLP 訓練 Stage
    // 參數：embedding 維度 512，隱藏層 128，輸出 1（二元分類），lr=0.001，每 32 樣本訓練一次
    auto mlp_stage = std::make_shared<MLPTrainingStage>(
        "mlp_training_stage", /*queue_size=*/4,
        /*in_dim=*/512, /*hidden_dim=*/128, /*out_dim=*/1,
        /*lr=*/0.001f, /*train_every_n=*/32);

    // 設定標籤來源（此處以固定值為例，實際應從外部服務或 UI 取得）
    mlp_stage->set_label_provider([](HailoROIPtr roi) -> std::optional<std::vector<float>> {
        auto detections = hailo_common::get_hailo_detections(roi);
        if (detections.empty()) return std::nullopt;
        // 範例：檢測到物件 → label=1，無物件 → label=0
        return std::vector<float>{1.0f};
    });

    // 嘗試載入已存在的權重
    try {
        mlp_stage->load_weights("/home/root/mlp_weights.bin");
        std::cout << "Loaded existing weights.\n";
    } catch (const std::exception&) {
        std::cout << "No existing weights, starting fresh.\n";
    }

    hailo_analytics::pipeline::PipelineBuilder pip_builder;
    pip_builder.add_stage(vision_pipeline, hailo_analytics::pipeline::StageType::SOURCE)
               .add_stage(npu_pipeline)
               .add_stage(mlp_stage)
               .add_stage(overlay_pipeline, hailo_analytics::pipeline::StageType::SINK);

    pip_builder.connect_frontend("vision_pipeline", "sink0", "npu_pipeline");
    pip_builder.connect("npu_pipeline", "mlp_training_stage");
    pip_builder.connect("mlp_training_stage", "overlay_pipeline");

    res->pipeline = pip_builder.build("mlp_training_app", true);
}
```

### 5.3 程式結束時儲存權重

```cpp
// 在 stop 之後呼叫
mlp_stage->save_weights("/home/root/mlp_weights.bin");
std::cout << "Weights saved.\n";
```

---

## 6. 訓練參數調整建議

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `lr`（學習率） | 0.001 | 太大導致振盪，太小收斂緩慢。建議從 0.01 開始，若 loss 震盪則降至 0.001 |
| `hidden_dim` | 128 | embedding 維度的 1/4 左右是合理起點 |
| `train_every_n` | 32 | 太小（如 1~4）梯度嘈雜；太大（如 256+）佔記憶體且更新慢 |
| 緩衝容量 | `4 × train_every_n` | 確保新舊樣本混合，避免過度擬合最近幾幀 |

---

## 7. 常見問題

**Q：loss 不下降**
- 確認 embedding 是否正確反量化（`fix_scale` 的 `qp_scale` 與 `qp_zp` 值）
- 確認標籤提供者回傳的值在 0~1 之間
- 嘗試提高學習率或減少隱藏層維度

**Q：confidence 輸出超出範圍導致 `assure_normal` 例外**
- `HailoClassification` 的 confidence 必須在 [0, 1]
- 程式碼已在加入前用 `std::max(0.0f, std::min(1.0f, pred[0]))` 截斷，確認此步驟未被省略

**Q：如何在不停機的情況下切換訓練/推論模式**
- 將 `m_label_provider` 設為 `nullptr` 即可停止收集樣本（推論繼續進行）
- `set_label_provider(nullptr)` 後 MLP 仍會輸出預測，只是不再更新權重
