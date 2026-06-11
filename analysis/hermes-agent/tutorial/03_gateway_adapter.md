# hermes-agent 開發教學 (三)：通訊閘道適配 (Gateway Adapters)

本教學將介紹如何新增一個通訊平台適配器（如接入一個新的通訊 App）。

## 1. 前置知識
- 理解 `gateway/run.py` 的非同步事件循環。
- 熟悉 `gateway/platforms/` 下的既有適配器實作。

## 2. 原始碼導航
- **適配器目錄**: `gateway/platforms/`
- **基礎類別**: `gateway/platforms/base.py` (若存在) 或參考 `telegram.py`。

## 3. 實作步驟

### 第一步：建立平台適配器檔案
```bash
touch gateway/platforms/my_platform.py
```

### 第二步：實作適配器類別
你至少需要處理訊息接收並呼叫 `gateway` 的分派邏輯。
```python
import asyncio
from gateway.platform_registry import register_platform

@register_platform("my_platform")
class MyPlatformAdapter:
    def __init__(self, config, gateway_runner):
        self.config = config
        self.gateway = gateway_runner

    async def run(self):
        # 這裡實作長連接或 Webhook 監聽
        while True:
            # 模擬接收訊息
            msg = await self.receive_external_message()
            # 呼叫 gateway 處理
            await self.gateway.handle_message(
                platform="my_platform",
                channel_id=msg.sender_id,
                text=msg.text,
                user_name=msg.sender_name
            )

    async def send_message(self, channel_id, text):
        # 這裡實作回傳訊息到外部平台的邏輯
        pass
```

### 第三步：配置憑證
在 `~/.hermes/config.yaml` 加入新平台的配置：
```yaml
gateway:
  platforms:
    my_platform:
      enabled: true
      api_key: "your-key-here"
```

## 4. 驗證方式
1. 執行閘道：`hermes gateway`
2. 檢查日誌，確認 `MyPlatformAdapter` 已成功啟動。
3. 嘗試從外部平台發送訊息，觀察 Agent 是否有回應。
