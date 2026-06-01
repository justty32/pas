# 設計決策 D01：Shim Layer 替換策略

**日期**: 2026-06-01  
**狀態**: 已採納

---

## 決策

在 `src/utils/llm/client.py::call_llm_with_task_name()` 加入一個「本地 AI 優先查詢」的前置鉤子，而不是修改任何上層 Phase 代碼或領域模型。

**參照來源**: `analysis/cultivation-world-simulator/architecture/02_level2_modules.md`（2.5 LLM 客戶端）

---

## 選項對比

| 方案 | 做法 | 優點 | 缺點 |
|---|---|---|---|
| **A. Shim Layer（採用）** | 只改 `call_llm_with_task_name()` | 影響面最小；上層 Phase 代碼不動；可保留 LLM fallback | 必須嚴格符合返回格式 |
| B. 替換各 Phase | 在每個 Phase 裡把 LLM 呼叫換成本地函數 | 直觀清晰 | 改動面廣（~10 個 Phase 檔案）；每次 CWS 更新都需要同步 |
| C. Mock LLM 服務 | 在本機起一個假的 LLM HTTP 服務 | 完全不改 Python 代碼 | 啟動複雜；JSON 生成邏輯在外部進程 |

---

## 理由

選 A 的核心原因：

1. **最小侵入**：`call_llm_with_task_name()` 在整個代碼庫只有一個呼叫點（`src/utils/llm/client.py:431`），改一個地方影響全部 16 個任務。
2. **保留降級能力**：dispatcher 返回 `None` 時自動 fallback 到 LLM，未來可選擇性保留某些任務走 LLM。
3. **易於測試**：dispatcher 是純函數 `(task_name, infos) -> dict | None`，可獨立單元測試不需要啟動整個伺服器。

---

## 實作形狀

```python
# src/utils/llm/client.py（唯一改動）
async def call_llm_with_task_name(task_name, template_path, infos, max_retries=None):
    from src.local_ai.dispatcher import dispatch   # 新增
    local_result = dispatch(task_name, infos)       # 新增
    if local_result is not None:                    # 新增
        return local_result                         # 新增

    mode = get_task_mode(task_name)
    return await call_llm_with_template(template_path, infos, mode, max_retries)
```

改動共 4 行。

---

## 風險

**返回格式不符**：若 shim 返回的 JSON 與消費端期望格式不符，會導致 `KeyError` 或靜默邏輯錯誤。  
緩解：Phase 0 開發時開啟 debug log，記錄每個 task 的 infos 輸入，並在消費端加斷言。

**`infos` 內容不明**：各 task 的 `infos` dict 鍵名尚未完全確認（見 `docs/task_interface_spec.md`）。  
緩解：Phase 0 stub 先以 `infos.get(key, default)` 防禦性讀取，待確認後收緊。
