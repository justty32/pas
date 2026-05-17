# Wesnoth 進階分析計畫 (Advanced Analysis Plan)

為了達成「更深入、更全面」的目標，我們將分析路徑延伸至底層工程細節與系統交互作用。

## 階段一：底層同步與確定性 (Level 7)
**目標**: 理解 Wesnoth 如何在跨平台環境下維持完全一致的遊戲狀態。
- **網路協議分析**: 解構 `src/network_asio.cpp` 與 `src/wesnothd_connection.cpp`。
- **確定性模擬**: 追蹤隨機數種子 (RNG Seed) 如何在 `actions/attack.cpp` 中被精確使用以支援重播 (Replay)。
- **同步檢查 (Synced Checkup)**: 分析 `src/synced_checkup.hpp` 如何檢測並處理 OOS (Out of Sync)。

## 階段二：視窗系統與圖形管線 (Level 8)
**目標**: 解構 Wesnoth 自研的 GUI2 框架與渲染流程。
- **GUI2 佈局引擎**: 研究 `src/gui/core/` 如何實現基於 WML 的動態 UI 佈局。
- **高品質渲染**: 分析 Pango 與 Cairo 在 `src/font/` 與 `src/draw.cpp` 中的整合。
- **動畫元件系統**: 研究 `src/units/animation_component.cpp` 如何處理多層次的單位動畫。

## 階段三：WML 預處理器之秘 (Level 9)
**目標**: 深入研究這套驅動整個遊戲的「DSL (領域專屬語言)」。
- **宏展開深度剖析**: 研究 `src/serialization/preprocessor.cpp` 如何處理極其複雜的 WML 宏嵌套與條件編譯。
- **性能瓶頸**: 分析大型戰役加載時，WML 解析對內存與 CPU 的負擔，以及 Config 系統的優化策略。

## 階段四：軟體工程與現代化 (Level 10)
**目標**: 從一個 20 年老專案的角度學習架構演進。
- **技術債調查**: 識別代碼庫中的遺留模式（Legacy Patterns）與現代 C++ (C++17/20) 的融合。
- **Boost 模組應用**: 總結 Wesnoth 如何高效（或過度）使用 Boost（如 Spirit, Asio, Coroutine）。
- **內存管理策略**: 追蹤 `config` 與 `unit` 等重型對象的生命週期與引用計數。

---
*計畫擬定日期: 2026-05-17*
