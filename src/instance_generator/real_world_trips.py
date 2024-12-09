import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import datetime, timedelta
import osmnx as osm
from shapely.geometry import Point

from input_data import InstanceParameters
from problem.network import Network
from problem.parameters import InstanceParams
import matplotlib.pyplot as plt
import networkx as nx
import warnings

# Suppress specific FutureWarning from GeoPandas
warnings.filterwarnings("ignore",
                        message="the convert_dtype parameter is deprecated and will be removed in a future version")

LAT_LON_CRS = "EPSG:4326"
WEB_MERCATOR_CRS = "EPSG:3857"
DEPARTURE_GITTERING = 2  # minutes
COORDS_GITTERING = 250  # meters
GITTERING_SEED = 42


def _plot_od_pairs(network: Network, dataset_gdf: gpd.GeoDataFrame, path_to_instance: Path, plot_flag: bool = False):
    """Plot and save the network and origin-destination pairs."""
    if not plot_flag:
        return
    origin_gdf = gpd.GeoDataFrame({
        'origin': dataset_gdf['origin_coords'].apply(lambda x: Point(x['x'], x['y']))})
    origin_gdf = origin_gdf.set_geometry(col="origin", crs=WEB_MERCATOR_CRS)
    destination_gdf = gpd.GeoDataFrame({
        'destination': dataset_gdf['destination_coords'].apply(lambda x: Point(x['x'], x['y']))
    })
    destination_gdf = destination_gdf.set_geometry(col="destination", crs=WEB_MERCATOR_CRS)

    fig, ax = plt.subplots(figsize=(12, 12))

    # Plot the network
    network_graph = nx.MultiDiGraph(network.G)
    osm.plot_graph(network_graph, ax=ax, show=False, close=False, edge_color='gray', node_size=0)

    # Plot the origin points
    origin_gdf.plot(ax=ax, color='blue', alpha=0.7, markersize=10, label='Origins')

    # Plot the destination points
    destination_gdf.plot(ax=ax, color='red', alpha=0.7, markersize=10, label='Destinations')

    # Plot the row index as labels for origin-destination pairs
    for idx, row in dataset_gdf.iterrows():
        origin = row['origin_coords']
        destination = row['destination_coords']
        ax.text(origin['x'], origin['y'], str(idx), fontsize=8, color='blue', alpha=0.7)
        ax.text(destination['x'], destination['y'], str(idx), fontsize=8, color='red', alpha=0.7)

    plt.legend()
    plt.title('Network with Origin-Destination Pairs')
    plt.savefig(path_to_instance.parent / "od_pairs.jpeg", dpi=300)
    plt.close()


