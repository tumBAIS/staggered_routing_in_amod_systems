from __future__ import annotations

import os
import typing
from dataclasses import dataclass, field

from utils.classes import CompleteSolution
from input_data import InstanceParameters, SAVE_CPP_INSTANCE
from utils.aliases import Time, Staggering
from typing import Optional

path_to_cpp_instance = os.path.join(os.path.dirname(__file__),
                                    "../../cpp_module/catch2_tests/instancesForTest/instanceForLocalSearch")


def save_list_of_strings_file(list_of_values: list[typing.Any], file_name: str, path: str):
    with open(f"{path}/{file_name}.txt", "w") as outfile:
        for i, value in enumerate(list_of_values):
            outfile.write(str(value) + ("\n" if i < len(list_of_values) - 1 else ""))


@dataclass
class Instance:
    input_data: InstanceParameters
    capacities_arcs: list[int]
    release_times_dataset: list[float]
    arrival_times_dataset: list[float]
    trip_routes: list[list[int]]
    node_based_trip_routes: list[list[int]]
    travel_times_arcs: list[float]
    deadlines: list[Time]
    clock_start_epoch: int = 0
    due_dates: list[float] = field(default_factory=list)
    undivided_conflicting_sets: list[list[list[int]]] = field(default_factory=list)
    conflicting_sets: list[list[int]] = field(default_factory=list)
    latest_departure_times: list[list[float]] = field(default_factory=list)
    earliest_departure_times: list[list[float]] = field(default_factory=list)
    min_delay_on_arc: list[list[float]] = field(default_factory=list)
    max_delay_on_arc: list[list[float]] = field(default_factory=list)
    start_solution_time: float = 0
    removed_vehicles: list[int] = field(default_factory=list)
    max_staggering_applicable: Optional[list[Staggering]] = None

    def __post_init__(self):
        self.set_max_staggering_applicable()

    def get_lb_travel_time(self) -> float:
        return sum(self.travel_times_arcs[arc] for path in self.trip_routes for arc in path)

    def set_deadlines(self, deadlines: list[Time]):
        if self.deadlines is None:
            self.deadlines = deadlines
            print(f"Deadline delta is {self.input_data.deadline_factor}% of congested travel time")
        else:
            raise ValueError("Attempting to override deadlines with class method!")

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
            staggering_cap_limit = self.input_data.staggering_cap / 100 * travel_time

            # Calculate max staggering based on deadlines
            deadline_limit = self.deadlines[vehicle] - (travel_time + self.release_times_dataset[vehicle])

            # The maximum staggering applicable is the minimum of the two limits
            max_staggering = min(staggering_cap_limit, deadline_limit)
            self.max_staggering_applicable.append(max_staggering)


def print_total_free_flow_time(instance: Instance):
    total_free_flow_time = sum(instance.travel_times_arcs[arc] for path in instance.trip_routes for arc in path)
    print(f"Total free flow time for the instance: {total_free_flow_time / 3600:.2f} hours")


def get_instance(input_data: InstanceParameters, arc_based_shortest_paths: list[list[int]],
                 nominal_travel_times: list[float], nominal_capacities: list[int],
                 release_times_dataset: list[Time], arrival_times_dataset: list[Time],
                 node_based_trip_routes: list[list[int]], deadlines: list[float]) -> Instance:
    return Instance(
        trip_routes=arc_based_shortest_paths,
        travel_times_arcs=nominal_travel_times,
        capacities_arcs=nominal_capacities,
        input_data=input_data,
        release_times_dataset=release_times_dataset,
        arrival_times_dataset=arrival_times_dataset,
        node_based_trip_routes=node_based_trip_routes,
        deadlines=deadlines
    )
