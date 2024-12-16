from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import pandas as pd

from instance_generator import InstanceComputer
from instance_module.graph import import_graph, set_arcs_nominal_travel_times_and_capacities
from instance_module.paths import get_arc_based_paths_with_features

from input_data import InstanceParameters, SPEED_KPH
from utils.aliases import Time, Staggering, ConflictingSets
from typing import Optional


@dataclass
class TripsData:
    routes: list[list[int]]  # list of node-based paths for each trip
    deadline: list[int]  # Deadlines for each trip
    release_time: list[int]  # Release times for each trip


@dataclass
class Instance:
    instance_params: InstanceParameters
    capacities_arcs: list[int]
    release_times: list[float]
    trip_routes: list[list[int]]
    node_based_trip_routes: list[list[int]]
    travel_times_arcs: list[float]
    deadlines: list[Time]
    latest_departure_times: list[list[float]] = field(default_factory=list)
    earliest_departure_times: list[list[float]] = field(default_factory=list)
    min_delay_on_arc: list[list[float]] = field(default_factory=list)
    max_delay_on_arc: list[list[float]] = field(default_factory=list)
    start_solution_time: float = 0
    max_staggering_applicable: Optional[list[Staggering]] = None

    def __post_init__(self):
        self.set_max_staggering_applicable()
        self.conflicting_sets = self.initialize_conflicting_sets()

    def initialize_conflicting_sets(self) -> ConflictingSets:
        num_arcs = len(self.travel_times_arcs)
        conflicting_sets = [[] for _ in range(num_arcs)]

        for trip, route in enumerate(self.trip_routes):
            for arc in route:
                conflicting_sets[arc].append(trip)
        return conflicting_sets

    def get_lb_travel_time(self) -> float:
        return sum(self.travel_times_arcs[arc] for path in self.trip_routes for arc in path)

    def set_max_staggering_applicable(self):
        """
        Calculate the maximum staggering applicable for each vehicle's trip route
        based on input staggering cap, travel times, deadlines, and release times.
        """
        if self.deadlines is None:
            raise ValueError("Deadlines are not set. Cannot calculate max staggering applicable.")

        if self.max_staggering_applicable is not None:
            raise ValueError("max_staggering_applicable is already set. Cannot override it.")

        self.max_staggering_applicable = []

        for vehicle, path in enumerate(self.trip_routes):
            # Calculate total travel time for the trip
            travel_time = sum(self.travel_times_arcs[arc] for arc in path)

            # Calculate max staggering based on staggering cap
            staggering_cap_limit = self.instance_params.staggering_cap / 100 * travel_time

            # Calculate max staggering based on deadlines
            deadline_limit = self.deadlines[vehicle] - (travel_time + self.release_times[vehicle])

            # The maximum staggering applicable is the minimum of the two limits
            max_staggering = min(staggering_cap_limit, deadline_limit)
            self.max_staggering_applicable.append(max_staggering)

    def print_info_arcs_utilized(self):
        """
        Print a concise summary of the arcs utilized in the instance.

        Args:
            instance: The instance containing travel times and capacities for arcs.
        """
        length_arcs = [travel_time * SPEED_KPH / 3.6 for travel_time in self.travel_times_arcs]
        dataframe_info = pd.DataFrame({
            "Length [m]": length_arcs,
            "Travel Times [min]": [x / 60 for x in self.travel_times_arcs],
            "Nominal Capacities": self.capacities_arcs,
        })

        summary = dataframe_info.describe().round(2)
        print("\nInfo - Arcs Utilized:")
        print(summary)


def get_instance(instance_params: InstanceParameters) -> Instance:
    """Constructs an instance from input data without simplification."""
    trips_data = import_trips_data(instance_params)
    graph = import_graph(instance_params)
    set_arcs_nominal_travel_times_and_capacities(graph, instance_params)
    trip_routes, travel_times_arcs, capacities_arcs = get_arc_based_paths_with_features(trips_data.routes, graph)
    instance = Instance(instance_params=instance_params, deadlines=trips_data.deadline,
                        trip_routes=trip_routes, travel_times_arcs=travel_times_arcs, capacities_arcs=capacities_arcs,
                        node_based_trip_routes=trips_data.routes, release_times=trips_data.release_time)
    instance.print_info_arcs_utilized()
    return instance


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
