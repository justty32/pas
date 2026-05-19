"""水文模擬：從水源點 BFS 漫水，標記海洋遮罩。"""
from __future__ import annotations
from collections import deque
from ..state import EditorState

# Pointy-top hex 的六個軸向鄰居偏移（axial coords）
_OFFSETS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]


def run_flood_fill(state: EditorState) -> None:
    """BFS 漫水：從水源出發，將所有連通且高程 ≤ sea_level 的格子標為 ocean。

    若無手動水源，則以地圖邊界上低於 sea_level 的格子作為種子（模擬海平面從邊緣流入）。
    """
    w, h = state.width, state.height
    visited = [[False] * w for _ in range(h)]
    queue: deque[tuple[int, int]] = deque()

    seeds = list(state.water_sources)
    if not seeds:
        # 邊界種子
        for q in range(w):
            for r in (0, h - 1):
                if state.get_h(q, r) <= state.sea_level:
                    seeds.append((q, r))
        for r in range(h):
            for q in (0, w - 1):
                if state.get_h(q, r) <= state.sea_level:
                    seeds.append((q, r))

    for (sq, sr) in seeds:
        if state.in_bounds(sq, sr) and not visited[sr][sq]:
            visited[sr][sq] = True
            queue.append((sq, sr))

    while queue:
        q, r = queue.popleft()
        for dq, dr in _OFFSETS:
            nq, nr = q + dq, r + dr
            if state.in_bounds(nq, nr) and not visited[nr][nq]:
                if state.get_h(nq, nr) <= state.sea_level:
                    visited[nr][nq] = True
                    queue.append((nq, nr))

    state.ocean_mask = visited
