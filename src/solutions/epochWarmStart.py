import datetime

from utils.aliases import VehicleSchedules
from instanceModule.epochInstance import EpochInstance
from utils.classes import EpochSolution
from congestion_model.core import getFreeFlowSchedule, \
    getTotalTravelTime, getDelaysOnArcs, getStaggeringApplicable
from congestion_model.conflict_binaries import getConflictBinaries
import cpp_module as cpp


def _runLocalSearch(solution: EpochSolution, instance: EpochInstance) -> VehicleSchedules:
    print("Computing warm start solution")
    instance.dueDates = instance.deadlines[:]
    totalTimeRemaining = instance.inputData.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - instance.startSolutionTime)
    epochTimeRemaining = instance.inputData.epoch_time_limit - (
            datetime.datetime.now().timestamp() - instance.clockStartEpoch)
    timeRemaining = min(totalTimeRemaining, epochTimeRemaining)
    startSearchClock = datetime.datetime.now().timestamp()
    cppParameters = [
        timeRemaining,
    ]
    congestedSchedule = cpp.cppSchedulingLocalSearch(
        release_times=solution.releaseTimes,
        remaining_time_slack=solution.staggeringApplicable,
        staggering_applied=solution.staggeringApplied,
        conflicting_sets=instance.conflictingSets,
        earliest_departure_times=instance.earliestDepartureTimes,
        latest_departure_times=instance.latestDepartureTimes,
        travel_times_arcs=instance.travel_times_arcs,
        capacities_arcs=instance.capacities_arcs,
        trip_routes=instance.trip_routes,
        deadlines=instance.deadlines,
        due_dates=instance.dueDates,
        list_of_slopes=instance.inputData.list_of_slopes,
        list_of_thresholds=instance.inputData.list_of_thresholds,
        parameters=cppParameters,
        lb_travel_time=instance.get_lb_travel_time()
    )
    endSearchClock = datetime.datetime.now().timestamp()
    print("Time necessary to compute warm start solution: ", endSearchClock - startSearchClock)
    return congestedSchedule


def _checkIfThereTimeLeftForOptimization(epochInstance: EpochInstance):
    algorithmRuntime = epochInstance.inputData.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - epochInstance.startSolutionTime)

    epochRuntime = epochInstance.inputData.epoch_time_limit - (
            datetime.datetime.now().timestamp() - epochInstance.clockStartEpoch)

    timeLeft = min(algorithmRuntime, epochRuntime)
    return timeLeft > 1e-6


def getEpochWarmStart(epochInstance: EpochInstance, epochStatusQuo: EpochSolution) -> EpochSolution:
    isThereTimeLeftForOptimization = _checkIfThereTimeLeftForOptimization(epochInstance)
    if epochInstance.inputData.improve_warm_start and isThereTimeLeftForOptimization:
        congestedSchedule = _runLocalSearch(epochStatusQuo, epochInstance)
    else:
        if not isThereTimeLeftForOptimization:
            print("no remaining time for optimization - ", end="")
        print("not improving status quo")
        return epochStatusQuo

    releaseTimes = [schedule[0] for schedule in congestedSchedule]
    freeFlowSchedule = getFreeFlowSchedule(epochInstance, congestedSchedule)
    staggeringApplied = [congestedSchedule[vehicle][0] - releaseTime for vehicle, releaseTime in
                         enumerate(epochStatusQuo.releaseTimes)]
    staggeringApplicable = getStaggeringApplicable(epochInstance, staggeringApplied)
    delaysOnArcs = getDelaysOnArcs(epochInstance, congestedSchedule)
    totalDelay = sum(sum(delays) for delays in delaysOnArcs)
    binaries = getConflictBinaries(epochInstance.conflictingSets, epochInstance.trip_routes,
                                   congestedSchedule)
    totalTravelTime = getTotalTravelTime(congestedSchedule)

    warmStart: EpochSolution = EpochSolution(totalDelay=totalDelay,
                                             congestedSchedule=congestedSchedule,
                                             delaysOnArcs=delaysOnArcs,
                                             releaseTimes=releaseTimes,
                                             staggeringApplicable=staggeringApplicable,
                                             binaries=binaries,
                                             freeFlowSchedule=freeFlowSchedule,
                                             staggeringApplied=staggeringApplied,
                                             totalTravelTime=totalTravelTime,
                                             vehiclesUtilizingArcs=epochStatusQuo.vehiclesUtilizingArcs
                                             )
    print(f"The delay of the warm start is {totalDelay / totalTravelTime:.2%} of the travel time")
    return warmStart
