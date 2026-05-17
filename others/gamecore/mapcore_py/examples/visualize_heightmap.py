"""高程 noise 視覺化範例 (pygame)。

依賴：`pip install pygame`

操作：
    方向鍵 ←→↑↓：平移視角   Home：相機歸位
    Space：換新 seed (隨機)
    N：seed - 1   M：seed + 1
    +/-：調 octaves (1~8)
    [ / ]：調 persistence (0.1~1.0，0.05 為一格)
    , / .：調 base_frequency (1~16)
    G：切換灰階 / 地形漸層
    ESC：離開
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.hex import Hex
from mapcore.generation.heightmap import generate_heightmap

HEX_SIZE = 16
MAP_W, MAP_H = 80, 50
WIDTH, HEIGHT = 1280, 760
MARGIN_X, MARGIN_Y = 30, 20
SCROLL_SPEED = 10

SQRT3 = math.sqrt(3)
BG = (12, 14, 20)
TEXT = (220, 220, 220)


def hex_to_pixel(h: Hex, cam_x: float = 0.0, cam_y: float = 0.0) -> tuple[float, float]:
    x = HEX_SIZE * (SQRT3 * h.q + SQRT3 / 2 * h.r) + MARGIN_X - cam_x
    y = HEX_SIZE * (1.5 * h.r) + MARGIN_Y - cam_y
    return x, y


def hex_corners(cx: float, cy: float) -> list[tuple[float, float]]:
    return [
        (cx + HEX_SIZE * math.cos(math.radians(60 * i - 30)),
         cy + HEX_SIZE * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]


def grayscale(v: float) -> tuple[int, int, int]:
    g = max(0, min(255, int(v * 255)))
    return g, g, g


def terrain_gradient(v: float) -> tuple[int, int, int]:
    """deep ocean → shallow → sand → grass → forest → hill → mountain → snow"""
    stops = [
        (0.00, (15, 35, 90)),     # 深海
        (0.30, (40, 90, 160)),    # 海
        (0.42, (70, 140, 200)),   # 淺海
        (0.46, (220, 200, 130)),  # 沙
        (0.55, (90, 170, 80)),    # 草
        (0.70, (40, 110, 55)),    # 森林
        (0.82, (130, 100, 60)),   # 丘陵
        (0.92, (110, 105, 100)),  # 山
        (1.00, (240, 245, 250)),  # 雪
    ]
    for i in range(len(stops) - 1):
        v0, c0 = stops[i]
        v1, c1 = stops[i + 1]
        if v <= v1:
            t = 0.0 if v1 == v0 else (v - v0) / (v1 - v0)
            return tuple(int(c0[k] * (1 - t) + c1[k] * t) for k in range(3))  # type: ignore[return-value]
    return stops[-1][1]


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("mapcore_py — heightmap demo")
    font = pygame.font.SysFont("monospace", 16)
    clock = pygame.time.Clock()

    seed = random.randint(0, 99999)
    octaves = 5
    persistence = 0.5
    base_frequency = 4
    use_gradient = True
    cam_x, cam_y = 0.0, 0.0

    def regenerate():
        return generate_heightmap(
            MAP_W, MAP_H,
            seed=seed, octaves=octaves,
            persistence=persistence, base_frequency=base_frequency,
        )

    heightmap = regenerate()
    dirty = False
    running = True

    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_SPACE:
                    seed = random.randint(0, 99999)
                    dirty = True
                elif ev.key == pygame.K_n:
                    seed = max(0, seed - 1)
                    dirty = True
                elif ev.key == pygame.K_m:
                    seed += 1
                    dirty = True
                elif ev.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    octaves = min(8, octaves + 1)
                    dirty = True
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    octaves = max(1, octaves - 1)
                    dirty = True
                elif ev.key == pygame.K_LEFTBRACKET:
                    persistence = max(0.1, round(persistence - 0.05, 2))
                    dirty = True
                elif ev.key == pygame.K_RIGHTBRACKET:
                    persistence = min(1.0, round(persistence + 0.05, 2))
                    dirty = True
                elif ev.key == pygame.K_COMMA:
                    base_frequency = max(1, base_frequency - 1)
                    dirty = True
                elif ev.key == pygame.K_PERIOD:
                    base_frequency = min(16, base_frequency + 1)
                    dirty = True
                elif ev.key == pygame.K_g:
                    use_gradient = not use_gradient
                elif ev.key == pygame.K_HOME:
                    cam_x, cam_y = 0.0, 0.0

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  cam_x -= SCROLL_SPEED
        if keys[pygame.K_RIGHT]: cam_x += SCROLL_SPEED
        if keys[pygame.K_UP]:    cam_y -= SCROLL_SPEED
        if keys[pygame.K_DOWN]:  cam_y += SCROLL_SPEED

        if dirty:
            heightmap = regenerate()
            dirty = False

        screen.fill(BG)
        color_fn = terrain_gradient if use_gradient else grayscale
        for r in range(MAP_H):
            for q in range(MAP_W):
                cx, cy = hex_to_pixel(Hex(q, r), cam_x, cam_y)
                if cx < -HEX_SIZE or cx > WIDTH + HEX_SIZE: continue
                if cy < -HEX_SIZE or cy > HEIGHT + HEX_SIZE: continue
                pygame.draw.polygon(screen, color_fn(heightmap[r][q]), hex_corners(cx, cy))

        info = [
            f"seed={seed}  octaves={octaves}  persistence={persistence}  base_freq={base_frequency}  cam=({cam_x:.0f},{cam_y:.0f})",
            f"color: {'gradient' if use_gradient else 'grayscale'} (G to toggle)",
            "Arrows=pan  Home=reset cam  Space=random  N/M=seed-/+  +/-=octaves  [/]=persistence  ,/.=base_freq  ESC=quit",
        ]
        for i, txt in enumerate(info):
            screen.blit(font.render(txt, True, TEXT), (10, HEIGHT - 70 + i * 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
