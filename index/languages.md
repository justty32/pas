# 程式語言 / 編譯器 / 代碼生成分析

> [← 回總索引 index.md](../index.md)。本檔收錄語言、編譯器與代碼生成器專案。

| 專案名稱 | 類型 | 分析深度 | 狀態 | 核心內容摘要 |
| :--- | :--- | :--- | :--- | :--- |
| **Hy (Lisp-Python)** | 程式語言 | 教學導向 (對齊 Hy 1.3.0) | 已深化 (2026-05-26) | 教學 11 篇 + answers/。已 clone Hy 1.3.0 源碼並 venv 實測；發現舊教學基於 0.x（`&rest`/舊 import/2-arg if/`with-decorator`/`async-defn`/錯誤重整表/把 hyrule 當核心 等多項已壞），全部對齊 1.3 重寫。重點深化 macro：05 重寫＋新增 11 進階篇（編譯期模型、`require` 機制、reader macro、`hy.R`/`hy.I`、核心 vs hyrule 速查、0.x→1.x 遷移表）。answers 含「Hy 能否跑 c-mera」（不行，附 Hy-mera 自製骨架）。 |
| **LispC** | 編譯器 | 教學導向 | 已遷移 | Lisp-to-C 轉換邏輯、宏系統與 C 語言嵌入教學。 |
| **C-mera** | 代碼生成器 | 高 (Architecture) | 已遷移 | 基於 Lisp 的 C/C++/CUDA 生成器、AST 轉換與宏系統分析。 |