def get_real_world_trips(instance_parameters: InstanceParameters, network: Network) -> list[dict]:
    """Retrieve all trips within a network polygon and time range."""
    dataset = _load_dataset(instance_parameters)
    dataset = _filter_dataset_by_time(dataset, instance_parameters)

    dataset_gdf = _convert_dataset_to_gdf(dataset, lon_col="Start_Lon", lat_col="Start_Lat")
    dataset_gdf = _filter_trips_not_in_network(dataset_gdf, network)
    dataset_gdf["origin_coords"] = dataset_gdf["geometry"]

    dataset_gdf = _convert_dataset_to_gdf(dataset_gdf, lon_col='End_Lon', lat_col='End_Lat')
    dataset_gdf = _filter_trips_not_in_network(dataset_gdf, network)
    dataset_gdf["destination_coords"] = dataset_gdf["geometry"]

    # Vectorized finding of closest nodes
    dataset_gdf["origin"] = dataset_gdf["origin_coords"].apply(network.find_closest_node)
    dataset_gdf["destination"] = dataset_gdf["destination_coords"].apply(network.find_closest_node)
    dataset_gdf = dataset_gdf[dataset_gdf['origin'] != dataset_gdf["destination"]]

    # Sample
    dataset_gdf = sample_dataset(dataset_gdf, instance_parameters)

    # END SELECTION -- START COMPUTATION #

    # Vectorized computation of shortest paths
    # Compute n-shortest paths for each row
    dataset_gdf['path'] = dataset_gdf.apply(lambda row: find_shortest_path(row, network),
                                            axis=1)

    # Calculate the length of each path in the paths list, store these as tuples (length, path)
    dataset_gdf['path_length'] = dataset_gdf['path'].apply(lambda path: network.compute_path_length(path))

    # Filter out rows where the shortest path is 350 or less
    dataset_gdf = dataset_gdf[dataset_gdf["path_length"] > 350]  # FILTER OUT SHORT PATHS

    dataset_gdf["origin_coords"] = dataset_gdf["origin_coords"].apply(_point_to_dict)
    dataset_gdf["destination_coords"] = dataset_gdf["destination_coords"].apply(_point_to_dict)
    # Set minimum release time
    dataset_gdf = _preprocess_real_world_times(dataset_gdf)
    _plot_od_pairs(network, dataset_gdf, instance_parameters.path_to_instance, plot_flag=False)
    # Replicate and sort DataFrame
    dataset_gdf = dataset_gdf.sort_values(by=["release_time"])
    dataset_gdf.reset_index(drop=True, inplace=True)
    dataset_gdf["trip_id"] = dataset_gdf.index

    print(f"Number of trips in network: {len(dataset_gdf)}")
    columns_to_drop = ["Start_Lon", "Start_Lat", "End_Lat", "End_Lon", "Trip_Pickup_DateTime", "Trip_Dropoff_DateTime",
                       "geometry"]
    dataset_gdf.drop(columns=columns_to_drop, axis=1, inplace=True)

    # Summarize the generated trips
    num_trips = len(dataset_gdf)
    avg_trip_length = dataset_gdf['path_length'].mean()
    num_unique_origins = dataset_gdf['origin'].nunique()
    num_unique_destinations = dataset_gdf['destination'].nunique()
    print(f"Trip generation complete! Returning data.")
    print(f"Trip Generation Summary")
    print("-" * 60)
    print(f"Total Number of Trips: {num_trips}")
    print(f"Average Trip Length (meters): {avg_trip_length:.2f}")
    print(f"Number of Unique Origins: {num_unique_origins}")
    print(f"Number of Unique Destinations: {num_unique_destinations}")
    print("=" * 60 + "\n")

    return dataset_gdf.to_dict("records")


def sample_dataset(dataset_gdf, instance_parameters) -> gpd.GeoDataFrame:
    len_before = dataset_gdf.shape[0]
    # Check if the sample size is greater than the size of the DataFrame
    if instance_parameters.number_of_trips > len_before:
        # Enable resampling by setting replace=True
        dataset_gdf = dataset_gdf.sample(n=instance_parameters.number_of_trips, replace=True,
                                         random_state=instance_parameters.seed)
    else:
        dataset_gdf = dataset_gdf.sample(n=instance_parameters.number_of_trips, random_state=instance_parameters.seed)
    len_after = dataset_gdf.shape[0]

    # Print the number of rows before and after sampling
    print(f"Length before sampling: {len_before}")
    print(f"Length after sampling: {len_after}")

    # Calculate the difference in length
    change_in_length = len_before - len_after

    # Print the change in length
    print(f"Change in number of rows: {change_in_length}")
    return dataset_gdf


def _move_point_within_radius(point: Point, radius: float, rng: np.random.Generator) -> Point:
    """Move a point randomly within a given radius."""
    angle = rng.uniform(0, 2 * np.pi)
    distance = rng.uniform(0, radius)
    delta_x = distance * np.cos(angle)
    delta_y = distance * np.sin(angle)
    return Point(point.x + delta_x, point.y + delta_y)


def _point_to_dict(point: Point) -> dict[str, float]:
    """Convert a Shapely Point geometry to a dictionary format."""
    return {"x": point.x, "y": point.y}


