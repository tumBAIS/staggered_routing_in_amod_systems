import matplotlib
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import shapely
from shapely.wkt import loads
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.polygon import Polygon
from shapely.prepared import prep, PreparedGeometry
from shapely import LineString
import numpy as np
import os
from datetime import datetime, timedelta
from geopandas import GeoDataFrame
from pandas import DataFrame
import geopandas as gpd
import osmnx as osm
import json
import jsonpickle
from networkx.readwrite import json_graph
from networkx import MultiDiGraph
import contextily as ctx

from datetime import datetime
from shapely.geometry import Polygon, Point

matplotlib.use('Agg')  # Switch to Agg backend for non-GUI environments
import warnings

# To filter out only the specific warning message you can do:
warnings.filterwarnings("ignore", message="FigureCanvasAgg is non-interactive, and thus cannot be shown")


def split_long_edges(graph):
    def split_edge(u, v, key, length):
        attributes = graph[u][v][key]
        line: LineString = attributes['geometry']

        if length > 1000:
            # Split at two points for really long arcs
            first_point = line.interpolate(1 / 4, normalized=True)
            second_point = line.interpolate(2 / 4, normalized=True)
            third_point = line.interpolate(3 / 4, normalized=True)

            first_third = LineString([line.coords[0], first_point.coords[0]])
            second_third = LineString([first_point.coords[0], second_point.coords[0]])
            third_third = LineString([second_point.coords[0], third_point.coords[0]])
            foruth_third = LineString([third_point.coords[0], line.coords[-1]])

            points = [first_point, second_point, third_point]
            segments = [first_third, second_third, third_third, foruth_third]
        else:
            # Split at one midpoint for arcs longer than 500 meters but less than 1000 meters
            mid_point = line.interpolate(0.5, normalized=True)
            points = [mid_point]
            segments = [LineString([line.coords[0], mid_point.coords[0]]),
                        LineString([mid_point.coords[0], line.coords[-1]])]

        graph.remove_edge(u, v, key=key)

        # Split the edge based on the number of points (one or two)
        prev_point = u
        for point, segment in zip(points, segments):
            midpoint_id = max(graph.nodes) + 1
            graph.add_node(midpoint_id, x=point.x, y=point.y)
            graph.add_edge(prev_point, midpoint_id, length=segment.length, geometry=segment)
            prev_point = midpoint_id
        # Add the final segment
        graph.add_edge(prev_point, v, length=segments[-1].length, geometry=segments[-1])

    while True:
        max_length_edge = max((data['length'] for u, v, data in graph.edges(data=True)))
        if max_length_edge <= 150:
            print(f"max lenght edge: {max_length_edge}")
            break

        for u, v, key, data in list(graph.edges(keys=True, data=True)):
            length = data['length']
            if length > 150:
                split_edge(u, v, key, length)


from shapely.geometry import LineString, Point
import networkx as nx


def filter_rides_by_time(loadedDataset: pd.DataFrame, startTime: datetime, endTime: datetime) -> pd.DataFrame:
    """Filter rides by start and end times."""
    valid_rides = loadedDataset.loc[
        (loadedDataset["Trip_Pickup_DateTime"] >= startTime) &
        (loadedDataset["Trip_Dropoff_DateTime"] <= endTime) &
        (loadedDataset["Trip_Pickup_DateTime"] < loadedDataset["Trip_Dropoff_DateTime"])
        ]
    return valid_rides


def create_geodataframe(df: pd.DataFrame, lon_col: str, lat_col: str) -> gpd.GeoDataFrame:
    """Convert a DataFrame with longitude and latitude columns to a GeoDataFrame."""
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_col], df[lat_col], crs="EPSG:4326"))


