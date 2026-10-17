import json
import math
import heapq

class PathPlanner:

    def __init__(self, graph_path):
        with open(graph_path) as f:
            graph = json.load(f)

        self.nodes = graph["nodes"]
        self.edges = graph["edges"]

        # convert edges to adjacency list
        self.adj = {}
        for edge in self.edges:
            for i in range(len(edge)-1):
                a = tuple(edge[i])
                b = tuple(edge[i+1])

                self.adj.setdefault(a, []).append(b)
                self.adj.setdefault(b, []).append(a)

    def heuristic(self, a, b):
        return math.hypot(a[0]-b[0], a[1]-b[1])

    def find_nearest_node(self, point):
        px, py = point
        return min(self.adj.keys(),
                   key=lambda n: math.hypot(n[0]-px, n[1]-py))

    def astar(self, start, goal):
        start = self.find_nearest_node(start)
        goal = self.find_nearest_node(goal)

        open_set = []
        heapq.heappush(open_set, (0, start))

        came_from = {}
        g_score = {start: 0}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                return path[::-1]

            for neighbor in self.adj.get(current, []):
                tentative = g_score[current] + self.heuristic(current, neighbor)

                if tentative < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative
                    f_score = tentative + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score, neighbor))

        return None
