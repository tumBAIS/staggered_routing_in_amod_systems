from __future__ import annotations

import datetime
import json
import os
from dataclasses import dataclass, field

import jsonpickle
import networkx as nx
import numpy as np

import pandas as pd
from networkx import DiGraph
from networkx.readwrite import json_graph

from instance_generator import InstanceComputer
from problem.paths import get_arc_based_paths_with_features

from input_data import InstanceParameters, SPEED_KPH
from utils.aliases import Time, ConflictingSets


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
    max_staggering_applicable: list[float]

    def __post_init__(self):
        self.conflicting_sets = self.initialize_conflicting_sets()
        self.earliest_departure_times = self.initialize_earliest_departure_times()
        self.latest_departure_times = self.initialize_latest_departure_times()
        self.min_delay_on_arcs = self.initialize_min_delay_on_arcs()
        self.max_delay_on_arcs = self.initialize_max_delay_on_arcs()

    def initialize_conflicting_sets(self) -> ConflictingSets:
        num_arcs = len(self.travel_times_arcs)
        conflicting_sets = [[] for _ in range(num_arcs)]

        for trip, route in enumerate(self.trip_routes):
            for arc in route:
                conflicting_sets[arc].append(trip)
        return conflicting_sets

    def get_lb_travel_time(self) -> float:
        return sum(self.travel_times_arcs[arc] for path in self.trip_routes for arc in path)

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

    def initialize_earliest_departure_times(self):
        # Initialize a list to store the earliest departure times for each trip
        earliest_departure_times = []

        # Iterate over each trip and its route
        for trip, route in enumerate(self.trip_routes):
            # Start with the release time for the trip
            release_time = self.release_times[trip]
            trip_departure_times = [release_time]

            # Calculate earliest departure times for each arc in the route
            for arc in route[:-1]:
                nominal_time = self.travel_times_arcs[arc]
                last_time = trip_departure_times[-1]
                trip_departure_times.append(last_time + nominal_time)

            # Add the calculated times for the current trip to the result
            earliest_departure_times.append(trip_departure_times)

        return earliest_departure_times

    def initialize_latest_departure_times(self):
        """
        Initializes the latest departure times for each trip based on the deadlines
        and nominal travel times for each arc in the route.
        """
        # Initialize a list to store the latest departure times for each trip
        latest_departure_times = []

        # Iterate over each trip and its route
        for trip, route in enumerate(self.trip_routes):
            # Start with the deadline for the trip
            deadline = self.deadlines[trip]
            trip_departure_times = [deadline]

            # Calculate latest departure times for each arc in reverse order
            for arc in reversed(route[1:-1]):
                nominal_time = self.travel_times_arcs[arc]
                last_time = trip_departure_times[0]  # Get the last computed time (at the front of the list)
                trip_departure_times.insert(0, last_time - nominal_time)
            max_staggered_departure = self.earliest_departure_times[trip][0] + self.max_staggering_applicable[trip]
            trip_departure_times.insert(0, max_staggered_departure)
            # Add the calculated times for the current trip to the result
            latest_departure_times.append(trip_departure_times)

        return latest_departure_times

    def initialize_min_delay_on_arcs(self):
        return [[0 for _ in route] for route in self.trip_routes]

    def initialize_max_delay_on_arcs(self):
        return [[self.latest_departure_times[trip][position] - self.earliest_departure_times[trip][position] for
                 position, arc in enumerate(route)] for trip, route in enumerate(self.trip_routes)]


def get_instance(instance_params: InstanceParameters) -> Instance:
    """Constructs an instance from input data without simplification."""
    trips_data = import_trips_data(instance_params)
    graph = import_graph(instance_params)
    set_arcs_nominal_travel_times_and_capacities(graph, instance_params)
    trip_routes, travel_times_arcs, capacities_arcs = get_arc_based_paths_with_features(trips_data.routes, graph)
    max_staggering_applicable = get_max_staggering_applicable(trip_routes, travel_times_arcs, trips_data.release_time,
                                                              trips_data.deadline, instance_params)
    instance = Instance(instance_params=instance_params, deadlines=trips_data.deadline,
                        trip_routes=trip_routes, travel_times_arcs=travel_times_arcs, capacities_arcs=capacities_arcs,
                        node_based_trip_routes=trips_data.routes, release_times=trips_data.release_time,
                        max_staggering_applicable=max_staggering_applicable)
    instance.print_info_arcs_utilized()
    return instance


def get_max_staggering_applicable(trip_routes: list[list[int]],
                                  travel_times_arcs: list[float],
                                  release_times: list[float],
                                  deadlines: list[float],
                                  instance_params: InstanceParameters) -> list[float]:
    """
    Calculate the maximum staggering applicable for each vehicle's trip route
    based on input staggering cap, travel times, deadlines, and release times.
    """
    # TODO: move this into instance generation
    max_staggering_applicable = []

    for vehicle, path in enumerate(trip_routes):
        # Calculate total travel time for the trip
        travel_time = sum(travel_times_arcs[arc] for arc in path)

        # Calculate max staggering based on staggering cap
        staggering_cap_limit = instance_params.staggering_cap / 100 * travel_time

        # Calculate max staggering based on deadlines
        deadline_limit = deadlines[vehicle] - (travel_time + release_times[vehicle])

        # The maximum staggering applicable is the minimum of the two limits
        max_staggering = min(staggering_cap_limit, deadline_limit)
        max_staggering_applicable.append(max_staggering)
    return max_staggering_applicable


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


def set_arcs_nominal_travel_times_and_capacities(graph: nx.DiGraph, instance_params: InstanceParameters) -> None:
    """
    Assigns nominal travel times and capacities to arcs in the Manhattan graph based on
    the speed and max flow allowed specified in the input data.
    """
    print(f"Assigning nominal travel times assuming vehicles traveling at {SPEED_KPH} kph")

    # Set initial nominal travel time attributes to NaN
    nx.set_edge_attributes(graph, float('nan'), 'nominal_travel_time')

    for origin, destination in graph.edges():
        distance = graph[origin][destination]['length']
        nominal_travel_time = distance * 3.6 / SPEED_KPH
        graph[origin][destination]['nominal_travel_time'] = nominal_travel_time

        # Calculate nominal capacity based on max flow allowed
        nominal_capacity = int(np.ceil(nominal_travel_time / instance_params.max_flow_allowed))
        graph[origin][destination]['nominal_capacity'] = nominal_capacity


def deserialize_graph(file_path: str) -> DiGraph:
    """
    Deserializes a NetworkX DiGraph from a JSON file using jsonpickle and json_graph.
    """
    with open(file_path, 'r') as file:
        graph_data = jsonpickle.decode(file.read())
        return json_graph.adjacency_graph(graph_data, directed=True)


def import_graph(instance_params: InstanceParameters) -> DiGraph:
    """
    Imports a graph structure from a JSON file located based on the network name provided in input_data.
    """
    if os.path.exists(instance_params.path_to_G):
        graph = DiGraph(deserialize_graph(instance_params.path_to_G))
        print(f"Loaded {instance_params.network_name} network")
    else:
        raise RuntimeError(f"{instance_params.network_name} network not found in {instance_params.path_to_G}")

    return graph
