from __future__ import annotations
import copy

from conflicting_sets.conflict_binaries import get_conflict_binaries
from problem.epoch_instance import EpochInstance
from simplify.merge_arcs_without_conflicts import merge_arcs_on_paths_where_no_conflicts_can_happen
from simplify.remove_not_utilized_arcs import remove_not_utilized_arcs
from problem.instance import Instance
from problem.solution import Solution
from input_data import TOLERANCE, SolverParameters


def adjust_release_times_and_deadlines(instance: Instance, status_quo: Solution) -> None:
    """
    Adjust release times and deadlines to set the minimum release time to zero.
    """
    min_release_time = min(status_quo.start_times)
    if min_release_time <= TOLERANCE:
        return

    for vehicle in range(len(status_quo.start_times)):
        status_quo.start_times[vehicle] -= min_release_time
        instance.deadlines[vehicle] -= min_release_time
        instance.release_times[vehicle] -= min_release_time

        for arc_id in range(len(status_quo.congested_schedule[vehicle])):
            status_quo.congested_schedule[vehicle][arc_id] -= min_release_time
            instance.latest_departure_times[vehicle][arc_id] -= min_release_time
            instance.earliest_departure_times[vehicle][arc_id] -= min_release_time


def remove_initial_paths(instance: EpochInstance, status_quo: Solution) -> None:
    """
    Remove the initial parts of paths without conflicts and remove vehicles with no remaining paths.
    """
    initial_vehicle_count = len(instance.trip_routes)

    for trip in reversed(range(initial_vehicle_count)):
        initial_route = instance.trip_routes[trip][:]  # Modified in place

        for arc in initial_route:
            if trip in instance.conflicting_sets[arc]:
                break

            # Remove the arc from the vehicle's route and update the solution state
            instance.remove_arc_at_position_from_trip_route(trip, 0, "first")
            status_quo.remove_trip_at_position_entry_from_solution(trip, 0)

        # Remove the trip if no routes are left
        if not instance.trip_routes[trip]:
            instance.remove_trip(trip)
            status_quo.remove_trip(trip)

    # Handle the case where all vehicles are removeds
    if not instance.trip_routes:
        print("All vehicles removed. Nothing to optimize.")
        return

    # Update conflicting sets for the remaining vehicles
    instance.update_conflicting_sets_after_trip_removal()


def remove_final_paths(instance: EpochInstance, status_quo: Solution) -> None:
    """
    Remove the final parts of paths without conflicts, starting from the second-to-last arc.

    Args:
        instance (EpochInstance): The problem instance containing trip routes and conflict data.
        status_quo (Solution): The current solution state to be updated.
    """
    for trip, route in enumerate(instance.trip_routes):
        reversed_route = list(reversed(route[:-1]))
        for index, arc in enumerate(reversed_route, 1):  # Start from the second-to-last arc
            position = len(reversed_route) - index  # Calculate the original index in the route
            if trip in instance.conflicting_sets[arc]:
                break
            instance.remove_arc_at_position_from_trip_route(trip, position, "last")
            status_quo.remove_trip_at_position_entry_from_solution(trip, position + 1)


def simplify_system(
        not_simplified_instance: EpochInstance,
        not_simplified_status_quo: Solution,
        solver_params: SolverParameters
) -> tuple[EpochInstance, Solution]:
    """
    Simplify the system by preprocessing paths, merging arcs, and removing unused arcs.
    """
    print("\nSimplifying system...")
    if not solver_params.simplify:
        return not_simplified_instance, not_simplified_status_quo

    # Create deep copies of the instance and status quo to avoid modifying the originals
    status_quo, instance = copy.deepcopy((not_simplified_status_quo, not_simplified_instance))

    # # Remove initial parts of paths without conflicts
    # remove_initial_paths(instance, status_quo)
    # not_simplified_instance.removed_vehicles = instance.removed_vehicles[:]
    # print(f" Removed vehicles: {len(instance.removed_vehicles)}, Remaining: {len(instance.trip_routes)}")

    # Check if all vehicles have been removed
    if not instance.trip_routes:
        print("All vehicles removed. Simplification complete.")
        return instance, status_quo

    # Further preprocessing steps
    remove_final_paths(instance, status_quo)
    print(" Removed final parts of paths.")

    merge_arcs_on_paths_where_no_conflicts_can_happen(instance, status_quo)
    print(" Merged arcs without conflicts.")

    instance.removed_arcs = remove_not_utilized_arcs(instance)
    print(f" Removed unused arcs: {len(instance.removed_arcs)}.")

    status_quo.binaries = get_conflict_binaries(
        instance.conflicting_sets,
        instance.trip_routes,
        status_quo.congested_schedule
    )
    print(" Updated conflict binaries.")

    print("System simplification complete.\n")
    return instance, status_quo
