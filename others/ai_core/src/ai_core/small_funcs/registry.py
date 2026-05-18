from __future__ import annotations

from pathlib import Path
from typing import Callable


class FuncRegistry:
    """管理 SFC 子函式的 registry（§9.3）。

    支援兩種子函式型態（§9.2）：
    - Pass-through：子函式是獨立可執行檔，SFC 把 --metadata 查詢轉給它執行
    - SFC 自管：子函式邏輯在 SFC 內（Python function 或 bash snippet），
      metadata 由 registry 統一維護，子函式無法獨立執行

    新增子函式不需修改核心程式碼（§9.3）：
    把 .py module 放到 funcs_dir，registry 啟動時自動 import 並掛載。
    """

    def __init__(self, funcs_dir: Path) -> None:
        """掃描 funcs_dir 下所有 .py module，自動 import，建立 name → handler 的 map。

        同時掃描獨立可執行檔（pass-through 型）並登記路徑。
        """
        pass

    def dispatch(self, func_name: str, args: list[str]) -> int:
        """呼叫指定子函式，回傳 exit code。

        - func_name 不存在：stderr 報錯，回傳 1
        - pass-through 型：subprocess 呼叫底層可執行檔
        - SFC 自管型：直接呼叫 Python handler function
        """
        pass

    def list_funcs(self) -> list[str]:
        """回傳所有已登記子函式的名稱 list（供 --list 旗標使用）。"""
        pass

    def get_metadata(self, func_name: str) -> dict:
        """回傳指定子函式的 metadata dict。

        - pass-through 型：呼叫 `<exec> --metadata` 取得（§9.2 說明）
        - SFC 自管型：從 registry 內部維護的 metadata dict 直接回傳
        func_name 不存在時回傳空 dict 並 stderr 警告。
        """
        pass

    def register(self, name: str, handler: Callable, metadata: dict) -> None:
        """手動登記一個 SFC 自管型子函式。

        供 funcs_dir 下 module 在 import 時呼叫（類似裝飾器模式）。
        """
        pass
