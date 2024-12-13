from __future__ import annotations
import copy

from congestion_model.conflict_binaries import get_conflict_binaries
from instance_module.epoch_instance import EpochInstance
from processing.merge_arcs_without_conflicts import merge_arcs_on_paths_where_no_conflicts_can_happen
from processing.remove_paths_sequences import remove_initial_paths, remove_final_paths
from processing.remove_not_utilized_arcs import remove_not_utilized_arcs
from instance_module.instance import Instance
from utils.classes import Solution
from input_data import TOLERANCE


def adjust_release_times_and_deadlines(instance: Instance, status_quo: Solution) -> None:
    """
    Adjust release times and deadlines to set the minimum release time to zero.
    """
    min_release_time = min(status_quo.release_times)
    if min_release_time <= TOLERANCE:
        return

    for vehicle in range(len(status_quo.release_times)):
        status_quo.release_times[vehicle] -= min_release_time
        instance.deadlines[vehicle] -= min_release_time
        instance.release_times[vehicle] -= min_release_time

        for arc_id in range(len(status_quo.congested_schedule[vehicle])):
            status_quo.congested_schedule[vehicle][arc_id] -= min_release_time
            status_quo.free_flow_schedule[vehicle][arc_id] -= min_release_time
            instance.latest_departure_times[vehicle][arc_id] -= min_release_time
            instance.earliest_departure_times[vehicle][arc_id] -= min_release_time


def simplify_system(
        not_simplified_instance: EpochInstance,
        not_simplified_status_quo: Solution
) -> tuple[EpochInstance, Solution]:
    """
    Simplify the system by preprocessing paths, merging arcs, and removing unused arcs.
    """
    # Create deep copies of the instance and status quo to avoid modifying the originals
    status_quo, instance = copy.deepcopy((not_simplified_status_quo, not_simplified_instance))

    # Remove initial parts of paths without conflicts
    remove_initial_paths(instance, status_quo)
    not_simplified_instance.removed_vehicles = instance.removed_vehicles[:]  # Map IDs of removed vehicles

    # If all vehicles are removed, return the simplified instance and status quo
    if not instance.trip_routes:
        return instance, status_quo

    # Further preprocessing steps
    remove_final_paths(instance, status_quo)
    merge_arcs_on_paths_where_no_conflicts_can_happen(instance, status_quo)
    instance.removed_arcs = remove_not_utilized_arcs(instance)

    # Update conflict binaries for the simplified system
    status_quo.binaries = get_conflict_binaries(
        instance.conflicting_sets,
        instance.trip_routes,
        status_quo.congested_schedule
    )

    # Adjust release times and deadlines
    adjust_release_times_and_deadlines(instance, status_quo)

    # Print congestion information for the simplified system
    status_quo.print_congestion_info()

    return instance, status_quo
