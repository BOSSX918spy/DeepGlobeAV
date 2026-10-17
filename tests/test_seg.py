from core.tile_engine.stream_tiles import get_tile_from_coords
from core.segmentation.hailo_segment import HailoSegmentor

# chandigarh test coords
lat = 30.5164
lon = 76.6598

tile = get_tile_from_coords(lat, lon)

seg = HailoSegmentor()
mask = seg.segment_tile(tile)

print("DONE:", mask)