def project_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Project a GeoDataFrame to a local metric CRS based on its bounds."""
    # Assuming osm.project_gdf is a valid function you have defined elsewhere that projects the GDF
    return osm.project_gdf(gdf, to_crs="epsg:32118")


def is_point_in_network(network_polygon: Polygon, point: Point) -> bool:
    """Check if a point is within a given network polygon."""
    return point.within(network_polygon)


def point_to_dict(point: Point) -> dict:
    """Convert a Shapely Point geometry to a dictionary format."""
    return {"x": point.x, "y": point.y}


def preprocess_times(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Convert datetime to timestamps and adjust them relative to the minimum departure time."""
    min_departure_time = gdf["Trip_Pickup_DateTime"].min()
    gdf["Trip_Pickup_DateTime"] = gdf["Trip_Pickup_DateTime"].apply(
        lambda x: int(x.timestamp() - min_departure_time.timestamp()))
    gdf["Trip_Dropoff_DateTime"] = gdf["Trip_Dropoff_DateTime"].apply(
        lambda x: int(x.timestamp() - min_departure_time.timestamp()))
    return gdf


def get_all_rides_in_network(startTime: datetime, endTime: datetime, loadedDataset: pd.DataFrame,
                             network_polygon: Polygon) -> gpd.GeoDataFrame:
    """Retrieve all rides within a network polygon and time range."""
    # Filter rides by time
    rides_df = filter_rides_by_time(loadedDataset, startTime, endTime)

    # Convert to GeoDataFrame for pickup points
    rides_gdf = create_geodataframe(rides_df, 'Start_Lon', 'Start_Lat')
    rides_gdf = project_gdf(rides_gdf, )
    rides_gdf = rides_gdf[rides_gdf.geometry.apply(lambda point: is_point_in_network(network_polygon, point))]

    if rides_gdf.empty:
        raise RuntimeError("No trips found")

    # Process pickup points
    rides_gdf["Projected Pickup Point"] = rides_gdf["geometry"].apply(point_to_dict)

    # Convert to GeoDataFrame for dropoff points
    rides_gdf = create_geodataframe(rides_gdf, 'End_Lon', 'End_Lat')
    rides_gdf = project_gdf(rides_gdf)
    rides_gdf = rides_gdf[rides_gdf.geometry.apply(lambda point: is_point_in_network(network_polygon, point))]
    rides_gdf.rename(columns={'geometry': 'Projected Dropoff Point'}, inplace=True)

    # Ensure pickup and dropoff points are not identical
    rides_gdf = rides_gdf[rides_gdf['Projected Pickup Point'] != rides_gdf["Projected Dropoff Point"]]
    rides_gdf["Projected Dropoff Point"] = rides_gdf["Projected Dropoff Point"].apply(point_to_dict)

    # Clean up the DataFrame
    rides_gdf = preprocess_times(rides_gdf)
    rides_gdf.drop(["Start_Lon", "Start_Lat", "End_Lon", "End_Lat"], axis=1, inplace=True)
    rides_gdf.reset_index(drop=True, inplace=True)

    print(f"Number of rides in network: {len(rides_gdf)}")
    return rides_gdf


def sampleRides(instanceGeoDataFrame, numberOfRides, seed) -> GeoDataFrame:
    if len(instanceGeoDataFrame) < numberOfRides:
        raise RuntimeError(f"max true rides that can be sampled is {len(instanceGeoDataFrame)}")
    instanceGeoDataFrame = instanceGeoDataFrame.sample(n=numberOfRides, random_state=seed).sort_values(
        by="Trip_Pickup_DateTime").reset_index(drop=True)
    return instanceGeoDataFrame


def getTimeFrame(day: int, t_min: int) -> (datetime, datetime):
    startTime: datetime = datetime(year=2015, month=1, day=day, hour=0, minute=0, second=0)
    endTime: datetime = datetime(year=2015, month=1, day=day, hour=23, minute=t_min - 1, second=59)
    return startTime, endTime


