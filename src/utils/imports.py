from __future__ import annotations

import json
import os.path
import pandas as pd
from pandas import DataFrame

from instance_module.graph import import_graph, set_arcs_nominal_travel_times_and_capacities
from instance_module.instance import Instance, get_instance, print_total_free_flow_time
from instance_module.paths import get_arc_based_paths_with_features
from input_data import InstanceParameters
from instance_generator.computer import InstanceComputer

import warnings

WARNING = "the convert_dtype parameter is deprecated and will be removed in a future version"
warnings.filterwarnings("ignore", message=WARNING)


def get_not_simplified_instance(instance_params: InstanceParameters) -> Instance:
    """Constructs an instance from input data without simplification."""
    trips_df = import_trips_df(instance_params)
    graph = import_graph(instance_params)
    set_arcs_nominal_travel_times_and_capacities(graph, instance_params)
    arc_based_shortest_paths, nominal_travel_times, nominal_capacities = get_arc_based_paths_with_features(
        trips_df['path'].to_list(), graph)
    instance = get_instance(instance_params, arc_based_shortest_paths, nominal_travel_times, nominal_capacities,
                            trips_df['release_time'].tolist(), trips_df['deadline'].tolist(),
                            trips_df['path'].tolist(), trips_df["deadline"].tolist())
    print_total_free_flow_time(instance)
    return instance


def import_trips_df(instance_parameters: InstanceParameters) -> DataFrame:
    """Imports trip data from JSON and integrates route data, raising an error if mismatched."""
    path_to_instance = instance_parameters.path_to_instance
    if not os.path.exists(path_to_instance):
        InstanceComputer(instance_parameters).run()

    with open(path_to_instance, 'r') as file:
        data = json.load(file)

    # Extract and normalize trip data from JSON
    trip_data = [data.pop(key) for key in list(data.keys()) if key.startswith('trip_')]
    trips_df = pd.json_normalize(trip_data)
    print(f"Initial number of trips: {len(trips_df)}")

    path_to_routes = instance_parameters.path_to_routes
    with open(path_to_routes, 'r') as file:
        routes_data = json.load(file)

    relevant_keys = ['path', 'origin', 'destination', 'origin_coords', 'destination_coords']
    filtered_routes_data = [{key: route[key] for key in relevant_keys if key in route} for route in routes_data]

    routes_df = pd.DataFrame(filtered_routes_data)

    if len(routes_df) != len(trips_df):
        raise ValueError("The number of routes does not match the number of trips.")

    combined_df = pd.concat([trips_df, routes_df], axis=1)
    return combined_df
