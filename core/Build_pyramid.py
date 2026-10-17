from PIL import Image
from PIL import ImageFile
from pathlib import Path
import math
import os

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

# =========================================================
# CONFIG
# =========================================================

SOURCE_IMAGE = "/home/bossx918spy/Desktop/DataSets/FULL RAWS/Mandalay Myanmar, earthquake, very high-resolution satellite image.jpg"

OUTPUT_DIR = "/home/bossx918spy/Desktop/DeepGlobeAV-Plus/services/tile_cache/Mandalay Myanmar, earthquake/pyramid"

TILE_SIZE = 512
MAX_ZOOM = 4

# =========================================================
# LOAD
# =========================================================

img = Image.open(SOURCE_IMAGE).convert("RGB")

width, height = img.size

print("IMAGE:", width, "x", height)

# =========================================================
# BUILD PYRAMID
# =========================================================

for z in range(MAX_ZOOM + 1):

    scale = 2 ** (MAX_ZOOM - z)

    level_width = width // scale
    level_height = height // scale

    print("\\nZOOM:", z)
    print("SIZE:", level_width, "x", level_height)

    resized = img.resize(
        (level_width, level_height),
        Image.LANCZOS
    )

    cols = math.ceil(level_width / TILE_SIZE)
    rows = math.ceil(level_height / TILE_SIZE)

    for x in range(cols):

        for y in range(rows):

            left = x * TILE_SIZE
            upper = y * TILE_SIZE

            right = min(left + TILE_SIZE, level_width)
            lower = min(upper + TILE_SIZE, level_height)

            tile = resized.crop(
                (left, upper, right, lower)
            )

            out_dir = Path(
                OUTPUT_DIR
            ) / str(z) / str(x)

            out_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            tile.save(
                out_dir / f"{y}.png"
            )

    print("DONE ZOOM", z)

print("\\nPYRAMID COMPLETE")