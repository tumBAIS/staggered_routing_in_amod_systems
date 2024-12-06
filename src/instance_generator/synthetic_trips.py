import time

import pandas as pd
from inputData import InputData
from problem.network import Network
from shapely.geometry import Point


def get_synthetic_trips(instance_params: InputData, network: Network) -> list[dict]:
    """Creates a set of trips on a synthetic network with all equal release times and all equal origin-destination."""
    origin, destination = _find_extreme_points(network.gdf_nodes)
    origin_coords = _point_to_dict(origin.geometry)
    destination_coords = _point_to_dict(destination.geometry)
    origin = network.find_closest_node(origin.geometry)
    destination = network.find_closest_node(destination.geometry)

    trips = _generate_trips_list(network, instance_params.number_of_trips, origin_coords, destination_coords,
                                 origin, destination)
    return trips


def _generate_trips_list(network: Network, number_trips: int, origin_coords: dict, destination_coords: dict,
                         origin: int, destination: int) -> list[dict]:
    """Generates a list of dictionaries representing trips with specified parameters."""
    trips = []

    start_cpu_time = time.process_time()
    for trip_id in range(number_trips):
        paths = network.kspwlo_cpp(origin, destination)

        trip = {
            'release_time': 0,
            'origin_coords': origin_coords,
            'destination_coords': destination_coords,
            'trip_id': trip_id,
            "paths": paths
        }
        trips.append(trip)
    end_cpu_time = time.process_time()
    print(f"CPP CPU time: {end_cpu_time - start_cpu_time}")

    return trips


def _find_extreme_points(df: pd.DataFrame) -> (pd.Series, pd.Series):
    """Finds the most south-west and north-east points from a dataframe."""
    if df.empty or 'geometry' not in df.columns:
        return None, None

    min_point = df.loc[df.geometry.apply(lambda point: (point.x, point.y)).idxmin()]
    max_point = df.loc[df.geometry.apply(lambda point: (point.x, point.y)).idxmax()]

    return min_point, max_point


def _point_to_dict(point: Point) -> dict:
    """Convert Shapely Point to a dictionary."""
    return {'x': point.x, 'y': point.y}
