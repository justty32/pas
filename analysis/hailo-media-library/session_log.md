# Session Log - hailo-media-library

- 2026-05-11: 初始探索專案結構，確認包含 hailo-media-library, hailo-analytics, hailo-postprocess 三大模組。
- 2026-05-11: 建立分析目錄結構。
- 2026-05-11: 搜索 MLP 與訓練相關關鍵字，初步發現 codebase 主要集中於推論 (inference) 與媒體處理。
- 2026-05-11: 完成 C++ API 設計詳解文件 (`architecture/cpp_api_design.md`)。
- 2026-05-11: 完成 MLP 訓練與推論實作指南文件 (`details/mlp_implementation.md`)。
- 2026-05-11: 建立完整的專案建置教學文件 (`tutorial/mlp_cpp_project_setup.md`)，並全面優化為以「x86 PC 交叉編譯至 ARM」為主的開發工作流。
- 2026-05-11: [修正] 對照原始碼驗證既有分析，發現兩處嚴重錯誤：(1) `get_tensor()` 拋例外非回 nullptr；(2) tutorial 使用 CMake 而非 Meson。重寫 `details/mlp_implementation.md`（修正 API 用法、移除 xt::linalg）與 `tutorial/mlp_cpp_project_setup.md`（全面改寫為 Meson 三情境教學）。
- 2026-05-11: 建立 MLP 訓練完整教學文件 `tutorial/mlp_training_guide.md`，涵蓋：BCE 反向傳播數學、He/Xavier 權重初始化、mini-batch TrainingBuffer（mutex 安全）、完整 MLPTrainingStage 實作、Pipeline 組裝範例、訓練參數建議與常見問題。
- 2026-05-11: 建立 MLP 推論專案模板 `others/mlp_inference_template.md`，包含完整可用的 meson.build、mlp.hpp、mlp_stage.hpp、main.cpp 及 config 佔位符，提供裝置直接編譯與 x86 交叉編譯兩種情境。