# Define the function to find the closest node for a given coordinate
def find_origin_node(row, network):
    return network.find_closest_node(row['origin_coords'])


def find_destination_node(row, network):
    return network.find_closest_node(row['destination_coords'])


def find_shortest_path(row, network: Network):
    # Get all shortest paths of the same length
    all_shortest_paths = list(nx.all_shortest_paths(
        network.G,
        source=row['origin'],
        target=row['destination'],
        weight='length'
    ))

    # Select the shortest path with the fewest arcs
    optimal_path = min(all_shortest_paths, key=len)
    return optimal_path


def _filter_trips_not_in_network(gdf: gpd.GeoDataFrame, network: Network) -> gpd.GeoDataFrame:
    """Filter trips that are not within the network polygon."""
    # Create a GeoSeries with the network polygon
    network_polygon = gpd.GeoSeries([network.polygon], crs=gdf.crs)

    # Use spatial indexing for efficient spatial queries
    spatial_index = gdf.sindex

    # Find all points within the network polygon using spatial indexing
    possible_matches_index = list(spatial_index.intersection(network_polygon.total_bounds))
    possible_matches = gdf.iloc[possible_matches_index]

    precise_matches = possible_matches[possible_matches.within(network_polygon.iloc[0])]

    if precise_matches.empty:
        raise RuntimeError("No trips found")

    return precise_matches


def _convert_dataset_to_gdf(dataset: pd.DataFrame, lon_col: str, lat_col: str) -> gpd.GeoDataFrame:
    """Convert a DataFrame with longitude and latitude columns to a GeoDataFrame in web mercator CRS."""
    gdf = gpd.GeoDataFrame(dataset, geometry=gpd.points_from_xy(dataset[lon_col], dataset[lat_col], crs=LAT_LON_CRS))
    return osm.project_gdf(gdf, to_crs=WEB_MERCATOR_CRS)


def _load_dataset(instance_params: InstanceParameters) -> pd.DataFrame:
    """Load TLC data relative to Manhattan."""
    tlc_folder_name = "YellowTripDataManhattan2015-01"
    path_to_repo = Path(__file__).resolve().parents[2]
    path_to_real_world_data = path_to_repo / "data" / tlc_folder_name
    file_path = path_to_real_world_data / f"{tlc_folder_name}-{instance_params.day:02d}.parquet"

    if not file_path.exists():
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    loaded_df = pd.read_parquet(file_path)
    columns_to_drop = ["travelTime", "Projected Pickup Point", "Projected Dropoff Point"]

    return loaded_df.drop(columns=columns_to_drop, axis=1)


def _preprocess_real_world_times(trips_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Convert datetime to timestamps and adjust them relative to the minimum departure time."""
    min_departure_time = trips_gdf["Trip_Pickup_DateTime"].min()
    trips_gdf["release_time"] = trips_gdf["Trip_Pickup_DateTime"].apply(
        lambda x: float(x.timestamp() - min_departure_time.timestamp()))
    trips_gdf["Trip_Dropoff_DateTime"] = trips_gdf["Trip_Dropoff_DateTime"].apply(
        lambda x: float(x.timestamp() - min_departure_time.timestamp()))
    return trips_gdf


def _filter_dataset_by_time(loaded_dataset: pd.DataFrame, instance_params: InstanceParameters) -> pd.DataFrame:
    """Filter trips by start and end times."""
    start_time = datetime(year=2015, month=1, day=instance_params.day, hour=16, minute=0, second=0)
    end_time = datetime(year=2015, month=1, day=instance_params.day, hour=16, minute=59, second=59)
    valid_trips = loaded_dataset[(loaded_dataset["Trip_Pickup_DateTime"] >= start_time) &
                                 (loaded_dataset["Trip_Dropoff_DateTime"] <= end_time) &
                                 (loaded_dataset["Trip_Pickup_DateTime"] < loaded_dataset["Trip_Dropoff_DateTime"])]
    return valid_trips
