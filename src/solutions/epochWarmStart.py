import datetime

from utils.aliases import VehicleSchedules
from instanceModule.epochInstance import EpochInstance
from utils.classes import EpochSolution
from congestionModel.core import getFreeFlowSchedule, \
    getTotalTravelTime, getDelaysOnArcs, getStaggeringApplicable
from congestionModel.conflictBinaries import getConflictBinaries
import cpp_module as cpp


def _runLocalSearch(solution: EpochSolution, instance: EpochInstance) -> VehicleSchedules:
    print("Computing warm start solution")
    instance.dueDates = instance.deadlines[:]
    totalTimeRemaining = instance.inputData.algorithmTimeLimit - (
            datetime.datetime.now().timestamp() - instance.startSolutionTime)
    epochTimeRemaining = instance.inputData.epochTimeLimit - (
            datetime.datetime.now().timestamp() - instance.clockStartEpoch)
    timeRemaining = min(totalTimeRemaining, epochTimeRemaining)
    startSearchClock = datetime.datetime.now().timestamp()
    cppParameters = [
        timeRemaining,
    ]
    congestedSchedule = cpp.cppSchedulingLocalSearch(
        solution.releaseTimes,
        solution.staggeringApplicable,
        solution.staggeringApplied,
        instance.conflictingSets,
        instance.earliestDepartureTimes,
        instance.latestDepartureTimes,
        instance.travelTimesArcsUtilized,
        instance.nominalCapacitiesArcs,
        instance.arcBasedShortestPaths,
        instance.deadlines,
        instance.dueDates,
        instance.inputData.list_of_slopes,
        instance.inputData.list_of_thresholds,
        cppParameters
    )
    endSearchClock = datetime.datetime.now().timestamp()
    print("Time necessary to compute warm start solution: ", endSearchClock - startSearchClock)
    return congestedSchedule


def _checkIfThereTimeLeftForOptimization(epochInstance: EpochInstance):
    algorithmRuntime = epochInstance.inputData.algorithmTimeLimit - (
            datetime.datetime.now().timestamp() - epochInstance.startSolutionTime)

    epochRuntime = epochInstance.inputData.epochTimeLimit - (
            datetime.datetime.now().timestamp() - epochInstance.clockStartEpoch)

    timeLeft = min(algorithmRuntime, epochRuntime)
    return timeLeft > 1e-6


def getEpochWarmStart(epochInstance: EpochInstance, epochStatusQuo: EpochSolution) -> EpochSolution:
    isThereTimeLeftForOptimization = _checkIfThereTimeLeftForOptimization(epochInstance)
    if epochInstance.inputData.improveWarmStart and isThereTimeLeftForOptimization:
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
    binaries = getConflictBinaries(epochInstance.conflictingSets, epochInstance.arcBasedShortestPaths,
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
