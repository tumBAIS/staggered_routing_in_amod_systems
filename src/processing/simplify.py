from __future__ import annotations

import copy

from congestion_model.conflict_binaries import get_conflict_binaries
from instanceModule.epoch_instance import EpochInstance
from processing.merge_arcs_without_conflicts import mergeArcsOnPathsWhereNoConflictsCanHappen
from processing.remove_paths_sequences import removeInitialPartOfPathsWithoutConflicts, \
    removeFinalPartOfPathsWithoutConflicts
from processing.remove_not_utilized_arcs import removeNotUtilizedArcs
from instanceModule.instance import Instance
from input_data import ACTIVATE_ASSERTIONS

from utils.classes import EpochSolution, CompleteSolution


def _setMinReleaseTimeTo0AndAdjustDeadlines(instance: Instance,
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


def _assertLenSchedulesIsTheSame(statusQuo):
    if ACTIVATE_ASSERTIONS:
        assert all(len(congSchedule) == len(ffSchedule) for congSchedule, ffSchedule in
                   zip(statusQuo.congested_schedule, statusQuo.free_flow_schedule))


def _assertReleaseTimesStatusQuo(statusQuo):
    if ACTIVATE_ASSERTIONS:
        assert all(abs(relTime - congSched[0]) < 1e-6 for relTime, congSched in
                   zip(statusQuo.release_times, statusQuo.congested_schedule))


def _printCongestionInfoSimplifiedSystem(statusQuo: CompleteSolution):
    totalFreeFlowTime = statusQuo.total_travel_time - statusQuo.total_delay
    print(
        f"The delay of the status quo after preprocessing "
        f"is {round(statusQuo.total_delay / statusQuo.total_travel_time * 100, 2)}% of the travel time")
    print(
        f"The tomtom congestion index "
        f"is {round((statusQuo.total_travel_time - totalFreeFlowTime) / totalFreeFlowTime * 100, 2)}% of the travel time")


def getODArcs(osmInfoArcsUtilized):
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
    print(f"Number of unique arc ODs before simplification: {getODArcs(instance.osm_info_arcs_utilized)}")
    removeInitialPartOfPathsWithoutConflicts(instance, statusQuo)
    notSimplifiedInstance.removed_vehicles = instance.removed_vehicles[:]  # we will map the ID of vehicles
    allVehiclesRemoved = len(notSimplifiedStatusQuo.congested_schedule) == len(notSimplifiedInstance.removed_vehicles)
    if allVehiclesRemoved:
        return instance, statusQuo
    removeFinalPartOfPathsWithoutConflicts(instance, statusQuo)
    mergeArcsOnPathsWhereNoConflictsCanHappen(instance, statusQuo)
    removeNotUtilizedArcs(instance)
    statusQuo.binaries = get_conflict_binaries(instance.conflicting_sets,
                                               instance.trip_routes,
                                               statusQuo.congested_schedule)  # necessary if no warm start is given
    _setMinReleaseTimeTo0AndAdjustDeadlines(instance, statusQuo)
    _printCongestionInfoSimplifiedSystem(statusQuo)
    print(f"Number of unique arc ODs after simplification: {getODArcs(instance.osm_info_arcs_utilized)}")
    return instance, statusQuo
