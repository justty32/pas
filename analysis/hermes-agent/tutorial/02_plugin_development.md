# hermes-agent 開發教學 (二)：系統級外掛開發 (Plugins)

如果你需要修改 Agent 的核心行為（例如攔截訊息、修改模型回傳文字），你需要開發一個「外掛」(Plugin)。

## 1. 前置知識
- 理解「生命週期鉤子」(Lifecycle Hooks)。
- 了解 `hermes_cli/plugins.py` 的載入機制。

## 2. 原始碼導航
- **核心邏輯**: `hermes_cli/plugins.py`
- **鉤子清單**: `VALID_HOOKS` 變數。

## 3. 實作步驟

### 第一步：建立外掛目錄
建議放在使用者目錄下以便開發：
```bash
mkdir -p ~/.hermes/plugins/my-interceptor
```

### 第二步：撰寫外掛清單 (`plugin.yaml`)
```yaml
name: my-interceptor
version: 1.0.0
description: "攔截並修改模型的回傳文字。"
enabled: true
```

### 第三步：實作註冊邏輯 (`__init__.py`)
你必須實作 `register(ctx)` 函數。
```python
def register(ctx):
    # 註冊一個鉤子，修改 LLM 的輸出
    @ctx.hook("transform_llm_output")
    def add_signature(text, **kwargs):
        if text:
            return text + "\n\n---\n*由 My Interceptor 插件增強*"
        return text

    # 你也可以在這裡註冊專屬工具
    # ctx.register_tool(...)
```

### 第四步：啟用外掛
在 `~/.hermes/config.yaml` 中確認啟用：
```yaml
plugins:
  enabled:
    - my-interceptor
```

## 4. 驗證方式
1. 啟動對話：`hermes`
2. 隨便問一個問題。
3. 觀察回覆的末尾是否出現了你的自定義簽名。
