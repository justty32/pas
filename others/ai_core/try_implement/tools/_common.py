"""共用小工具：讓 try_implement 下的各工具能 import 既有的 ai_core library。

設計理由（KISS / least dependency）：
- ai_core library 位在 repo 的 ``src/ai_core``，本 spike 不安裝套件、也不改 sys.path 設定檔，
  改用「動態把 src 目錄塞進 sys.path」的最輕量手段，讓 import ai_core 可用。
- 只用標準庫（sys / pathlib）。
"""

from __future__ import annotations

import sys
from pathlib import Path

# try_implement/tools/_common.py → repo 根目錄為 parents[2]，try_implement 為 parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
_TRY_ROOT = Path(__file__).resolve().parents[1]


def ensure_ai_core_importable() -> None:
    """把 repo 的 src 目錄加入 sys.path，使 ``import ai_core`` 成功。"""
    src = str(_SRC)
    if src not in sys.path:
        sys.path.insert(0, src)


def ensure_lib_importable() -> None:
    """把 try_implement 根目錄加入 sys.path，使 ``from lib import ...`` 成功。"""
    root = str(_TRY_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def repo_root() -> Path:
    return _REPO_ROOT
