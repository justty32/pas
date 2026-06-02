# 啟動指南 — cws-no-llm

> 本文件說明如何在 **零網路、零 API Key** 的環境下啟動修仙世界模擬器（含本地 AI shim）。

---

## 前置需求

| 工具 | 版本 | 用途 |
|---|---|---|
| Python | 3.10+ | 後端執行環境 |
| Node.js | 18+ | 前端開發伺服器（`npm`） |
| Git | 任意 | （已 clone 則不需要） |

---

## 一次性安裝（首次執行）

在 `projects/cultivation-world-simulator/` 目錄下執行：

```powershell
# 1. 安裝後端依賴
pip install -r requirements.txt

# 2. 安裝前端依賴
cd web
npm install
cd ..
```

---

## 每次啟動

```powershell
# 在 projects/cultivation-world-simulator/ 目錄下執行
python src/server/main.py --dev
```

啟動成功後，終端會顯示前端地址，通常為：

```
http://localhost:5173
```

用瀏覽器開啟此網址即可進入遊戲。

---

## 首次設定（進入遊戲後，只需做一次）

由於 cws-no-llm 已 patch 掉 LLM 連線檢查，**不需要真實的 API Key 或模型服務**。
但遊戲 UI 的設定頁可能仍需要填入欄位才能點擊開始。

如果設定頁要求填寫，請填入任意假值：

| 欄位 | 填入值 |
|---|---|
| Base URL | `http://localhost:11434/v1` |
| API Key | `no-llm` |
| 智能模型名稱 | `local` |
| 快速模型名稱 | `local` |

> 這些值不會真正被使用——所有 LLM 呼叫都被 shim 攔截，永遠不會實際連線。

設定完成後點擊「開始新遊戲」即可。

---

## 已部署的 Patch 清單

以下是 cws-no-llm 對原版專案的所有改動（均在 `projects/cultivation-world-simulator/src/` 下）：

| 檔案 | 改動內容 | 類型 |
|---|---|---|
| `utils/llm/client.py` | `call_llm_with_task_name()` 加 4 行 shim 鉤子 | 核心 shim |
| `server/init_runtime.py` | `check_llm_connectivity()` 有 local_ai 時直接返回 `(True, "")` | 啟動 bypass |
| `systems/sect_random_event.py` | `_generate_reason_fragment()` 返回固定 reason fragment | 特殊 patch |
| `server/services/autonomous_custom_content_service.py` | `should_trigger()` 本地模式返回 `False` | 停用觸發 |

新增目錄：

```
src/local_ai/
├── __init__.py
├── dispatcher.py       ← 路由入口
├── decision.py         ← Utility AI（action_decision）
├── goals.py            ← 目標模板（long_term_objective）
├── relations.py        ← 關係公式（relation_delta）
├── narrative.py        ← 敘事詞庫（story_teller / interaction_feedback / backstory）
├── epithets.py         ← 外號生成（nickname）
├── sect_ai.py          ← 宗門 AI（sect_decider / sect_thinker）
└── minor_events.py     ← 隨機事件（random_minor_event）
```

---

## 驗證是否正常運行

啟動後觀察終端日誌：

- **正常**：模擬步驟會持續推進，不出現 HTTP 連線錯誤或 `LLM timeout` 等字樣
- **shim 生效**：不應看到任何 `call_llm_with_task_name` 的網路請求日誌

可用基準測試腳本驗證（不需要啟動伺服器）：

```powershell
# 在 projects/cultivation-world-simulator/ 目錄下執行
python C:/code/mine/pas/derived/cws-no-llm/tests/benchmark_100month.py
```

預期結果：100 月，零崩潰，零 ERROR。

---

## 常見問題

**Q: 出現「LLM 配置不完整」的錯誤**
A: 表示 `init_runtime.py` 的 patch 未生效。確認 `src/local_ai/` 目錄存在，且 `dispatcher.py` 可正常 import。

**Q: 模擬很快但角色行為單調（全部做同樣的事）**
A: shim 正在運作，但 `action_decision` 的 Utility AI 效用權重可能需要調整。參見 `src/local_ai/decision.py`。

**Q: 想恢復原版 LLM 模式**
A: 將 `src/utils/llm/client.py` 中的 shim 4 行移除，並移除 `src/local_ai/` 目錄即可，其他原版代碼未動。
