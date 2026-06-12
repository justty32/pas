# hermes-agent 開發教學 (一)：基礎技能開發 (Skills)

本教學將引導你如何為 `hermes-agent` 建立一個新的「技能」(Skill)。技能是 Agent 最基本的擴充方式，通常是一組解決特定問題的 Python 腳本或 Shell 命令。

## 1. 前置知識
- 理解 `tools/registry.py` 的自註冊機制。
- 熟悉 Markdown 格式（用於撰寫 `SKILL.md`）。
- 基礎的 Python 程式設計。

## 2. 原始碼導航
- **技能存放路徑**: `skills/<category>/<skill-name>/`
- **範例參考**: `skills/productivity/google-workspace/`

## 3. 實作步驟

### 第一步：建立技能目錄
在 `skills/` 下建立你的技能目錄，例如：
```bash
mkdir -p skills/utility/my-calculator
```

### 第二步：撰寫技能定義文件 (`SKILL.md`)
這是技能的靈魂，讓 Agent 知道何時以及如何使用它。
```markdown
---
name: my-calculator
description: "一個簡單的計算工具，支援加減乘除。"
version: 1.0.0
author: YourName
license: MIT
platforms: [linux, macos, windows]
---

# My Calculator Skill

這個技能提供基礎的數學運算功能。

## Scripts
- `scripts/calc.py` ??主要執行腳本
```

### 第三步：撰寫執行腳本 (`scripts/calc.py`)
Agent 會透過 Shell 調用此腳本。
```python
import json
import sys
import fire

def add(a: float, b: float):
    return {"result": a + b}

def multiply(a: float, b: float):
    return {"result": a * b}

if __name__ == "__main__":
    fire.Fire({
        "add": add,
        "multiply": multiply
    })
```

### 第四步：註冊工具 (透過 `tools/` 適配器)
在 `tools/` 下建立一個對應的註冊檔案（或在現有工具中加入），讓 LLM 能看到它：

> **注意**：`schema` 只傳內層字典（`name / description / parameters`），**不要**加 `{"type":"function","function":{...}}` 的外層包裝。`ToolRegistry.get_definitions()`（`tools/registry.py:383`）會在對外輸出時自動補上。若雙重包裝，LLM 拿到的格式會是嵌套錯誤的結構。參考範例：`tools/terminal_tool.py`。

```python
from tools.registry import registry

def register_my_calc():
    registry.register(
        name="my_calc",
        toolset="utility",
        schema={
            "name": "my_calc",
            "description": "執行基礎數學運算",
            "parameters": {
                "type": "object",
                "properties": {
                    "op": {"type": "string", "enum": ["add", "multiply"]},
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                }
            }
        },
        handler=my_calc_handler
    )
```

## 4. 驗證方式
1. 啟動對話：`hermes`
2. 輸入：`使用 my_calc 幫我算 123 乘以 456`
3. 觀察 Agent 是否正確調用腳本並回傳結果。
