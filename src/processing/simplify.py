from __future__ import annotations

import copy

from congestion_model.conflict_binaries import get_conflict_binaries
from instanceModule.epoch_instance import EpochInstance
from processing.merge_arcs_without_conflicts import merge_arcs_on_paths_where_no_conflicts_can_happen
from processing.remove_paths_sequences import remove_initial_part_of_paths_without_conflicts, \
    remove_final_part_of_paths_without_conflicts
from processing.remove_not_utilized_arcs import remove_not_utilized_arcs
from instanceModule.instance import Instance
from input_data import ACTIVATE_ASSERTIONS

from utils.classes import EpochSolution, CompleteSolution


def _set_min_release_time_to0_and_adjust_deadlines(instance: Instance,
                                                   statusQuo: CompleteSolution) -> None:
    minReleaseTime = min(statusQuo.release_times)
    if minReleaseTime == 0:
        return
    for vehicle in range(len(statusQuo.release_times)):
        statusQuo.release_times[vehicle] -= minReleaseTime
        instance.deadlines[vehicle] -= minReleaseTime
        try:
            instance.due_dates[vehicle] -= minReleaseTime
        except:
            pass
        for arcId in range(len(statusQuo.congested_schedule[vehicle])):
            statusQuo.congested_schedule[vehicle][arcId] -= minReleaseTime
            statusQuo.free_flow_schedule[vehicle][arcId] -= minReleaseTime
            instance.latest_departure_times[vehicle][arcId] -= minReleaseTime
            instance.earliest_departure_times[vehicle][arcId] -= minReleaseTime

    return


def _print_congestion_info_simplified_system(statusQuo: CompleteSolution):
    totalFreeFlowTime = statusQuo.total_travel_time - statusQuo.total_delay
    print(
        f"The delay of the status quo after preprocessing "
        f"is {round(statusQuo.total_delay / statusQuo.total_travel_time * 100, 2)}% of the travel time")
    print(
        f"The tomtom congestion index "
        f"is {round((statusQuo.total_travel_time - totalFreeFlowTime) / totalFreeFlowTime * 100, 2)}% of the travel time")


def get_od_arcs(osmInfoArcsUtilized):
    unique_combinations = set()
    for arcInfo in osmInfoArcsUtilized:
        origin = arcInfo.get("origin")
        destination = arcInfo.get("destination")
        if origin is not None and destination is not None:
            unique_combinations.add((origin, destination))

    return len(unique_combinations)


def simplify_system(notSimplifiedInstance: Instance | EpochInstance,
                    notSimplifiedStatusQuo: CompleteSolution | EpochSolution) -> \
        tuple[Instance | EpochInstance, CompleteSolution | EpochSolution]:
    statusQuo, instance = copy.deepcopy((notSimplifiedStatusQuo, notSimplifiedInstance))
    print(f"Number of unique arc ODs before simplification: {get_od_arcs(instance.osm_info_arcs_utilized)}")
    remove_initial_part_of_paths_without_conflicts(instance, statusQuo)
    notSimplifiedInstance.removed_vehicles = instance.removed_vehicles[:]  # we will map the ID of vehicles
    allVehiclesRemoved = len(notSimplifiedStatusQuo.congested_schedule) == len(notSimplifiedInstance.removed_vehicles)
    if allVehiclesRemoved:
        return instance, statusQuo
    remove_final_part_of_paths_without_conflicts(instance, statusQuo)
    merge_arcs_on_paths_where_no_conflicts_can_happen(instance, statusQuo)
    remove_not_utilized_arcs(instance)
    statusQuo.binaries = get_conflict_binaries(instance.conflicting_sets,
                                               instance.trip_routes,
                                               statusQuo.congested_schedule)  # necessary if no warm start is given
    _set_min_release_time_to0_and_adjust_deadlines(instance, statusQuo)
    _print_congestion_info_simplified_system(statusQuo)
    print(f"Number of unique arc ODs after simplification: {get_od_arcs(instance.osm_info_arcs_utilized)}")
    return instance, statusQuo
