from core.navigation.city_mapper import CityMapper

lat = 30.5164
lon = 76.6598

mapper = CityMapper()

# radius=1 → 3x3 tiles
city_graph = mapper.build_area(lat, lon, radius=1)

print("CITY GRAPH:", city_graph)
