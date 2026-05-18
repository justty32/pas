from __future__ import annotations


async def generate_function(
    spec: dict,
    language: str = "bash",
    retry_limit: int = 3,
    previous_error: str = "",
) -> str:
    """透過 ai-core-call 讓 LLM 產生函式原始碼（§8.1 步驟 1）。

    流程：
    1. 呼叫 build_author_prompt() 組 prompt（含 spec + 語言要求 + --metadata 協議 + examples）
    2. 把 prompt 寫入暫存檔，呼叫 ai-core-call --input <tmp> --output <tmp>
    3. 解析 LLM 回應，提取可執行的函式原始碼（去掉 markdown code block 等包裝）
    4. 回傳原始碼字串

    previous_error 有值時代表重試情境（dry-run 失敗回饋），prompt 會附上錯誤細節。
    retry_limit 由 ai-core-author cli.py 控制，這裡只做單次產生。
    """
    pass


def build_author_prompt(spec: dict, language: str, previous_error: str = "") -> str:
    """組合給 LLM 的 authoring prompt。

    包含：
    - spec 描述（name、description、examples）
    - 語言要求（bash、python 等）
    - --metadata 協議說明（要求產生的函式必須支援 --metadata，§4）
    - examples 要求（LLM 應在 metadata 中抄回 examples 欄位）
    - previous_error（重試時附上 dry-run 失敗的 input/expected/actual 比較）
    """
    pass


def extract_code(llm_response: str, language: str) -> str:
    """從 LLM 回應中提取可執行的函式原始碼，去掉 markdown code fence 等包裝。

    語言為 bash 時移除 ```bash ... ``` 包裝；
    語言為 python 時移除 ```python ... ``` 包裝；
    無法識別時回傳原始字串。
    """
    pass
