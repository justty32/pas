"""互動式六角格範例 (pygame)。

依賴：`pip install pygame`

操作：
    左鍵：設定中心格 (黃色)
    右鍵：設定直線終點 (粉紅)
    + / - / 滾輪：調整半徑
    1 / 2 / 3 / 4：切換模式 (鄰居 / 環 / 螺旋範圍 / 直線)
    ESC：離開
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.hex import Hex, distance, hex_round, line, ring, spiral

HEX_SIZE = 28
WIDTH, HEIGHT = 960, 720
GRID_RADIUS = 8

BG = (20, 22, 30)
GRID_LINE = (60, 64, 78)
TEXT = (220, 220, 220)
CENTER_COLOR = (250, 200, 70)
HIGHLIGHT = (90, 200, 250)
SECONDARY = (250, 90, 130)

SQRT3 = math.sqrt(3)
CX, CY = WIDTH // 2, HEIGHT // 2

MODES = ("neighbors", "ring", "spiral", "line")


def hex_to_pixel(h: Hex) -> tuple[float, float]:
    # pointy-top axial → pixel
    x = HEX_SIZE * (SQRT3 * h.q + SQRT3 / 2 * h.r) + CX
    y = HEX_SIZE * (1.5 * h.r) + CY
    return x, y


def pixel_to_hex(px: float, py: float) -> Hex:
    x = (px - CX) / HEX_SIZE
    y = (py - CY) / HEX_SIZE
    q = SQRT3 / 3 * x - 1.0 / 3 * y
    r = 2.0 / 3 * y
    return hex_round(q, r)


def hex_corners(cx: float, cy: float) -> list[tuple[float, float]]:
    pts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        pts.append((cx + HEX_SIZE * math.cos(angle), cy + HEX_SIZE * math.sin(angle)))
    return pts


def draw_hex(surface, h: Hex, fill=None, outline=GRID_LINE, width=1):
    pts = hex_corners(*hex_to_pixel(h))
    if fill is not None:
        pygame.draw.polygon(surface, fill, pts)
    pygame.draw.polygon(surface, outline, pts, width)


def in_grid(h: Hex) -> bool:
    return distance(Hex(0, 0), h) <= GRID_RADIUS


def compute_highlights(mode: str, center: Hex, line_end: Hex, radius: int) -> list[Hex]:
    if mode == "neighbors":
        return list(center.neighbors())
    if mode == "ring":
        return ring(center, radius)
    if mode == "spiral":
        return list(spiral(center, radius))
    if mode == "line":
        return line(center, line_end)
    return []


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("mapcore_py — hex demo")
    font = pygame.font.SysFont("monospace", 16)
    clock = pygame.time.Clock()

    center = Hex(0, 0)
    line_end = Hex(4, -2)
    radius = 3
    mode_idx = 0
    running = True

    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif pygame.K_1 <= ev.key <= pygame.K_4:
                    mode_idx = ev.key - pygame.K_1
                elif ev.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    radius = min(radius + 1, GRID_RADIUS)
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    radius = max(radius - 1, 0)
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 4:
                    radius = min(radius + 1, GRID_RADIUS)
                elif ev.button == 5:
                    radius = max(radius - 1, 0)
                else:
                    h = pixel_to_hex(*ev.pos)
                    if in_grid(h):
                        if ev.button == 1:
                            center = h
                        elif ev.button == 3:
                            line_end = h

        mode = MODES[mode_idx]
        highlights = compute_highlights(mode, center, line_end, radius)

        screen.fill(BG)
        for h in spiral(Hex(0, 0), GRID_RADIUS):
            draw_hex(screen, h)
        for h in highlights:
            draw_hex(screen, h, fill=HIGHLIGHT)
        draw_hex(screen, center, fill=CENTER_COLOR)
        if mode == "line":
            draw_hex(screen, line_end, fill=SECONDARY)

        info = [
            f"Mode: {mode}    (1=neighbors  2=ring  3=spiral  4=line)",
            f"Radius: {radius}    (+/-/wheel)",
            f"Center: ({center.q}, {center.r})    Line end: ({line_end.q}, {line_end.r})",
            "Left=center  Right=line end  ESC=quit",
            f"highlighted: {len(highlights)}",
        ]
        for i, txt in enumerate(info):
            screen.blit(font.render(txt, True, TEXT), (10, 10 + i * 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
