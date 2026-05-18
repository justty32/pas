# Hailo Python 應用開發指南：MLP 訓練與部署流程

經深入分析 `hailo-media-library` (特別是 `hailo-analytics/apps/clip`)，我們釐清了在 Python 環境下配合 Hailo 進行 MLP 任務的標準實作路徑。本專案中的 Python 主要扮演 **「模型準備與驗證」** 的角色。

---

## 1. 完整工作流：從 Python 訓練到硬體部署
在 Hailo 生態系中，Python 通常用於「離線」階段，而 C++ 用於「在線」高效能部署。

### 第一步：模型訓練與導出 (Python @ PC)
您可以使用 PyTorch 或 TensorFlow 訓練 MLP。本專案提供了一個 CLIP Text Encoder (本質上是帶有 Projection Layer 的 MLP) 的導出範例：
- **參考腳本**: `hailo-analytics/apps/clip/utils/clip_encoder_onnx/clip_text_encode_onnx_export.py`
- **核心操作**:
  ```python
  import torch
  import torch.nn as nn
  # 定義 MLP 並導出為 ONNX (Opset 14 建議)
  torch.onnx.export(model, dummy_input, "model.onnx", opset_version=14)
  ```

### 第二步：二進位權重提取 (Python @ PC)
對於某些特定架構（如 CLIP 的 Projection 層），專案建議將部分運算放在 CPU 執行以節省 NPU 資源，或是在 CPU 預處理。
- **參考腳本**: `clip_text_hailo_binary_export.py`
- **功能**: 從 ONNX 中提取特定的 Tensor 並存為 `.bin` 格式供 C++ `hailo-postprocess` 讀取。

### 第三步：編譯與部署 (DFC @ PC)
使用 **Hailo Dataflow Compiler (DFC)** 將 ONNX 編譯為 `.hef`。
- **注意**: 這是將 Python 產出的模型轉化為硬體可執行檔的關鍵步驟。

---

## 2. Python 推論與驗證 (Python @ PC/Device)
在部署到 C++ 之前，專案提供了 Python 腳本來驗證模型正確性。

### 使用 ONNX Runtime 進行初步驗證
- **參考腳本**: `clip_text_encoder_full_test.py`
- **功能**: 同時運行 PyTorch 原生模型與 ONNX 模型，對比每一層的輸出差異（Max Difference），確保轉換無損。

### 使用 HailoRT Python API (推薦推論方式)
雖然本專案未直接包含此類腳本，但這是官方推薦的 Python 推論路徑：
```python
from hailort import VDevice, HEF

# 載入 HEF
hef = HEF("mlp_model.hef")
with VDevice() as target:
    with target.create_infer_model("mlp_model.hef") as infer_model:
        # 推論邏輯...
```

---

## 3. 專案特有的 Python 依賴
如果您要運行本專案附帶的工具，需要安裝以下套件：
```bash
# 模型導出與測試
pip install torch torchvision onnx onnxruntime numpy
# CLIP 專用 (如果您參考 CLIP app)
pip install git+https://github.com/openai/CLIP.git open-clip-torch transformers
# 視覺化工具 ( analytic_viewer )
pip install PyGObject pycairo pyzmq msgpack pydantic
```

---

## 4. 關鍵錯誤修正 (與前一版本對比)
1.  **訓練地點**: 修正了「晶片上訓練」的誤導。Hailo 晶片**僅支援推論**，訓練必須在 Python 環境（PC）完成並編譯。
2.  **MLP 角色**: 在本專案中，MLP (如 CLIP 的 Projection 層) 有時被拆分：Transformer 部分在 NPU，最後的全連接層 (MLP) 在 CPU 以 C++ 實作（參考 `hailo-postprocess`）。

---

## 總結
對於您的需求：
1.  **訓練**: 請在 Python (PyTorch) 中完成，導出為 **ONNX**。
2.  **推論**: 
    - **快速驗證**: 使用 `onnxruntime`。
    - **硬體加速推論**: 使用 `hailort` Python API。
    - **高效能部署**: 參考本專案，將模型編譯為 **HEF**，並使用 C++ `AIStage` 整合進流水線。
