import cv2
import numpy as np
import json
import os
from skimage.morphology import skeletonize

GRAPH_DIR = "services/graphs"

class RoadGraphBuilder:

    def build_graph(self, mask_path):
        print("🧠 Building road graph from:", mask_path)

        img = cv2.imread(mask_path, 0)
        binary = (img > 0).astype(np.uint8)

        # skeletonize roads
        skel = skeletonize(binary).astype(np.uint8)

        # find nodes (junctions)
        nodes = []
        h, w = skel.shape

        for y in range(1, h-1):
            for x in range(1, w-1):
                if skel[y, x]:
                    neighbors = np.sum(skel[y-1:y+2, x-1:x+2]) - 1
                    if neighbors > 2:  # intersection
                        nodes.append((x, y))

        # build edges
        edges = []
        visited = set()

        for y in range(h):
            for x in range(w):
                if skel[y, x] and (x, y) not in visited:
                    stack = [(x, y)]
                    segment = []

                    while stack:
                        cx, cy = stack.pop()
                        if (cx, cy) in visited:
                            continue
                        visited.add((cx, cy))
                        segment.append((cx, cy))

                        for nx in range(cx-1, cx+2):
                            for ny in range(cy-1, cy+2):
                                if 0 <= nx < w and 0 <= ny < h:
                                    if skel[ny, nx] and (nx, ny) not in visited:
                                        stack.append((nx, ny))

                    if len(segment) > 20:
                        edges.append(segment)

        graph = {
            "nodes": nodes,
            "edges": edges
        }

        name = os.path.basename(mask_path).replace("_mask.png", "_graph.json")
        save_path = os.path.join(GRAPH_DIR, name)

        with open(save_path, "w") as f:
            json.dump(graph, f)

        print("🛣 Graph saved:", save_path)
        return save_path
