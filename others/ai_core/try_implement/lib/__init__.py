"""try_implement 的可重用 library 集合（純標準庫、零外部相依）。

這些不是 CLI 工具，而是給工具/函式 import 的小型 library。各自對應 ai_core 規範
中的一個慣例或基礎設施：

- ``state_dirs``  — composite_spec.md「標準狀態目錄慣例」的參考實作
- ``recovery``    — composite_spec.md「中斷恢復慣例」的參考實作
- ``memoize``     — session_resume 提到、尚未定案的「記憶化慣例」原型
- ``server``      — persistent server 標準 lifecycle（thinking_pending §3）
- ``singleton``   — singleton 資源：queue + consume rate（thinking_pending §4）
- ``trace``       — 調用鏈追蹤：結構化 stderr log + trace id（thinking_pending §5）
- ``call``        — 跨邊界統一呼叫：in-process / subprocess / http（thinking_pending §6）
- ``llm_call``    — llm_call(str)->str 基底 + context packing（CLAUDE.md 元件 2）

全部是 try_implement 的提案 / 遊樂場實作，非正式 library；正式版扶正進 src/ 前由使用者定奪。
"""
