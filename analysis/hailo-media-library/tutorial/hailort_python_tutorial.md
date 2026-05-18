# HailoRT Python API 實戰教學：MLP 推論篇

本教學旨在引導您使用 `hailort` Python 庫在硬體設備上執行 MLP（多層感知器）模型的推論。

---

## 1. 環境準備

### 安裝 HailoRT Python 擴展
通常 `hailort` 隨官方軟體包提供。您可以透過以下命令驗證或安裝（需對應您的 Python 版本）：
```bash
pip install hailort
```

### 準備模型 (HEF)
確保您已經使用 Hailo Dataflow Compiler (DFC) 將 MLP 的 ONNX 模型編譯為 `.hef` 檔案。

---

## 2. 基礎推論流程 (同步模式)

同步模式適合簡單的單幀處理，程式碼結構直觀。

```python
import numpy as np
from hailort import VDevice, HEF

# 1. 載入編譯好的 HEF 文件
hef_path = 'mlp_model.hef'
hef = HEF(hef_path)

# 2. 啟動虛擬設備 (VDevice)
# VDevice 會自動尋找可用的 Hailo 晶片 (PCIe 或 M.2)
with VDevice() as target:
    # 3. 根據 HEF 配置推論模型
    # 一個 HEF 可以包含多個網路，通常取第一個 [0]
    configure_params = target.create_configure_params(hef)
    network_group = target.configure(hef, configure_params)[0]
    
    # 4. 準備輸入與輸出虛擬流 (VStreams)
    input_vstream_params = network_group.make_input_vstream_params()
    output_vstream_params = network_group.make_output_vstream_params()
    
    with network_group.activate():
        with target.create_input_vstreams(network_group, input_vstream_params) as inputs, \
             target.create_output_vstreams(network_group, output_vstream_params) as outputs:
            
            # 5. 準備數據 (假設 MLP 輸入維度是 128)
            input_data = np.random.randn(1, 128).astype(np.float32)
            
            # 6. 執行推論
            inputs[0].write(input_data)
            result = outputs[0].read()
            
            print(f"推論成功！輸出維度: {result.shape}")
            print(f"結果範例: {result[0][:5]}")
```

---

## 3. 進階推論流程 (非同步模式)

非同步模式（Async）能發揮 Hailo 晶片的最大吞吐量，適合高頻率的推論任務。

```python
from hailort import VDevice, HEF
import numpy as np
import threading

def on_inference_complete(completion_info):
    """回調函數：當推論完成時被觸發"""
    if completion_info.status == 0:
        print("非同步推論完成！")

with VDevice() as target:
    hef = HEF('mlp_model.hef')
    
    # 使用 InferModel API (更現代且簡潔的推論介面)
    with target.create_infer_model(hef) as infer_model:
        # 設定 Batch Size
        infer_model.set_batch_size(1)
        
        with infer_model.configure() as configured_model:
            bindings = configured_model.create_bindings()
            
            # 準備輸入數據 Buffer
            input_data = np.random.randn(1, 128).astype(np.float32)
            bindings.input().set_buffer(input_data)
            
            # 啟動非同步推論
            job = configured_model.run_async(bindings, on_inference_complete)
            
            # 您可以在此處執行其他 CPU 任務
            # ...
            
            # 等待推論結束
            job.wait()
            
            # 獲取輸出
            output_buffer = bindings.output().get_buffer()
            print(f"非同步輸出結果: {output_buffer}")
```

---

## 4. 常見問題與技巧

### 1. 數據格式轉換
Hailo 硬體推論通常使用 `UINT8` 或 `UINT16` 以達到最高效能。
- 如果您的 HEF 包含量化資訊，Python API 會自動處理 `FLOAT32` 與 `UINT` 之間的轉換（Auto-scaling）。
- 確保輸入數據的 `dtype` 與 `bindings.input().type` 一致。

### 2. 多模型管理
如果您的應用需要同時運行多個 MLP，建議建立一個 `VDevice` 並配置多個 `InferModel`。
- **注意**: 資源競爭。如果 NPU 負載過高，請考慮調整 `scheduler_threshold`。

### 3. 獲取模型資訊
您可以透過 `hef` 對象查詢模型的輸入輸出名稱與維度：
```python
for input_info in hef.get_input_vstream_infos():
    print(f"Input Name: {input_info.name}, Shape: {input_info.shape}")
```

---

## 5. 總結
1.  **訓練**: 在 PC 使用 PyTorch，導出為 ONNX。
2.  **編譯**: 使用 DFC 編譯 ONNX 得到 **HEF**。
3.  **部署**: 使用 `hailort` Python API 在目標設備上載入 HEF 並執行推論。

本專案 (`hailo-media-library`) 中的 C++ 邏輯與此處的 Python 邏輯在硬體底層是完全對等的。您可以先用 Python 快速驗證 MLP 效果，再遷移到 C++ 以獲得更極致的系統效能。