def save_dict_to_pretty_json(data, file_path):
    """
    Save a dictionary to a file in a pretty formatted JSON.

    Parameters:
    - data (dict): The dictionary to save.
    - file_path (str): The path of the file where the JSON should be saved.
    """
    with open(fr"{file_path}\instance.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# https://gist.github.com/nuthanmunaiah/523a5e112f1e1f458e2c
def _deserialize(file_path) -> MultiDiGraph:
    '''Function to _deserialize a NetworkX DiGraph from a JSON file.'''
    with open(file_path, 'r+') as _file:
        call_graph = json_graph.adjacency_graph(jsonpickle.decode(_file.read()), directed=True)
    return call_graph


def _serialize(call_graph, file_path):
    '''Function to serialize a NetworkX DiGraph to a JSON file.'''
    if not isinstance(call_graph, MultiDiGraph):
        raise Exception('call_graph has to be an instance of networkx.MultiDiGraph')

    with open(file_path, 'w+') as _file:
        _file.write(jsonpickle.encode(
            json_graph.adjacency_data(call_graph))
        )


def format_place(place: str) -> str:
    return place.lower().split(",")[0].replace(" ", "_")


def extract_largest_strongly_connected_component(graph):
    """
    Extract the largest strongly connected component from a directed graph.

    Parameters:
    - graph (nx.DiGraph): A directed graph.

    Returns:
    - largest_scc (nx.DiGraph): The largest strongly connected component of the graph.
    """
    # Find strongly connected components (SCCs) and sort them by size in descending order
    sccs = sorted(nx.strongly_connected_components(graph), key=len, reverse=True)
    # Get the largest SCC
    largest_scc_nodes = sccs[0]
    # Create a subgraph of the graph containing only the nodes in the largest SCC
    largest_scc = graph.subgraph(largest_scc_nodes).copy()

    return largest_scc


def plot_network_with_background_map(G, path_to_network):
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(10, 10))
    G = osm.project_graph(G, to_crs='epsg:3857')

    # Plot the edges
    edges = osm.graph_to_gdfs(G, nodes=False)
    nodes = osm.graph_to_gdfs(G, edges=False)
    edges.plot(ax=ax, linewidth=1, edgecolor='gray')
    nodes.plot(ax=ax, markersize=5, edgecolor='black', zorder=10)
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
    plt.axis("off")
    # Add basemap

    # # Set the axis limits to the graph's bounding box
    # west, south, east, north = edges.bounds
    # ax.set_xlim(west, east)
    # ax.set_ylim(south, north)

    # Save the figure as a JPEG file
    fig.savefig(fr"{path_to_network}\network.jpeg", dpi=300)


def get_network(place: str, replace: bool) -> MultiDiGraph:
    place_format = format_place(place)
    path_to_network = os.path.dirname(__file__) + rf"\data\{place_format}\\"

    if os.path.exists(path_to_network) and os.path.isfile(fr"{path_to_network}\network.json") and not replace:
        network = _deserialize(fr"{path_to_network}\network.json")
    else:
        os.makedirs(path_to_network, exist_ok=True)
        network = osm.graph_from_place(place, network_type="drive")
        network = extract_largest_strongly_connected_component(network)
        network = osm.project_graph(network, to_crs="epsg:32118")
        network = osm.consolidate_intersections(network, tolerance=25)
        split_long_edges(network)
        plot_network_with_background_map(network, path_to_network)
        max_length_edge = max((data['length'] for u, v, data in network.edges(data=True)))
        print(f"max_length_edge: {max_length_edge}")
        _serialize(network, fr"{path_to_network}\network.json")
    print(f"number of nodes: {len(network.nodes)}, edges: {len(network.edges)}")
    return network


