from core.tile_engine.stream_tiles import get_tile_from_coords
from core.segmentation.hailo_segment import HailoSegmentor
from core.vector_engine.road_graph import RoadGraphBuilder

lat = 30.7333
lon = 76.7794

tile = get_tile_from_coords(lat, lon)

seg = HailoSegmentor()
mask = seg.segment_tile(tile)

builder = RoadGraphBuilder()
graph = builder.build_graph(mask)

print("FINAL GRAPH:", graph)
