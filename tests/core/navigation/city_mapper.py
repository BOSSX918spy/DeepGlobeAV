import json
import os

from core.tile_engine.stream_tiles import deg2num, download_tile
from core.segmentation.hailo_segment import HailoSegmentor
from core.vector_engine.road_graph import RoadGraphBuilder
from config.settings import ZOOM_LEVEL

GRAPH_DIR = "services/graphs"

class CityMapper:

    def __init__(self):
        self.segmentor = None
        self.graph_builder = RoadGraphBuilder()

    def build_area(self, lat, lon, radius=1):
        print("🌍 Building area graph...")

        center_x, center_y = deg2num(lat, lon, ZOOM_LEVEL)

        full_graph = {
            "nodes": [],
            "edges": []
        }

        for dx in range(-radius, radius+1):
            for dy in range(-radius, radius+1):

                x = center_x + dx
                y = center_y + dy

                tile_path = download_tile(x, y, ZOOM_LEVEL)
                if not tile_path:
                    continue

                mask_path = self.segmentor.segment_tile(tile_path)
                graph_path = self.graph_builder.build_graph(mask_path)

                with open(graph_path) as f:
                    tile_graph = json.load(f)

                full_graph["nodes"].extend(tile_graph["nodes"])
                full_graph["edges"].extend(tile_graph["edges"])

        save_path = os.path.join(GRAPH_DIR, "city_graph.json")
        with open(save_path, "w") as f:
            json.dump(full_graph, f)

        print("🏙 City graph saved:", save_path)
        return save_path