def generate_random_trips(geodataframe: GeoDataFrame, n: int, t_min: int, seed: int = None) -> pd.DataFrame:
    if seed is not None:
        np.random.seed(seed)

    # Select n random origins and n random destinations
    origins_indices = np.random.choice(geodataframe.index, size=n, replace=True)
    destinations_indices = np.random.choice(geodataframe.index, size=n, replace=True)

    origins_projected = geodataframe.loc[origins_indices].copy().reset_index(drop=True)
    destinations_projected = geodataframe.loc[destinations_indices].copy().reset_index(drop=True)

    # Generate n random starting times between 0 and 3600 seconds
    pickup_datetimes = sorted([round(np.random.uniform(0, t_min * 60), 2) for _ in range(n)])
    dropoff_datetimes = [-1] * n  # Placeholder for Trip_Dropoff_DateTime

    # Create the final DataFrame
    trips_df = pd.DataFrame({
        'Trip_Pickup_DateTime': pickup_datetimes,
        'Trip_Dropoff_DateTime': dropoff_datetimes,
        'Projected Pickup Point': origins_projected.geometry,
        'Projected Dropoff Point': destinations_projected.geometry
    })
    trips_df["Projected Pickup Point"] = trips_df["Projected Pickup Point"].apply(lambda x: point_to_dict(x))
    trips_df["Projected Dropoff Point"] = trips_df["Projected Dropoff Point"].apply(lambda x: point_to_dict(x))

    return trips_df


def createInstance(type_of_instance: str, seed: int, t_min: int, number_of_rides: int, day: int, place: str):
    # t_min: time window expressed in minutes
    if type_of_instance not in ["all_true_rides", "sampled_true_rides", "synthetic"]:
        raise ValueError("choose correct type_of_instance: all_true_rides", "sampled_true_rides", "synthetic")

    network = get_network(place, replace=True)
    network_gdf = osm.graph_to_gdfs(network, edges=False)
    network_polygon: Polygon = network_gdf.unary_union.convex_hull
    print(f"Polygon area: {network_polygon.area / 1e6:.2f} km^2")

    if type_of_instance == "synthetic":
        rides = generate_random_trips(network_gdf, t_min=t_min, seed=seed, n=number_of_rides)
    else:
        loadedDataset = pd.read_parquet(f"data/YellowTripData2015-01/YellowTripData2015-01-{day:02d}.parquet")
        startTime, endTime = getTimeFrame(day=day, t_min=t_min)
        rides = get_all_rides_in_network(startTime, endTime, loadedDataset, network_polygon)
        if type_of_instance == "sampled_true_rides":
            rides = sampleRides(rides, number_of_rides, seed=seed)
    file_directory = os.path.dirname(
        __file__) + rf"\data\{format_place(place)}\{type_of_instance}\{t_min}_minutes\{number_of_rides}_rides\day_{day}\seed_{seed}"
    if not os.path.exists(file_directory):
        os.makedirs(file_directory, exist_ok=True)
    instance_dict = rides.to_dict()
    save_dict_to_pretty_json(instance_dict, file_directory)

    print(fr"saved instance {format_place(place)}\{t_min}_minutes\{number_of_rides}_rides\day_{day}\seed_{seed}")


def get_manhattan_polygon_prepared() -> PreparedGeometry:
    manhattanMultipolygon: str = pd.read_csv("ManhattanBoundaries.csv").iloc[
        1, 0]  # string with lat/long of manhattan boundaries
    manhattanGeometry: MultiPolygon = loads(manhattanMultipolygon)  # convert string to geometry object
    listManhattanPolygons: list[Polygon] = list(manhattanGeometry.geoms)
    listAreasOfPolygons = [poly.area for poly in listManhattanPolygons]
    idx = np.argmax(listAreasOfPolygons)  # get index of polygon with largest area
    manhattanPolygon: Polygon = listManhattanPolygons[idx]

    # A geometry prepared for efficient comparison to a set of other geometries.
    manhattanPolygonPrepared: PreparedGeometry = prep(manhattanPolygon)
    return manhattanPolygonPrepared


if __name__ == "__main__":
    place = "Little Italy, Manhattan, New York"
    createInstance(type_of_instance="synthetic", t_min=0, seed=0, day=1, number_of_rides=50, place=place)
    print("operation completed!")
