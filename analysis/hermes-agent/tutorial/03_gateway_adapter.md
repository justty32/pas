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

> **注意**：沒有 `@register_platform` 裝飾器。適配器需透過 `PlatformEntry` 手動向 `platform_registry` 註冊，入口訊息則以 `MessageEvent` 物件傳入私有方法 `_handle_message`。

```python
import asyncio
from gateway.platform_registry import platform_registry, PlatformEntry
from gateway.run import MessageEvent  # 視實際 import 路徑調整

class MyPlatformAdapter:
    def __init__(self, config, gateway_runner):
        self.config = config
        self.gateway = gateway_runner

    async def run(self):
        # 這裡實作長連接或 Webhook 監聽
        while True:
            # 模擬接收訊息
            msg = await self.receive_external_message()
            # 呼叫 gateway 處理（使用 MessageEvent，非展開的關鍵字引數）
            event = MessageEvent(
                platform="my_platform",
                channel_id=msg.sender_id,
                text=msg.text,
                user_name=msg.sender_name,
            )
            await self.gateway._handle_message(event)

    async def send_message(self, channel_id, text):
        # 這裡實作回傳訊息到外部平台的邏輯
        pass

# 在模組載入時向 platform_registry 登記（gateway/run.py:14-23 範例）
platform_registry.register(PlatformEntry(
    name="my_platform",
    label="My Platform",
    adapter_factory=lambda cfg, runner: MyPlatformAdapter(cfg, runner),
))
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
