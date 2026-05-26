# Hymera

Hy 寫的 c-mera 風格 C/C++ 程式碼生成器。

> ⚠️ 目前處於**設計階段**。實作尚未開始。詳細目標、設計文件與進度請看 [`PROJECT.md`](PROJECT.md)。

## 一句話

用 S-expression（Hy 語法）寫程式碼，生成你要的 C 或 C++ 原始碼，跨平台、可被任何 C/C++ 編譯器接受。

## 從這裡開始讀

1. [`PROJECT.md`](PROJECT.md) — 衍生目標、範圍、完成定義
2. [`docs/01_architecture.md`](docs/01_architecture.md) — 三層架構總覽
3. [`docs/02_ast_shape.md`](docs/02_ast_shape.md) 起 — 各層設計細節

## 為什麼不直接用 c-mera？

見 [`../../analysis/hy/answers/hy_run_cmera.md`](../../analysis/hy/answers/hy_run_cmera.md)。簡言之：c-mera 是 SBCL/CLOS/Quicklisp 棧，Hy 跑不了；但設計概念可以完整移植，並換到 Python 生態系。
