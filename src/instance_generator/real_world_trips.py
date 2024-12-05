import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import datetime, timedelta
import osmnx as osm
from shapely.geometry import Point
from problem.network import Network
from problem.parameters import InstanceParams
import matplotlib.pyplot as plt
import networkx as nx
import kspwlo

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


def get_real_world_trips(instance_parameters: InstanceParams, network: Network) -> list[dict]:
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

    # Scale demand by adding new trips
    new_trips = _scale_demand(dataset_gdf, instance_parameters, network)
    dataset_gdf = pd.concat([dataset_gdf, new_trips], ignore_index=True)

    # END SELECTION -- START COMPUTATION #
    dataset_gdf = _preprocess_real_world_times(dataset_gdf)

    # Vectorized computation of shortest paths
    _, kspwlo_computer = _get_kspwlo_computer_cpp(network)
    # Compute n-shortest paths for each row
    dataset_gdf['paths'] = dataset_gdf.apply(
        lambda row: find_n_shortest_paths(row, network, kspwlo_computer),
        axis=1
    )

    # Calculate the length of each path in the paths list, store these lists of tuples (length, path)
    dataset_gdf['paths_with_lengths'] = dataset_gdf['paths'].apply(
        lambda paths: [(network.compute_path_length(path), path) for path in paths]
    )

    # Sort the paths for each row by path length
    dataset_gdf['paths_with_lengths'] = dataset_gdf['paths_with_lengths'].apply(
        lambda path_list: sorted(path_list, key=lambda x: x[0])
    )

    # Optionally, if you want to store the shortest path length in a separate column
    dataset_gdf["length_shortest_path"] = dataset_gdf['paths_with_lengths'].apply(
        lambda paths: paths[0][0] if paths else None
    )

    # Filter out rows where the shortest path is 350 or less
    dataset_gdf = dataset_gdf[dataset_gdf["length_shortest_path"] > 350]  # FILTER OUT SHORT PATHS

    # Update the 'paths' column to only include sorted paths (without lengths)
    dataset_gdf['paths'] = dataset_gdf['paths_with_lengths'].apply(
        lambda paths: [path for _, path in paths]
    )

    # Remove the 'paths_with_lengths' column if it's no longer needed
    dataset_gdf.drop(columns=['paths_with_lengths'], inplace=True)

    dataset_gdf["origin_coords"] = dataset_gdf["origin_coords"].apply(_point_to_dict)
    dataset_gdf["destination_coords"] = dataset_gdf["destination_coords"].apply(_point_to_dict)
    _plot_od_pairs(network, dataset_gdf, instance_parameters.path_to_instance, plot_flag=False)

    # Replicate and sort DataFrame
    dataset_gdf = dataset_gdf.sort_values(by=["release_time"])
    dataset_gdf.reset_index(drop=True, inplace=True)
    dataset_gdf["trip_id"] = dataset_gdf.index

    print(f"Number of trips in network: {len(dataset_gdf)}")
    columns_to_drop = ["Start_Lon", "Start_Lat", "End_Lat", "End_Lon", "Trip_Pickup_DateTime", "Trip_Dropoff_DateTime",
                       "geometry", "length_shortest_path"]
    dataset_gdf.drop(columns=columns_to_drop, axis=1, inplace=True)

    # Summarize the generated trips
    num_trips = len(dataset_gdf)
    avg_trip_length = dataset_gdf['paths'].apply(lambda paths: network.compute_path_length(paths[0])).mean()
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


def _scale_demand(dataset_gdf: pd.DataFrame, instance_parameters: InstanceParams, network: Network,
                  gittering_seed: int = 42) -> pd.DataFrame:
    """Scale the demand in the dataset by creating additional copies of trips."""

    # Create a separate random generator instance with its own seed
    rng = np.random.default_rng(seed=gittering_seed)

    new_trips = []
    for _, trip in dataset_gdf.iterrows():
        # Append the original trip first
        new_trips.append(trip)

        # Create (demand_factor - 1) new trips based on the original trip
        for _ in range(int(instance_parameters.demand_factor) - 1):
            new_trip = trip.copy()

            # Generate a random total adjustment time within the range of -5 to +5 minutes
            total_seconds = rng.integers(-DEPARTURE_GITTERING * 60, DEPARTURE_GITTERING * 60 + 1)

            # Convert numpy.int64 to a regular Python int
            time_adjustment = timedelta(seconds=int(total_seconds))
            new_trip["Trip_Pickup_DateTime"] = trip["Trip_Pickup_DateTime"] + time_adjustment

            # Adjust origin and destination by moving them randomly within a 500-meter radius
            new_trip["origin_coords"] = _move_point_within_radius(trip["origin_coords"], 500, rng)
            new_trip["destination_coords"] = _move_point_within_radius(trip["destination_coords"], 500, rng)

            # Update origin and destination nodes
            new_trip["origin"] = network.find_closest_node(new_trip["origin_coords"])
            new_trip["destination"] = network.find_closest_node(new_trip["destination_coords"])

            if new_trip["origin"] != new_trip["destination"]:
                new_trips.append(new_trip)

    # Create a new DataFrame from the new_trips list
    new_trips_df = pd.DataFrame(new_trips)

    return new_trips_df


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


