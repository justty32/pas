"""測試共用工具：fixture 路徑、stdout 捕獲、檔案複製。"""

import io
import sys
import shutil
import contextlib
from pathlib import Path

EXAMPLES = Path(__file__).parent.parent / "examples"
FIGHTER  = EXAMPLES / "fighter.tres"
META     = EXAMPLES / "fighter.anim.meta.json"
SM       = EXAMPLES / "state_machine_sample.tres"


def copy_fixture(src: Path, dst_dir: Path) -> Path:
    """把 src 複製到 dst_dir，回傳新路徑。"""
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    return dst


@contextlib.contextmanager
def capture():
    """with capture() as out: ... → out.getvalue() 取 stdout 字串。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf
