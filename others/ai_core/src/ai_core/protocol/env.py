# 全系統共用的環境變數名稱常數
# 新增環境變數時在此集中定義，避免各模組各自硬寫字串

AI_CORE_TOKEN = "AI_CORE_TOKEN"
# wrapper 讀取此 env var 做 Bearer token 認證（§6.13）；未設定時從預設路徑讀 token 檔

AI_CORE_FUNCS_DIR = "AI_CORE_FUNCS_DIR"
# 覆蓋 ai-core-author 的輸出目錄與 ai-core-hub 的預設掃描目錄（§8.3）

AI_CORE_SERVER_HOST = "AI_CORE_SERVER_HOST"
AI_CORE_SERVER_PORT = "AI_CORE_SERVER_PORT"
# 覆蓋 ai-core-server 預設 127.0.0.1:5577

AI_CORE_HUB_HOST = "AI_CORE_HUB_HOST"
AI_CORE_HUB_PORT = "AI_CORE_HUB_PORT"
# 覆蓋 ai-core-hub-server 預設 127.0.0.1:5578
