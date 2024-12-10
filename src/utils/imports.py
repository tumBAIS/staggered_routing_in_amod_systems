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
from dataclasses import dataclass
import warnings

WARNING = "the convert_dtype parameter is deprecated and will be removed in a future version"
warnings.filterwarnings("ignore", message=WARNING)


@dataclass
class TripsData:
    routes: list[list[int]]  # list of node-based paths for each trip
    deadline: list[int]  # Deadlines for each trip
    release_time: list[int]  # Release times for each trip


def get_instance(instance_params: InstanceParameters) -> Instance:
    """Constructs an instance from input data without simplification."""
    trips_data = import_trips_data(instance_params)
    graph = import_graph(instance_params)
    set_arcs_nominal_travel_times_and_capacities(graph, instance_params)
    trip_routes, travel_times_arcs, capacities_arcs = get_arc_based_paths_with_features(trips_data.routes, graph)
    return Instance(input_data=instance_params, deadlines=trips_data.deadline,
                    trip_routes=trip_routes, travel_times_arcs=travel_times_arcs, capacities_arcs=capacities_arcs,
                    node_based_trip_routes=trips_data.routes, release_times_dataset=trips_data.release_time)


def import_trips_data(instance_parameters: InstanceParameters) -> TripsData:
    """
    Imports trip data and route data from JSON files and integrates them into a TripsData dataclass.
    """
    # Ensure the instance data exists; otherwise, compute it
    if not os.path.exists(instance_parameters.path_to_instance):
        InstanceComputer(instance_parameters).run()

    # Load trip data from JSON
    with open(instance_parameters.path_to_instance, 'r') as file:
        data = json.load(file)

    trip_data = [
        data[key] for key in data.keys() if key.startswith('trip_')
    ]
    trips_df = pd.json_normalize(trip_data)
    print(f"Loaded {len(trips_df)} trips.")

    # Load route data from JSON
    with open(instance_parameters.path_to_routes, 'r') as file:
        routes_data = json.load(file)

    routes_df = pd.DataFrame([
        {"path": route["path"]} for route in routes_data if "path" in route
    ])

    # Validate consistency between trips and routes
    if len(routes_df) != len(trips_df):
        raise ValueError("Mismatch: Number of routes does not match number of trips.")

    # Combine data and return as TripsData
    return TripsData(
        routes=routes_df["path"].tolist(),
        deadline=trips_df["deadline"].tolist(),
        release_time=trips_df["release_time"].tolist(),
    )
