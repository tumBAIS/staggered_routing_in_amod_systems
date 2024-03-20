from __future__ import annotations

import cpp_module as cpp
from instanceModule.instance import Instance
from instanceModule.epochInstance import EpochInstance
from utils.aliases import *
from utils.aliases import Time


def getFreeFlowSchedule(instance: Instance | EpochInstance,
                        congestedSchedule: list[VehicleSchedule]) -> list[VehicleSchedule]:
    freeFlowSchedule = [[schedule[0]] for schedule in congestedSchedule]

    for vehicle, path in enumerate(instance.arcBasedShortestPaths):
        for arcIndex, arc in enumerate(path[:-1]):
            departureTime = freeFlowSchedule[vehicle][-1] + instance.travelTimesArcsUtilized[arc]
            freeFlowSchedule[vehicle].append(departureTime)

    return freeFlowSchedule


def getCongestedSchedule(instance: Instance | EpochInstance,
                         releaseTimes: list[float]) -> list[VehicleSchedule]:
    cppParameters = [instance.inputData.algorithmTimeLimit]

    congestedScheduleStatusQuo = cpp.cppComputeCongestedSchedule(
        instance.arcBasedShortestPaths,
        releaseTimes,
        instance.travelTimesArcsUtilized,
        instance.nominalCapacitiesArcs,
        instance.inputData.list_of_slopes,
        instance.inputData.list_of_thresholds,
        cppParameters
    )
    releaseTimes[:] = [schedule[0] for schedule in congestedScheduleStatusQuo]
    return congestedScheduleStatusQuo


def getTotalDelay(freeFlowSchedule: list[VehicleSchedule], congestedSchedule: list[VehicleSchedule]) -> float:
    totalDelay = sum(congestedSchedule[vehicle][-1] - congestedSchedule[vehicle][0] -
                     (freeFlowSchedule[vehicle][-1] - freeFlowSchedule[vehicle][0])
                     for vehicle in range(len(congestedSchedule)))
    return totalDelay


def getDelaysOnArcs(instance: Instance | EpochInstance,
                    congestedSchedule: list[VehicleSchedule]) -> list[VehicleSchedule]:
    delaysOnArcs = [
        [
            congestedSchedule[vehicle][position + 1] - congestedSchedule[vehicle][position] -
            instance.travelTimesArcsUtilized[arc]
            for position, arc in enumerate(path[:-1])
        ]
        for vehicle, path in enumerate(instance.arcBasedShortestPaths)
    ]
    delaysOnArcs = [[0 if abs(element) < 1e-6 else element for element in delays] + [0] for delays in delaysOnArcs]
    return delaysOnArcs


def getTotalTravelTime(vehicleSchedule: list[VehicleSchedule]) -> float:
    return sum([schedule[-1] - schedule[0] for schedule in vehicleSchedule])


def getStaggeringApplicable(instance: Instance | EpochInstance, staggeringApplied: list[float]):
    return [vMaxStaggeringApplicable - vStaggeringApplied for vMaxStaggeringApplicable, vStaggeringApplied in
            zip(instance.maxStaggeringApplicable, staggeringApplied)]


def addMaxStaggeringApplicableToInstance(instance: Instance, freeFlowSchedule: list[VehicleSchedule]):
    # Calculate the maximum staggering for each vehicle based on the free flow schedule if maxStaggering in input data
    # is positive, otherwise set maximum staggering to inf
    staggeringCaps = [
        instance.inputData.staggeringCapPercentage / 100 * (freeFlow[-1] - freeFlow[0])
        if instance.inputData.staggeringCapPercentage >= 0 else float("inf") for freeFlow in freeFlowSchedule
    ]

    # Calculate the maximum applicable staggering for each vehicle as the minimum between the maxStaggering computed
    # above and the deadline slack (deadline - arrival at free flow)
    maxStaggeringApplicable = [
        min(deadline - freeFlow[-1], stagCap)
        for deadline, freeFlow, stagCap
        in zip(instance.deadlines, freeFlowSchedule, staggeringCaps)
    ]

    # Compute the total staggering applicable and total free flow time (print)
    totalStaggeringApplicable = sum(maxStaggeringApplicable)
    totalFreeFlowTime = sum(schedule[-1] - schedule[0] for schedule in freeFlowSchedule)

    # Print information about the total staggering applicable
    print(f"Total staggering applicable is {round(totalStaggeringApplicable / 60, 2)} [min]"
          f"({round(totalStaggeringApplicable / totalFreeFlowTime * 100, 2)}% of the total free flow time)")
    instance.maxStaggeringApplicable = maxStaggeringApplicable
    return


def getDeadlines(instance: Instance) -> list[Time]:
    """Create list of the latest arrival time at destination for trips.
    It is assumed to be the arrival time at the destination plus a delta
    inputData.deadlineFactor: value comprised between 0 and 100, denotes percentage of status quo
    travel time to use to extend the deadline
    :return list of deadlines
    """
    congestedSchedule = getCongestedSchedule(instance, instance.releaseTimesDataset)
    freeFlowSchedule = getFreeFlowSchedule(instance, congestedSchedule)
    deadlines = []
    for vehicle, schedule in enumerate(congestedSchedule):
        congestedArrival = schedule[-1]
        totTimeFreeFlow = freeFlowSchedule[vehicle][-1] - freeFlowSchedule[vehicle][0]
        delta = totTimeFreeFlow * instance.inputData.deadlineFactor / 100
        deadline = congestedArrival + delta + 30
        deadlines.append(deadline)

    print(f"Deadline delta is {instance.inputData.deadlineFactor} % of nominal travel time")
    return deadlines
