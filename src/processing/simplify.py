from __future__ import annotations
import copy

from congestion_model.conflict_binaries import get_conflict_binaries
from instance_module.epoch_instance import EpochInstance
from processing.merge_arcs_without_conflicts import merge_arcs_on_paths_where_no_conflicts_can_happen
from processing.remove_paths_sequences import remove_initial_paths, remove_final_paths
from processing.remove_not_utilized_arcs import remove_not_utilized_arcs
from instance_module.instance import Instance
from utils.classes import EpochSolution, CompleteSolution


def _adjust_release_times_and_deadlines(instance: Instance, status_quo: CompleteSolution) -> None:
    """
    Adjust release times and deadlines to set the minimum release time to zero.
    """
    min_release_time = min(status_quo.release_times)
    if min_release_time == 0:
        return

    for vehicle in range(len(status_quo.release_times)):
        status_quo.release_times[vehicle] -= min_release_time
        instance.deadlines[vehicle] -= min_release_time

        for arc_id in range(len(status_quo.congested_schedule[vehicle])):
            status_quo.congested_schedule[vehicle][arc_id] -= min_release_time
            status_quo.free_flow_schedule[vehicle][arc_id] -= min_release_time
            instance.latest_departure_times[vehicle][arc_id] -= min_release_time
            instance.earliest_departure_times[vehicle][arc_id] -= min_release_time


def _print_congestion_info(status_quo: CompleteSolution) -> None:
    """
    Print summary statistics about the congestion in the simplified system.
    """
    total_free_flow_time = status_quo.total_travel_time - status_quo.total_delay
    congestion_delay_percentage = (status_quo.total_delay / status_quo.total_travel_time) * 100
    tomtom_congestion_index = ((status_quo.total_travel_time - total_free_flow_time) / total_free_flow_time) * 100

    print(f"Delay after preprocessing: {round(congestion_delay_percentage, 2)}% of travel time")
    print(f"TomTom congestion index: {round(tomtom_congestion_index, 2)}%")


def get_od_arc_count(osm_info_arcs_utilized: list[dict]) -> int:
    """
    Count unique origin-destination (OD) arc combinations.
    """
    unique_combinations = {
        (arc_info.get("origin"), arc_info.get("destination"))
        for arc_info in osm_info_arcs_utilized
        if arc_info.get("origin") is not None and arc_info.get("destination") is not None
    }
    return len(unique_combinations)


def simplify_system(
        not_simplified_instance: EpochInstance,
        not_simplified_status_quo: CompleteSolution | EpochSolution
) -> tuple[Instance | EpochInstance, CompleteSolution | EpochSolution]:
    """
    Simplify the system by preprocessing paths, merging arcs, and removing unused arcs.
    """
    # Create deep copies of the instance and status quo to avoid modifying the originals
    status_quo, instance = copy.deepcopy((not_simplified_status_quo, not_simplified_instance))

    # Remove initial parts of paths without conflicts
    remove_initial_paths(instance, status_quo)
    not_simplified_instance.removed_vehicles = instance.removed_vehicles[:]  # Map IDs of removed vehicles

    # If all vehicles are removed, return the simplified instance and status quo
    if len(not_simplified_status_quo.congested_schedule) == len(not_simplified_instance.removed_vehicles):
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
    _adjust_release_times_and_deadlines(instance, status_quo)

    # Print congestion information for the simplified system
    _print_congestion_info(status_quo)

    return instance, status_quo
