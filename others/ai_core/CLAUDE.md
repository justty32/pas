# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案狀態

此資料夾為新專案，目前**處於構想階段**，尚無任何實作程式碼、建置設定、測試或相依套件。唯一的內容是 `thinking.md`，記錄了專案的核心想法與規劃。

未來在此目錄新增實作時，請同步更新本檔案，補上實際的建置 / 執行 / 測試指令與架構細節。

## 設計哲學

整個系統遵循四個原則（出自 `thinking.md`）：

- **KISS** — 簡單優先
- **Lightweight** — 輕量
- **No wheel-remake** — 不重造輪子
- **Least dependency** — 相依最少化

理解這些原則對於後續實作決策非常關鍵：當你考慮要不要引入框架、抽象層、或自訂 DSL 時，預設答案應該是「不要」，除非有明確理由。

## 目標架構（規劃中的四個元件）

整體把 LLM 呼叫視為**一個函式 (function)**，再把所有支援設施（佇列管理、shell 包裝、metadata 收集）疊在這個基礎概念上。

### 1. LLM Entry Manager（第一支程式）

定位類似 [litellm](https://github.com/BerriAI/litellm) 或 [OpenRouter](https://openrouter.ai/)：統一管理多個 LLM 模型 / API 的呼叫入口。

關鍵設計重點：
- LLM 是**單例資源 (singleton resource)**，本地或遠端模型一次只能處理一個請求 → 採佇列 (queue) 模式
- 每個 queue 可以由不同 LLM entry 來消費
- 由本程式集中管理 **consume rate**：token 用量、金錢用量；本地模型還包含算力 / GPU 用量

### 2. LLM Calling Packing（context binding 與 output processing）

把 LLM 呼叫包裝成具語意的函式。基本介面：

```
llm_call(string) -> string
```

在這個基底上疊加 context 與 post-processing 形成新函式，例如：

```python
def llm_call_coding_question(string):
    input = "you are a professor of coding, and... " + string
    output = llm_call(input)
    output = output + " -- at 20240505"
    return output
```

> 注意：上面範例直接出自 `thinking.md`，是設計範例不是已實作程式碼。

### 3. Shell / App 作為函式（標準化介面）

由於 LLM 的輸入輸出都是文字，**shell 命令是最自然的封裝介面**。任何 shell script、Python 程式、其他 app 都可以成為一個「函式」：

```bash
llm_call --input XXX.txt --output YYY.txt
llm_call --input "haha hello how are you" > XXX.txt
```

呼叫端不需要知道底層是 bash 或 .py。

**強制介面合約 (mandatory interface contract)：**

每個函式都必須實作 `--metadata` 旗標，回傳 JSON 包含：
- 預期執行時間 (expect execution time)
- 預期記憶體用量 (memory expect usage)
- 格式 (format) — bash / .py / 其他

```bash
llm_call --input XXX.txt --output XXX.txt   # 一般執行
llm_call --metadata                          # 回傳 metadata JSON
```

**函式型態 (function types)：**
- **大多數函式應為 one-shot、無狀態 (stateless)**
- 需要多輪互動的函式必須**自行管理狀態**（存檔到外部檔案，下一輪由參數 / 檔案載入）
- **重量級函式應變成 server**，提供 API 介面，自身也成為單例資源（與 LLM Entry Manager 同模式）

### 4. Function Hub（第二支程式）

掃描函式集，呼叫每個函式的 `--metadata` 並彙總成清單：

```bash
hub --build-function-list ./funcs/* > list.txt
```

產出的 `list.txt` 概念上類似 LLM 的 skill 清單，用來告訴 LLM「我手邊有哪些工具可用」。

> 設計待辦：hub 要能對函式做摘要 (shorter conclusion)，避免 list.txt 太大撐爆 LLM context。

### 5. Small Function Center（第三支程式）

許多函式可能只是一行 shell 或非常薄的 LLM 包裝。為避免檔案爆炸，把這些 tiny function 集中到一個 dispatcher：

```bash
small-func-center --call func_1 --input XXX --output YYY
```

## 實作時的注意事項

當你開始實作上述任一元件時：

1. **先決定語言／執行環境**：`thinking.md` 沒有指定。預設選擇應該偏向「最少相依」（純 Python 標準庫、純 bash，避免重型框架）。
2. **`--metadata` 介面是跨元件契約**：Function Hub 的可行性完全建立在所有函式都遵守此介面之上。實作任何新函式時，metadata 不是可選項。
3. **單例資源模式會反覆出現**：LLM Entry Manager 與 heavy server-style function 都是這個模式。如果有重複實作的需求，考慮抽出共用的 queue / rate-limit 模組。
4. **shell 為一等公民**：不要為了「讓 Python API 更好用」而犧牲 shell 介面的清晰度。CLI 才是預設介面。

## 與上層 `pas/` 專案的關係

本資料夾位於 `pas/others/ai_core/`。上層 `pas/CLAUDE.md` 定義了 pas 工作空間的規範（繁體中文輸出、自動留檔到 `analysis/<project_name>/` 等）。**這些規範對本資料夾下的工作同樣適用**，除非本檔案另有指定。

## 文件語言

所有回覆、註解、留檔請使用**繁體中文**。程式碼識別子、shell 指令、技術名詞保留原文。
