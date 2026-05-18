"""ai-core-hub-server：常駐版 function hub，提供 runtime discovery API（§7.2）。"""
from __future__ import annotations

from fastapi import FastAPI, Request

app = FastAPI(title="ai-core-hub-server")

_funcs: list = []   # 啟動時掃描後快取的 MetadataView list


def reload_funcs(funcs_dir) -> None:
    """重新掃描 funcs_dir，更新 _funcs 快取。

    server 啟動時呼叫一次；未來可考慮加 file-watcher 自動 reload（第一版不做）。
    """
    pass


@app.get("/funcs")
async def list_funcs(detail: str = "summary"):
    """列出所有函式。

    detail=summary：回傳 name + summary（給 AI scan 用，避免 context 爆炸）。
    detail=full：回傳完整 metadata（包含 examples、io 等）。
    """
    pass


@app.get("/funcs/{name}")
async def get_func(name: str):
    """回傳單一函式的完整 metadata。名稱不存在時 404。"""
    pass


@app.get("/search")
async def search_funcs(q: str):
    """對 description / summary 做關鍵字搜尋。

    進階版：透過 ai-core-call 做語意搜尋（真正的自舉，§7.4）。
    第一版只做關鍵字比對。
    """
    pass


@app.post("/funcs/{name}/call")
async def call_func(name: str, request: Request):
    """代理執行指定函式。

    body: {"input": ..., "args": [...]}
    把 input 傳給函式執行，擷取 stdout 回傳，stderr 轉成回應欄位。
    """
    pass


@app.get("/graph")
async def get_graph():
    """回傳函式依賴圖。

    從每個 MetadataView.dependencies 累積建構有向圖，以 JSON 格式回傳。
    """
    pass


@app.get("/export")
async def export_funcs(format: str):
    """Runtime export（§15.3）。

    format 可為：mcp | openai-tools | anthropic-tools | claude-skill | agent-md | functions-md
    """
    pass


def main() -> None:
    """啟動 ai-core-hub-server。

    旗標：
    --host        綁定 host（預設 AI_CORE_HUB_HOST env 或 127.0.0.1）
    --port        綁定 port（預設 AI_CORE_HUB_PORT env 或 5578）
    --funcs-dir   指定掃描目錄（預設 AI_CORE_FUNCS_DIR env 或 user_data_dir/ai_core/funcs/）
    --log-file / --log-level  同 ai-core-server（§6.11）
    --metadata    印自身 metadata 後 exit
    """
    pass
