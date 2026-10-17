import os
import shutil

SOURCE = "/home/bossx918spy/Desktop/DeepGlobeAV-Plus/services/tile_cache/Mandalay Myanmar, earthquake/tiles"
DEST = "/home/bossx918spy/Desktop/DeepGlobeAV-Plus/services/tile_cache/Mandalay Myanmar, earthquake/leaflet_tiles/0"

os.makedirs(DEST, exist_ok=True)

for file in os.listdir(SOURCE):

    if file.startswith("._"):
        continue

    if not file.endswith(".png"):
        continue

    parts = file.replace(".png", "").split("_")

    # IMPORTANT:
    # tile_Y_X.png

    y = int(parts[1]) // 512
    x = int(parts[2]) // 512

    x_dir = os.path.join(DEST, str(x))
    os.makedirs(x_dir, exist_ok=True)

    src = os.path.join(SOURCE, file)
    dst = os.path.join(x_dir, f"{y}.png")

    shutil.copy(src, dst)

print("DONE")