def find_n_shortest_paths(row, network: Network, kspwlo_computer):
    return run_kspwlo_cpp(source=row['origin'], target=row['destination'], network=network,
                          kspwlo_computer=kspwlo_computer)


def _get_kspwlo_computer_cpp(network: Network) -> (kspwlo.RoadNetwork, kspwlo.PathComputer):
    """Represent graph as a list of lists of floats.
    The first list specifies numNodes and numEdges, the remaining lists are origin/destination/weights of the arcs."""
    cpp_rn_constructor = [[network.G.number_of_nodes(), network.G.number_of_edges()]]

    for edge in network.G.edges(data=True):
        # Assuming edge data contains 'length' as weight
        u, v = edge[0], edge[1]
        length = edge[2].get('length', 0.0)  # Default to 0.0 if 'length' is not present
        cpp_edge = [u, v, float(length)]
        cpp_rn_constructor.append(cpp_edge)

    road_network = kspwlo.RoadNetwork(cpp_rn_constructor)
    return road_network, kspwlo.PathComputer(road_network)


def _run_kspwlo_computer(source, target, instance_params: InstanceParams, kspwlo_computer: kspwlo.PathComputer):
    k = instance_params.num_alternative_paths
    theta = float(instance_params.path_similarity_theta)

    if instance_params.kspwlo_algo == "onepass":
        return kspwlo_computer.onepass(source, target, k, theta)
    elif instance_params.kspwlo_algo == "multipass":
        return kspwlo_computer.multipass(source, target, k, theta)
    elif instance_params.kspwlo_algo == "svp_plus":
        return kspwlo_computer.svp_plus(source, target, k, theta)
    elif instance_params.kspwlo_algo == "onepass_plus":
        return kspwlo_computer.onepass_plus(source, target, k, theta)
    elif instance_params.kspwlo_algo == "esx":
        return kspwlo_computer.esx(source, target, k, theta)
    elif instance_params.kspwlo_algo == "esx_complete":
        return kspwlo_computer.esx_complete(source, target, k, theta)
    elif instance_params.kspwlo_algo == "svp_plus_complete":
        return kspwlo_computer.svp_plus_complete(source, target, k, theta)
    else:
        raise ValueError(f"Unknown algorithm: {instance_params.kspwlo_algo}")


def run_kspwlo_cpp(network, source: int, target: int, kspwlo_computer) -> list[list[int]]:
    if (source, target) in network.shortest_path_map:
        return network.shortest_path_map[source, target]

    kspwlo_result = _run_kspwlo_computer(source, target, network.instance_params, kspwlo_computer)
    paths = [x.nodes for x in sorted(kspwlo_result, key=lambda x: x.length)]  # from shortest to longest

    network.shortest_path_map[source, target] = paths

    return paths


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


def _load_dataset(instance_params: InstanceParams) -> pd.DataFrame:
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


def _preprocess_real_world_times(trips_gdf: pd.DataFrame) -> pd.DataFrame:
    """Convert datetime to timestamps and adjust them relative to the minimum departure time."""
    min_departure_time = trips_gdf["Trip_Pickup_DateTime"].min()
    trips_gdf["release_time"] = trips_gdf["Trip_Pickup_DateTime"].apply(
        lambda x: float(x.timestamp() - min_departure_time.timestamp()))
    trips_gdf["Trip_Dropoff_DateTime"] = trips_gdf["Trip_Dropoff_DateTime"].apply(
        lambda x: float(x.timestamp() - min_departure_time.timestamp()))
    return trips_gdf


def _filter_dataset_by_time(loaded_dataset: pd.DataFrame, instance_params: InstanceParams) -> pd.DataFrame:
    """Filter trips by start and end times."""
    start_time = datetime(year=2015, month=1, day=instance_params.day, hour=16, minute=0, second=0)
    end_time = datetime(year=2015, month=1, day=instance_params.day, hour=16, minute=59, second=59)
    valid_trips = loaded_dataset[(loaded_dataset["Trip_Pickup_DateTime"] >= start_time) &
                                 (loaded_dataset["Trip_Dropoff_DateTime"] <= end_time) &
                                 (loaded_dataset["Trip_Pickup_DateTime"] < loaded_dataset["Trip_Dropoff_DateTime"])]
    return valid_trips
