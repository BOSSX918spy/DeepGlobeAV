import os
import requests
from config.settings import MAPTILER_KEY, ZOOM_LEVEL

CACHE_DIR = "services/tile_cache"

def deg2num(lat, lon, zoom):
    """Convert lat/lon to tile numbers"""
    import math
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + 
            (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return xtile, ytile

def download_tile(x, y, z):
    url = f"https://api.maptiler.com/tiles/satellite-v2/{z}/{x}/{y}.jpg?key={MAPTILER_KEY}"
    path = f"{CACHE_DIR}/{z}_{x}_{y}.jpg"

    if os.path.exists(path):
        print("Tile cached:", path)
        return path

    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        with open(path, "wb") as f:
            f.write(r.content)
        print("Downloaded:", path)
        return path
    else:
        print("Tile download failed", r.status_code)
        return None

def get_tile_from_coords(lat, lon):
    x, y = deg2num(lat, lon, ZOOM_LEVEL)
    return download_tile(x, y, ZOOM_LEVEL)

if __name__ == "__main__":
    # test coordinates (change later)
    lat = 30.7333   # chandigarh area
    lon = 76.7794

    tile = get_tile_from_coords(lat, lon)
    print("Tile saved:", tile)
