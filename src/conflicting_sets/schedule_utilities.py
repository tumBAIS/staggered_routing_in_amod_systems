from __future__ import annotations
import datetime
import conflicting_sets.split
import utils.prints
from conflicting_sets.time_bounds import TimeBound, get_initial_latest_arrival_times, get_arc_based_time_bounds, \
    split_time_bounds_on_arcs, arrange_bounds_by_vehicle, get_undivided_conflicting_sets
from problem.instance import Instance
from utils.aliases import *
from input_data import TOLERANCE, CONSTR_TOLERANCE


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
    """
    Calculate the latest departure times for each vehicle based on time bounds.

    """
    return [
        [
            bound.latest_departure
            if bound.latest_departure > bound.earliest_departure
            else bound.earliest_departure + CONSTR_TOLERANCE
            for bound in sorted(bounds_of_one_vehicle, key=lambda x: x.earliest_departure)
        ]
        for bounds_of_one_vehicle in vehicle_based_time_bounds
    ]


def add_conflicting_sets_to_instance(instance: Instance, ff_schedule: Schedules) -> None:
    """
    Add undivided conflicting sets and update time-related properties in the instance.

    Args:
        instance (Instance): The problem instance to update.
        ff_schedule (TripSchedules): Free-flow trip schedules.
    """
    print("\n========================================")
    print("Starting to add undivided conflicting sets to the instance...")
    print("----------------------------------------")
    clock_start = datetime.datetime.now().timestamp()

    # Initialize latest arrival times
    print("Initializing latest arrival times...", end=" ")
    known_latest_arrival_times = get_initial_latest_arrival_times(instance, ff_schedule)
    print("done.")

    # Iteratively refine time bounds until convergence
    iteration = 0
    print("\nRefining time bounds iteratively until convergence:")
    while True:
        iteration += 1
        print(f"  Iteration {iteration}: Computing arc-based time bounds...", end=" ")
        arc_based_time_bounds = get_arc_based_time_bounds(instance, known_latest_arrival_times, ff_schedule)
        bounds_on_arcs_split = split_time_bounds_on_arcs(instance, arc_based_time_bounds)
        vehicle_based_time_bounds = arrange_bounds_by_vehicle(arc_based_time_bounds, instance.trip_routes)
        print("done.")

        # Extract new latest arrival times
        print("  Extracting new latest arrival times...", end=" ")
        new_latest_arrival_times = [
            [bound.latest_arrival for bound in bounds] for bounds in vehicle_based_time_bounds
        ]
        print("done.")

        # Break loop if arrival times have converged
        if known_latest_arrival_times == new_latest_arrival_times:
            print(f"  Convergence achieved after {iteration} iterations.")
            break
        else:
            print(f"  Convergence not yet achieved. Updating arrival times...")
        known_latest_arrival_times = new_latest_arrival_times[:]

    # Update instance properties
    print("\nUpdating instance properties...", end=" ")
    undivided_conflicting_sets = get_undivided_conflicting_sets(instance, bounds_on_arcs_split)
    instance.earliest_departure_times = get_earliest_departure_times(vehicle_based_time_bounds)
    instance.latest_departure_times = get_latest_departure_times(vehicle_based_time_bounds)
    instance.min_delay_on_arcs = get_min_delay_on_arcs(vehicle_based_time_bounds)
    instance.max_delay_on_arcs = get_max_delay_on_arcs(vehicle_based_time_bounds)
    print("done.")

    # Split conflicting sets
    print("Splitting conflicting sets...", end=" ")
    conflicting_sets.split.split_conflicting_sets(instance, undivided_conflicting_sets)
    print("done.")

    # Measure and display execution time
    clock_end = datetime.datetime.now().timestamp()
    print("----------------------------------------")
    print(f"Process completed! Total execution time: {clock_end - clock_start:.2f} seconds")
    print("========================================\n")

    utils.prints.print_conflicting_sets_info(instance)
