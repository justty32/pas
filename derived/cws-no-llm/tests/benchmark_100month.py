"""
Phase 4 基準測試：100 月模擬無崩潰

執行方式（在 projects/cultivation-world-simulator 目錄下）:
  python C:/code/mine/pas/derived/cws-no-llm/tests/benchmark_100month.py

輸出寫入 benchmark_result.txt（UTF-8）。
"""
import asyncio
import logging
import os
import sys
import traceback

PROJECT = r"C:\code\mine\pas\projects\cultivation-world-simulator"
sys.path.insert(0, PROJECT)
os.chdir(PROJECT)

# 設定語言與 config（必須在 import 源碼前就設定）
os.environ.setdefault("CWS_DATA_DIR", r"C:\tmp\cws_benchmark")

from src.classes.language import language_manager
from src.utils.df import reload_game_configs
from src.utils.config import update_paths_for_language

language_manager.set_language("zh-TW")
update_paths_for_language("zh-TW")
reload_game_configs()

from src.run.load_map import load_cultivation_world_map
from src.classes.core.world import World
from src.systems.time import Year, Month, create_month_stamp
from src.sim.avatar_init import make_avatars
from src.sim.simulator import Simulator

log_lines: list[str] = []
error_count = 0
warning_count = 0


class Capture(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        global error_count, warning_count
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            error_count += 1
            log_lines.append(f"[ERROR] {msg}")
        elif record.levelno >= logging.WARNING:
            warning_count += 1
            log_lines.append(f"[WARN] {msg}")


capture = Capture()
capture.setFormatter(logging.Formatter("%(name)s: %(message)s"))
logging.getLogger().addHandler(capture)
logging.getLogger().setLevel(logging.WARNING)
# 靜音 httpx / uvicorn 噪音
for noisy in ("httpcore", "httpx", "uvicorn", "websocket"):
    logging.getLogger(noisy).setLevel(logging.CRITICAL)


async def run_benchmark(months: int = 100, npc_count: int = 10) -> dict:
    global error_count, warning_count
    error_count = 0
    warning_count = 0
    crash_months: list[int] = []

    # 初始化
    print("Loading map...", flush=True)
    game_map = load_cultivation_world_map()
    ms = create_month_stamp(Year(100), Month.JANUARY)
    world = World(map=game_map, month_stamp=ms, start_year=100)
    world.run_config_snapshot = {}  # Simulator 需要此屬性

    print(f"Generating {npc_count} NPCs...", flush=True)
    avatar_dict = make_avatars(world, count=npc_count, current_month_stamp=ms, existed_sects=None)
    # make_avatars 不一定自動 register，確保都注冊
    for avatar in avatar_dict.values():
        if avatar.id not in world.avatar_manager.avatars:
            world.avatar_manager.register_avatar(avatar)

    alive_initial = len(list(world.avatar_manager.get_living_avatars()))
    print(f"Initial avatars: {alive_initial}", flush=True)

    sim = Simulator(world)

    print(f"Running {months} months...", flush=True)
    for m in range(months):
        try:
            await sim.step()
        except Exception:
            crash_months.append(m + 1)
            tb = traceback.format_exc()
            log_lines.append(f"[CRASH] month={m+1}:\n{tb}")
            # 嘗試繼續（不中止循環）

        if (m + 1) % 12 == 0:
            alive = len(list(world.avatar_manager.get_living_avatars()))
            yr = world.month_stamp.get_year()
            print(f"  Year {yr}: {alive} alive", flush=True)

    alive_final = len(list(world.avatar_manager.get_living_avatars()))
    final_year = world.month_stamp.get_year()

    return {
        "months": months,
        "npc_count": npc_count,
        "alive_initial": alive_initial,
        "alive_final": alive_final,
        "final_year": final_year,
        "crashes": len(crash_months),
        "crash_months": crash_months,
        "errors": error_count,
        "warnings": warning_count,
    }


if __name__ == "__main__":
    result = asyncio.run(run_benchmark(months=100, npc_count=10))

    lines = [
        "=== Phase 4 基準測試結果 ===",
        f"模擬月數: {result['months']}",
        f"初始 NPC: {result['npc_count']}（實際初始化: {result['alive_initial']}）",
        f"結束存活: {result['alive_final']}（第 {result['final_year']} 年）",
        f"崩潰次數: {result['crashes']}（月份: {result['crash_months']}）",
        f"ERROR 日誌: {result['errors']}",
        f"WARNING 日誌: {result['warnings']}",
        "",
        "=== 詳細日誌（ERROR/WARN/CRASH 只列前 50 條）===",
    ] + log_lines[:50]

    out_path = r"C:\code\mine\pas\derived\cws-no-llm\tests\benchmark_result.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines[:10]))
    print(f"\n完整結果已寫入: {out_path}")
