import json
from pathlib import Path
from PIL import Image

# =========================================================
# CONFIG
# =========================================================

REGION = "Mandalay Myanmar, earthquake"

ROOT = Path(
    "/home/bossx918spy/Desktop/DeepGlobeAV-Plus"
)

# =========================================================
# PATHS
# =========================================================

INPUT_GEOJSON = (

    ROOT /

    f"services/roads/{REGION}/Myanmmar.geojson"
)

OUTPUT_GEOJSON = (

    ROOT /

    f"services/roads/{REGION}/roads_pixels.geojson"
)

TILES_DIR = (

    ROOT /

    f"services/tile_cache/{REGION}/tiles"
)

# =========================================================
# AUTO IMAGE SIZE
# =========================================================

files = (

    list(TILES_DIR.glob("*.png")) +

    list(TILES_DIR.glob("*.jpg"))
)

if not files:

    raise Exception("❌ NO TILES FOUND")

img = Image.open(files[0])

tile_w, tile_h = img.size

max_x = 0
max_y = 0

for f in files:

    parts = f.stem.split("_")

    nums = []

    for p in parts:

        if p.isdigit():

            nums.append(int(p))

    if len(nums) < 2:
        continue

    x = nums[-2]
    y = nums[-1]

    max_x = max(max_x, x)
    max_y = max(max_y, y)

IMAGE_WIDTH = max_x + tile_w
IMAGE_HEIGHT = max_y + tile_h

print("🖼 IMAGE SIZE:")
print("WIDTH :", IMAGE_WIDTH)
print("HEIGHT:", IMAGE_HEIGHT)

# =========================================================
# GEO BOUNDS
# =========================================================
#
# TOP LEFT
# lon = 96.0475
# lat = 22.0200
#
# BOTTOM RIGHT
# lon = 96.1350
# lat = 21.8700
#
# =========================================================

MIN_LON = 96.0475
MAX_LON = 96.1350

MIN_LAT = 21.8700
MAX_LAT = 22.0200

# =========================================================
# GEO -> PIXEL
# =========================================================

def geo_to_pixel(lon, lat):

    ####################################################
    # ORIGINAL PIXEL
    ####################################################

    x = (
        (lon - MIN_LON)
        /
        (MAX_LON - MIN_LON)
    ) * IMAGE_WIDTH

    y = (
        (MAX_LAT - lat)
        /
        (MAX_LAT - MIN_LAT)
    ) * IMAGE_HEIGHT

    ####################################################
    # SCALE ONLY
    ####################################################

    x = x * 1.42
    y = y * 1.54

    ####################################################
    # EXISTING 90° ANTICLOCKWISE
    ####################################################

    rx = y
    ry = IMAGE_WIDTH - x

    ####################################################
    # ADDITIONAL 90° CLOCKWISE
    ####################################################

    rx2 = IMAGE_WIDTH - ry
    ry2 = rx

    ####################################################
    # EXISTING VERTICAL FLIP
    ####################################################

    fx = rx2
    fy = IMAGE_HEIGHT - ry2

    ####################################################
    # ADD ONE MORE VERTICAL FLIP
    ####################################################

    final_x = fx
    final_y = IMAGE_HEIGHT - fy

    return [final_x, final_y]

# =========================================================
# CONVERT LINESTRING
# =========================================================

def convert_linestring(coords):

    converted = []

    for coord in coords:

        ################################################
        # GEOJSON FORMAT
        ################################################

        lon = coord[0]
        lat = coord[1]

        ################################################
        # DEBUG
        ################################################

        if lon < 90 or lon > 100:

            print("⚠️ BAD LON:", lon)

        if lat < 15 or lat > 30:

            print("⚠️ BAD LAT:", lat)

        ################################################
        # PIXEL
        ################################################

        pixel = geo_to_pixel(
            lon,
            lat
        )

        converted.append(pixel)

    ####################################################
    # DEBUG SAMPLE
    ####################################################

    if converted:

        print("📍 SAMPLE:", converted[0])

    return converted

# =========================================================
# CONVERT MULTILINESTRING
# =========================================================

def convert_multilinestring(lines):

    converted = []

    for line in lines:

        converted.append(

            convert_linestring(line)

        )

    return converted

# =========================================================
# LOAD GEOJSON
# =========================================================

with open(INPUT_GEOJSON, "r") as f:

    data = json.load(f)

print("📦 FEATURES:", len(data["features"]))

# =========================================================
# PROCESS
# =========================================================

new_features = []

for feature in data["features"]:

    geometry = feature.get("geometry")

    if geometry is None:
        continue

    gtype = geometry["type"]

    try:

        ################################################
        # LINESTRING
        ################################################

        if gtype == "LineString":

            new_geom = {

                "type": "LineString",

                "coordinates":

                    convert_linestring(

                        geometry["coordinates"]

                    )
            }

        ################################################
        # MULTILINESTRING
        ################################################

        elif gtype == "MultiLineString":

            new_geom = {

                "type": "MultiLineString",

                "coordinates":

                    convert_multilinestring(

                        geometry["coordinates"]

                    )
            }

        else:
            continue

        ################################################
        # NEW FEATURE
        ################################################

        new_feature = {

            "type": "Feature",

            "properties":

                feature.get("properties", {}),

            "geometry": new_geom
        }

        new_features.append(new_feature)

    except Exception as e:

        print("❌ ERROR:", e)

# =========================================================
# SAVE
# =========================================================

output = {

    "type": "FeatureCollection",

    "features": new_features
}

with open(OUTPUT_GEOJSON, "w") as f:

    json.dump(output, f)

print()
print("✅ DONE")
print("💾 SAVED:", OUTPUT_GEOJSON)
print("📦 FINAL FEATURES:", len(new_features))
