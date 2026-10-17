from flask import Flask, jsonify, send_from_directory
import threading
import time
import os
import json
from datetime import datetime
from queue import Queue, Empty
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from core.tile_engine.stream_tiles import deg2num, num2deg, download_tile
from core.segmentation.hailo_segment import HailoSegmentor
from config.settings import ZOOM_LEVEL

app = Flask(__name__, static_folder="../frontend", static_url_path="")

# ======================
# GLOBAL STATE
# ======================
running_flag = {"run": False}

stats = {
    "fps": 0,
    "latency": 0,
    "tiles_processed": 0,
    "status": "idle"
}

# ======================
# INIT HAILO (ONCE)
# ======================
segmentor = HailoSegmentor()

# ======================
# OUTPUT DIR
# ======================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(BASE_DIR, "../../services/masks/json")

os.makedirs(JSON_DIR, exist_ok=True)

# ======================
# SAVE JSON ONLY (PNG already saved by Hailo)
# ======================
def save_json(mask_path, lat, lon):

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    name = f"{lat:.6f}_{lon:.6f}_{timestamp}.json"
    json_path = os.path.join(JSON_DIR, name)

    data = {
        "lat": lat,
        "lon": lon,
        "mask_file": mask_path
    }

    with open(json_path, "w") as f:
        json.dump(data, f)

# ======================
# TILE PIPELINE
# ======================
tile_queue = Queue(maxsize=20)

start_lat, start_lon = 30.7333, 76.7794
start_x, start_y = deg2num(start_lat, start_lon, ZOOM_LEVEL)

GRID_SIZE = 20

# ======================
# PRODUCER
# ======================
def tile_producer():

    for dx in range(GRID_SIZE):
        for dy in range(GRID_SIZE):

            if not running_flag["run"]:
                return

            x = start_x + dx
            y = start_y + dy

            tile_path = download_tile(x, y, ZOOM_LEVEL)

            if tile_path:
                lat, lon = num2deg(x, y, ZOOM_LEVEL)
                tile_queue.put((tile_path, lat, lon))

# ======================
# CONSUMER
# ======================
def tile_consumer():

    while running_flag["run"]:

        try:
            tile_path, lat, lon = tile_queue.get(timeout=1)
        except Empty:
            continue

        start = time.time()

        # 🔥 YOUR EXISTING HAILO CALL (UNCHANGED)
        mask_path = segmentor.segment_tile(tile_path)

        # save metadata JSON
        save_json(mask_path, lat, lon)

        latency = time.time() - start

        stats["fps"] = round(1 / latency, 2) if latency > 0 else 0
        stats["latency"] = round(latency, 3)
        stats["tiles_processed"] += 1
        stats["status"] = "running"

# ======================
# MAIN LOOP
# ======================
def segmentation_loop():

    t1 = threading.Thread(target=tile_producer)
    t2 = threading.Thread(target=tile_consumer)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

# ======================
# ROUTES
# ======================
@app.route("/")
def serve_ui():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/stats")
def get_stats():
    return jsonify(stats)

@app.route("/start")
def start():
    if not running_flag["run"]:
        running_flag["run"] = True
        stats["status"] = "running"

        t = threading.Thread(target=segmentation_loop)
        t.start()

    return "started"

@app.route("/stop")
def stop():
    running_flag["run"] = False
    stats["status"] = "stopped"
    return "stopped"

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)