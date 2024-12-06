from __future__ import annotations

import json
import os.path
import pandas as pd
from pandas import DataFrame

from processing.shortcuts import add_shortcuts
from instance_module.graph import import_graph, reduce_graph, set_arcs_nominal_travel_times_and_capacities
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
    reduce_graph(graph, trips_df['path'])

    node_based_shortest_paths = add_shortcuts(instance_params, graph, trips_df, trips_df['path'])
    set_arcs_nominal_travel_times_and_capacities(graph, instance_params)

    arc_based_shortest_paths, arcs_features = get_arc_based_paths_with_features(node_based_shortest_paths, graph)
    instance = get_instance(instance_params, arc_based_shortest_paths, arcs_features, trips_df['release_time'].tolist(),
                            trips_df['deadline'].tolist())

    print_total_free_flow_time(instance)
    instance.set_deadlines(trips_df['deadline'].tolist())
    instance.set_max_staggering_applicable()
    instance.check_optional_fields()
    return instance


def import_trips_df(input_data: InstanceParameters) -> DataFrame:
    """Imports trip data from JSON and integrates route data, raising an error if mismatched."""
    path_to_instance = input_data.path_to_instance
    if not os.path.exists(path_to_instance):
        InstanceComputer(input_data).run()

    with open(path_to_instance, 'r') as file:
        data = json.load(file)

    # Extract and normalize trip data from JSON
    trip_data = [data.pop(key) for key in list(data.keys()) if key.startswith('trip_')]
    trips_df = pd.json_normalize(trip_data)
    print(f"Initial number of trips: {len(trips_df)}")

    path_to_routes = input_data.path_to_routes
    with open(path_to_routes, 'r') as file:
        routes_data = json.load(file)

    relevant_keys = ['path', 'origin', 'destination', 'origin_coords', 'destination_coords']
    filtered_routes_data = [{key: route[key] for key in relevant_keys if key in route} for route in routes_data]

    routes_df = pd.DataFrame(filtered_routes_data)

    if len(routes_df) != len(trips_df):
        raise ValueError("The number of routes does not match the number of trips.")

    combined_df = pd.concat([trips_df, routes_df], axis=1)
    return combined_df
