"""hymera — Hy 寫的 c-mera 風格 C/C++ 程式碼生成器。

此檔刻意是 .py（而非 .hy）：它必須先 ``import hy`` 註冊 .hy 的 import 鉤子，
之後套件內其餘的 .hy 模組才能被正常載入。

設計文件見 ``docs/``；總覽見 ``docs/01_architecture.md``。
"""

import hy  # noqa: F401  —— 註冊 .hy import 鉤子，務必最先

__version__ = "0.1.0"
