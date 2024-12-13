from __future__ import annotations
import datetime
import conflicting_sets.split
from conflicting_sets.time_bounds import TimeBound, get_initial_latest_arrival_times, get_arc_based_time_bounds, \
    split_time_bounds_on_arcs, arrange_bounds_by_vehicle, get_undivided_conflicting_sets
from instance_module.instance import Instance
from utils.aliases import *
from input_data import TOLERANCE


def get_max_delay_on_arcs(vehicle_based_time_bounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.max_delay_on_arc for bound in sorted(bounds_of_one_vehicle, key=lambda x: x.earliest_departure)]
        for bounds_of_one_vehicle in vehicle_based_time_bounds
    ]


def get_min_delay_on_arcs(vehicle_based_time_bounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.min_delay_on_arc for bound in sorted(bounds_of_one_vehicle, key=lambda x: x.earliest_departure)]
        for bounds_of_one_vehicle in vehicle_based_time_bounds
    ]


def get_earliest_departure_times(vehicle_based_time_bounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.earliest_departure for bound in sorted(bounds_of_one_vehicle, key=lambda x: x.earliest_departure)]
        for bounds_of_one_vehicle in vehicle_based_time_bounds
    ]


def get_latest_departure_times(vehicle_based_time_bounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.latest_departure for bound in
         sorted(bounds_of_one_vehicle, key=lambda x: x.earliest_departure)]
        for bounds_of_one_vehicle in vehicle_based_time_bounds
    ]


def add_conflicting_sets_to_instance(instance: Instance, ff_schedule: TripSchedules) -> None:
    """Add undivided conflicting sets and update time-related properties in the instance."""
    print("Adding undivided conflicting sets to instance...", end=" ")
    clock_start = datetime.datetime.now().timestamp()

    # Initialize latest arrival times
    known_latest_arrival_times = get_initial_latest_arrival_times(instance, ff_schedule)

    # Iteratively refine time bounds until convergence
    while True:
        arc_based_time_bounds = get_arc_based_time_bounds(instance, known_latest_arrival_times, ff_schedule)
        bounds_on_arcs_split = split_time_bounds_on_arcs(instance, arc_based_time_bounds)
        vehicle_based_time_bounds = arrange_bounds_by_vehicle(arc_based_time_bounds, instance.trip_routes)

        # Extract new latest arrival times
        new_latest_arrival_times = [
            [bound.latest_arrival for bound in bounds] for bounds in vehicle_based_time_bounds
        ]

        # Break loop if arrival times have converged
        if known_latest_arrival_times == new_latest_arrival_times:
            break
        known_latest_arrival_times = new_latest_arrival_times[:]

    # Update instance properties
    undivided_conflicting_sets = get_undivided_conflicting_sets(instance, bounds_on_arcs_split)
    instance.earliest_departure_times = get_earliest_departure_times(vehicle_based_time_bounds)
    instance.latest_departure_times = get_latest_departure_times(vehicle_based_time_bounds)
    instance.min_delay_on_arc = get_min_delay_on_arcs(vehicle_based_time_bounds)
    instance.max_delay_on_arc = get_max_delay_on_arcs(vehicle_based_time_bounds)

    # Split conflicting sets
    conflicting_sets.split.split_conflicting_sets(instance, undivided_conflicting_sets)

    # Measure and display execution time
    clock_end = datetime.datetime.now().timestamp()
    print(f"done! - time necessary: {clock_end - clock_start:.2f} seconds")
