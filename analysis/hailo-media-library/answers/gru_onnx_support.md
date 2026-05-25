# 問題：Hailo 能把 GRU 相關的 ONNX 編譯成 Hailo 格式嗎？

## 結論（先說重點）

**直接答案：幾乎不行。** Hailo DFC（Dataflow Compiler）不支援 ONNX `GRU` 算子作為一等公民的硬體運算。

但有三條迂迴路線，視情況可行。

---

## 背景：兩個層次的區別

這個問題涉及兩個完全不同的工具，需要先釐清：

| 工具 | 職責 | 位置 |
|------|------|------|
| **Hailo DFC（Dataflow Compiler）** | 將 ONNX → HEF（Hailo Execution Format），離線編譯，在 PC 上執行 | 獨立工具，**不在此 repo** |
| **hailo-media-library（此 repo）** | 執行期 Media Pipeline + 後處理，呼叫 HailoRT 載入 HEF 進行推論 | 本 repo |

本 repo 的 codebase 搜尋結果：**零筆 GRU/LSTM/RNN 相關代碼**（只有 "grunter" 一字包含 gru 子字串）。  
所有後處理模組（YOLO、NMS、Segmentation、Landmarks、OCR、CLIP）均為純 CNN 前向推論。

---

## 為何 GRU 難以在 Hailo 上執行

### 1. 硬體架構差異

Hailo 晶片（Hailo-8、Hailo-15）是為**密集並行的 CNN 矩陣計算**優化的 NPU：
- 核心是大型矩陣乘法陣列（MAC arrays）+ 激活函數硬體加速
- 記憶體架構針對 feature map 的空間讀取模式設計
- 不支援任意形狀的有狀態計算圖（stateful graph with temporal dependency）

GRU 的核心問題是**時序依賴（temporal dependency）**：

```
# GRU 偽碼
h_t = f(h_{t-1}, x_t)   # 每個時間步都需要上一步的隱藏狀態
```

這個 `h_{t-1} → h_t` 的回饋迴路，無法直接映射到純前向推論的 NPU 執行模型。

### 2. DFC 算子支援

Hailo DFC 3.x 的 ONNX 算子支援清單（官方文件）：

**支援的基本算子（與 GRU 組成相關的）**：
- `MatMul`、`Gemm`
- `Sigmoid`、`Tanh`
- `Add`、`Mul`（element-wise）
- `Reshape`、`Squeeze`、`Unsqueeze`
- `Concat`、`Split`

**不支援的算子**：
- ONNX `GRU` 算子（fused 版本）
- ONNX `LSTM` 算子
- ONNX `RNN` 算子
- `Loop`、`Scan`（任何動態迴圈結構）

---

## 三條可能的迂迴路線

### 路線 A：將 GRU 展開（Unroll）為基本算子

**原理**：ONNX GRU 算子可以「展開」成一系列 MatMul + Sigmoid + Tanh + Add + Mul，  
如果序列長度固定（例如固定 T=16 時間步），則可完全展開成靜態圖。

```python
# PyTorch 導出技巧：不使用 nn.GRU，而是手動展開
class UnrolledGRU(nn.Module):
    def __init__(self, input_size, hidden_size, seq_len):
        super().__init__()
        self.cells = nn.ModuleList([
            GRUCell(input_size, hidden_size) for _ in range(seq_len)
        ])
    
    def forward(self, x, h0):
        # x: [batch, seq_len, input_size]
        h = h0
        outputs = []
        for i, cell in enumerate(self.cells):
            h = cell(x[:, i, :], h)
            outputs.append(h)
        return torch.stack(outputs, dim=1), h

# 這樣導出的 ONNX 不含 GRU 算子，只有基本算子
torch.onnx.export(model, ...)
```

**限制**：
- 序列長度必須固定（不能動態）
- 展開後模型尺寸線性成長（T=100 → 100x 參數量）
- DFC 可能仍有最大算子數限制

**可行性**：中等（短序列、固定長度時可行）

---

### 路線 B：使用 Hailo 的 Loopback（回饋）機制

**原理**：hailo-media-library 的**降噪模組**（`src/denoise_config_t`）正是使用這種模式——  
CNN 的輸出回饋到下一幀的輸入（`feedback_y_channel`、`feedback_uv_channel`）。  
這本質上是「外部狀態管理」的 RNN 近似。

```
Frame N:
  [input_frame_N, hidden_state_N-1] → HEF 推論 → [output_N, hidden_state_N]

Frame N+1:
  [input_frame_N+1, hidden_state_N] → HEF 推論 → [output_N+1, hidden_state_N+1]
```

**代碼參考**（`media_library_types.hpp:248-263`）：
```cpp
struct feedback_network_config_t {
    std::string network_path;
    std::string y_channel;
    std::string uv_channel;
    std::string feedback_y_channel;    // ← 上一幀 Y 輸出回饋
    std::string feedback_uv_channel;   // ← 上一幀 UV 輸出回饋
    std::string output_y_channel;
    std::string output_uv_channel;
};
```

**實作方式**：
1. 將 GRU 的 hidden state 視為 buffer，在 CPU 側管理
2. 每個推論周期：把 hidden state concat 到 input，送入 HEF
3. 推論完成後，從輸出提取新的 hidden state，存回 buffer

**限制**：
- 隱藏狀態需在 CPU 複製（每幀一次），有延遲
- 需要自行管理狀態 buffer
- 適合時序不太密集的場景（如每幀更新一次的 detection + tracking）

**可行性**：高（需額外工程，但可行）

---

### 路線 C：用 Temporal CNN 替代 GRU

**原理**：大多數 GRU 應用（語音、動作識別、時序分析）可以用 TCN（Temporal Convolutional Network）替代，  
TCN 完全由 1D/2D Conv 組成，Hailo 完整支援。

```
GRU → TCN (dilated 1D Conv + residual) → 幾乎同等精度，完整 Hailo 支援
```

**可行性**：最高（但需重新訓練模型）

---

## 實際驗證建議

若要確認特定 GRU ONNX 是否可編譯，最直接的方法：

```bash
# 安裝 Hailo DFC（需 Hailo Developer Zone 帳號）
pip install hailo_sdk_client

# 嘗試解析 ONNX 模型
from hailo_sdk_client import ClientRunner
runner = ClientRunner(hw_arch="hailo15")
runner.translate_onnx_model("your_gru_model.onnx")
# 若出現 "Unsupported layer type: GRU" 即確認不支援
```

---

## 參考資源

- Hailo Developer Zone → Model Zoo → DFC Operator Support Matrix（需登入）
- `hailo-media-library` denoise 模組：`media_library/src/denoise_config_t` — Loopback 機制範例
- Hailo 官方討論區：GRU 相關討論（社群多次確認 fused GRU 不支援）
