"""mapcore_py_square.generation：地圖生成管線（Phase 1~7）。"""

from .biome import apply_biomes
from .classify import expand_coast, heightmap_to_tilemap
from .climate import (
    apply_climate,
    compute_hilliness,
    compute_rainfall_mm,
    compute_temperature_celsius,
    latitude_normalized,
)
from .depressions import fill_depressions
from .heightmap import generate_heightmap
from .pipeline import WorldGenResult, generate_world
from .postprocess import (
    find_components,
    is_land,
    is_water,
    post_process,
    relabel_coast,
    remove_small_islands,
    remove_small_lakes,
)

__all__ = [
    "apply_biomes",
    "apply_climate",
    "compute_hilliness",
    "compute_rainfall_mm",
    "compute_temperature_celsius",
    "expand_coast",
    "fill_depressions",
    "find_components",
    "generate_heightmap",
    "generate_world",
    "heightmap_to_tilemap",
    "is_land",
    "is_water",
    "latitude_normalized",
    "post_process",
    "relabel_coast",
    "remove_small_islands",
    "remove_small_lakes",
    "WorldGenResult",
]
