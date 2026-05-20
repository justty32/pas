"""水文模擬：從水源點 BFS 漫水，標記海洋遮罩（方格 4 鄰居版）。"""
from __future__ import annotations
from collections import deque
from ..state import EditorState

_OFFSETS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def run_flood_fill(state: EditorState) -> None:
    """BFS 漫水：從水源出發，將所有連通且高程 ≤ sea_level 的格子標為 ocean。

    若無手動水源，以地圖邊界上低於 sea_level 的格子作為種子。
    """
    w, h = state.width, state.height
    visited: list[list[bool]] = [[False] * w for _ in range(h)]
    queue: deque[tuple[int, int]] = deque()

    seeds = list(state.water_sources)
    if not seeds:
        for x in range(w):
            for y in (0, h - 1):
                if state.get_h(x, y) <= state.sea_level:
                    seeds.append((x, y))
        for y in range(h):
            for x in (0, w - 1):
                if state.get_h(x, y) <= state.sea_level:
                    seeds.append((x, y))

    for sx, sy in seeds:
        if state.in_bounds(sx, sy) and not visited[sy][sx]:
            visited[sy][sx] = True
            queue.append((sx, sy))

    while queue:
        x, y = queue.popleft()
        for dx, dy in _OFFSETS:
            nx, ny = x + dx, y + dy
            if state.in_bounds(nx, ny) and not visited[ny][nx]:
                if state.get_h(nx, ny) <= state.sea_level:
                    visited[ny][nx] = True
                    queue.append((nx, ny))

    state.ocean_mask = visited
