from core.navigation.path_planner import PathPlanner

graph_path = "services/graphs/city_graph.json"

planner = PathPlanner(graph_path)

start = (100, 100)
goal = (400, 400)

route = planner.astar(start, goal)

print("ROUTE:", route[:10], "..." if route else "No path")

