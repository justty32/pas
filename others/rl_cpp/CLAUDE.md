# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案定位

`rl_cpp` 是一個**從零手刻強化學習 (Reinforcement Learning) 的學習型專案**。
使用者的目標是**理解 RL**，不是做出生產級框架，也不是追求效能。

核心約束（由使用者明確指定）：
- **語言**：純 C++17。
- **相依**：零第三方相依 —— 連神經網路與自動微分都自己手刻（最硬核路線）。
  唯一允許的是 C++ 標準庫。**引入任何第三方庫前都要先問使用者。**
- **硬體**：純 CPU，**不使用 CUDA / GPU**。
- **路徑**：循序漸進走完整條課程，見 `ROADMAP.md`。

## 教學優先的工作準則

因為這是學習型專案，協助時請遵守：

1. **概念先講清楚再寫碼**：每段實作前，先用繁體中文說明「這在學什麼 RL 概念、
   為什麼這樣設計」。程式碼裡的註解也以「解釋概念」為主，不只是描述語法。
2. **看得到學習發生**：每個 milestone 都要有一支 `demos/*_demo.cpp`，跑出能對照
   課本或直覺的數字/曲線。沒有可觀察的結果就不算完成。
3. **不要過早抽象 / 不要替使用者跳關**：嚴格按 `ROADMAP.md` 的順序推進。不要為了
   「之後會用到」而預先加抽象層；介面要等到第二個使用者出現才抽出來（KISS）。
4. **小步前進**：一次專注一個 milestone，編譯通過、測試綠、demo 有結果，再往下走。

## 建置 / 執行 / 測試

```bash
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build -j

./build/rl_tests      # 單元測試（無框架，CHECK 巨集；exit code 非零代表失敗）
./build/bandit_demo   # M1 示範：重現 Sutton & Barto 圖 2.2
# 或用 ctest：
ctest --test-dir build
```

- 預設 build type 是 `Release`（示範程式跑大量蒙地卡羅實驗，Debug 會很慢）。
- 警告開到 `-Wall -Wextra -Wpedantic`（MSVC 為 `/W4`），應維持零警告。
- 每完成一個 milestone，把新的 `src/*.cpp` 加進 `CMakeLists.txt` 的 `RL_SOURCES`，
  新的 demo 用 `add_executable` 加上。

## 程式碼慣例

- 全部放在 `namespace rl`。
- 標頭在 `include/rl/`，實作在 `src/`，測試在 `tests/`，示範在 `demos/`。
- 亂數一律走 `rl::Rng`（`include/rl/rng.hpp`），明確指定 seed 以確保實驗可重現。
- 註解、文件、git commit、對使用者的回覆一律**繁體中文**；
  程式碼識別子、技術名詞、指令保留原文。

## 文件與留檔

- `ROADMAP.md`：完整學習路線圖與各 milestone 的概念/待辦（**唯一的進度真相來源**）。
- `progress.md`：逐次工作的流水帳（append 一句話）。
- 完成或修改一個 milestone 後，請同步更新 `ROADMAP.md` 的勾選狀態與 `progress.md`。

## 與上層 `pas/` 專案的關係

本資料夾位於 `pas/others/rl_cpp/`，與 `ai_core`、`gamecore` 並列為「原創自建」專案
（不是 `pas/projects/` 下被分析的外部克隆）。上層 `pas/CLAUDE.md` 的工作空間規範
（繁體中文輸出、程式碼標註位置）同樣適用，除非本檔另有指定。
