from __future__ import annotations

import copy

from congestion_model.conflict_binaries import get_conflict_binaries
from instanceModule.epochInstance import EpochInstance
from processing.mergeArcsWithoutConflicts import mergeArcsOnPathsWhereNoConflictsCanHappen
from processing.removePathsSequences import removeInitialPartOfPathsWithoutConflicts, \
    removeFinalPartOfPathsWithoutConflicts
from processing.removeNotUtilizedArcs import removeNotUtilizedArcs
from instanceModule.instance import Instance
from inputData import ACTIVATE_ASSERTIONS

from utils.classes import EpochSolution, CompleteSolution


def _setMinReleaseTimeTo0AndAdjustDeadlines(instance: Instance,
                                            statusQuo: CompleteSolution) -> None:
    minReleaseTime = min(statusQuo.releaseTimes)
    if minReleaseTime == 0:
        return
    for vehicle in range(len(statusQuo.releaseTimes)):
        statusQuo.releaseTimes[vehicle] -= minReleaseTime
        instance.deadlines[vehicle] -= minReleaseTime
        try:
            instance.dueDates[vehicle] -= minReleaseTime
        except:
            pass
        for arcId in range(len(statusQuo.congestedSchedule[vehicle])):
            statusQuo.congestedSchedule[vehicle][arcId] -= minReleaseTime
            statusQuo.freeFlowSchedule[vehicle][arcId] -= minReleaseTime
            instance.latestDepartureTimes[vehicle][arcId] -= minReleaseTime
            instance.earliestDepartureTimes[vehicle][arcId] -= minReleaseTime

    return


def _assertLenSchedulesIsTheSame(statusQuo):
    if ACTIVATE_ASSERTIONS:
        assert all(len(congSchedule) == len(ffSchedule) for congSchedule, ffSchedule in
                   zip(statusQuo.congestedSchedule, statusQuo.freeFlowSchedule))


def _assertReleaseTimesStatusQuo(statusQuo):
    if ACTIVATE_ASSERTIONS:
        assert all(abs(relTime - congSched[0]) < 1e-6 for relTime, congSched in
                   zip(statusQuo.releaseTimes, statusQuo.congestedSchedule))


def _printCongestionInfoSimplifiedSystem(statusQuo: CompleteSolution):
    totalFreeFlowTime = statusQuo.totalTravelTime - statusQuo.totalDelay
    print(
        f"The delay of the status quo after preprocessing "
        f"is {round(statusQuo.totalDelay / statusQuo.totalTravelTime * 100, 2)}% of the travel time")
    print(
        f"The tomtom congestion index "
        f"is {round((statusQuo.totalTravelTime - totalFreeFlowTime) / totalFreeFlowTime * 100, 2)}% of the travel time")


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
    print(f"Number of unique arc ODs before simplification: {getODArcs(instance.osmInfoArcsUtilized)}")
    removeInitialPartOfPathsWithoutConflicts(instance, statusQuo)
    notSimplifiedInstance.removedVehicles = instance.removedVehicles[:]  # we will map the ID of vehicles
    allVehiclesRemoved = len(notSimplifiedStatusQuo.congestedSchedule) == len(notSimplifiedInstance.removedVehicles)
    if allVehiclesRemoved:
        return instance, statusQuo
    removeFinalPartOfPathsWithoutConflicts(instance, statusQuo)
    mergeArcsOnPathsWhereNoConflictsCanHappen(instance, statusQuo)
    removeNotUtilizedArcs(instance)
    statusQuo.binaries = get_conflict_binaries(instance.conflictingSets,
                                               instance.trip_routes,
                                               statusQuo.congestedSchedule)  # necessary if no warm start is given
    _setMinReleaseTimeTo0AndAdjustDeadlines(instance, statusQuo)
    _printCongestionInfoSimplifiedSystem(statusQuo)
    print(f"Number of unique arc ODs after simplification: {getODArcs(instance.osmInfoArcsUtilized)}")
    return instance, statusQuo
