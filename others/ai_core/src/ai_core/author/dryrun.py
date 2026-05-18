from __future__ import annotations

from pathlib import Path


def run_dryrun(func_path: Path, examples: list[dict]) -> tuple[bool, str]:
    """把 examples 逐筆當輸入跑 func_path，比對實際輸出與預期輸出（§8.1 步驟 2）。

    回傳 (passed: bool, error_message: str)。

    examples 為空時退化為「只驗執行不 crash」（§8.2）：
    - 呼叫 func_path 不帶任何輸入
    - exit code 0 視為通過

    失敗時 error_message 格式範例：
    「example[0] 失敗：input="hello"，expected="hello"，actual="HELLO"」
    此字串會被 generator.generate_function() 原文附在下一輪 prompt 中。
    """
    pass


def validate_metadata_protocol(func_path: Path) -> tuple[bool, str]:
    """呼叫 `<func_path> --metadata`，驗 exit 0 且 stdout 為合法 JSON（§8.1 步驟 4）。

    這是 dry-run 流程的最後一關，確認 LLM 產出的函式確實遵守 --metadata 協議。
    回傳 (passed: bool, error_message: str)。
    """
    pass


def _run_example(func_path: Path, example: dict) -> tuple[int, str]:
    """執行 func_path，傳入 example["input"]，回傳 (exit_code, stdout_output)。

    input 方式由 example.get("input_mode", "stdin") 決定：
    - "stdin"：把 input 字串 pipe 進 subprocess 的 stdin
    - "file"：把 input 寫入暫存檔，以 --input <tmpfile> 傳入
    """
    pass
