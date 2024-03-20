import datetime

from congestionModel.core import getCongestedSchedule, getFreeFlowSchedule, \
    getTotalTravelTime, getTotalDelay, getDelaysOnArcs
from instanceModule.epochInstance import EpochInstance
from utils.classes import EpochSolution


def mapSimplifiedEpochSolution(epochInstance: EpochInstance,
                               simplifiedEpochSolution: EpochSolution) -> EpochSolution:
    releaseTimesEpoch = epochInstance.releaseTimes
    removedVehicles = epochInstance.removedVehicles  # to map back
    staggeringAppliedInEpoch = simplifiedEpochSolution.staggeringApplied[:]
    staggeringApplicable = simplifiedEpochSolution.staggeringApplicable[:]

    # reinsert vehicles in schedule
    for vehicle in sorted(removedVehicles):
        staggeringAppliedInEpoch.insert(vehicle, 0)
        staggeringApplicable.insert(vehicle, 0)
    staggeredReleaseTimes = [releaseTime + staggering for releaseTime, staggering in
                             zip(releaseTimesEpoch, staggeringAppliedInEpoch)]

    congestedSchedule = getCongestedSchedule(epochInstance, staggeredReleaseTimes)
    freeFlowSchedule = getFreeFlowSchedule(epochInstance, congestedSchedule)
    totalDelay = getTotalDelay(freeFlowSchedule, congestedSchedule)
    totalTravelTime = getTotalTravelTime(congestedSchedule)
    delaysOnArcs = getDelaysOnArcs(epochInstance, congestedSchedule)
    epochInstance.clockEndEpoch = datetime.datetime.now().timestamp()
    print(
        f"Time to complete the epoch: {epochInstance.clockEndEpoch - epochInstance.clockStartEpoch:.2f} [s]")
    print(f"total delay mapped solution: {totalDelay / 60:.2f} [min]")
    epochSolution = EpochSolution(totalDelay=totalDelay,
                                  congestedSchedule=congestedSchedule,
                                  delaysOnArcs=delaysOnArcs,
                                  releaseTimes=staggeredReleaseTimes,
                                  staggeringApplicable=staggeringApplicable,
                                  freeFlowSchedule=freeFlowSchedule,
                                  staggeringApplied=staggeringAppliedInEpoch,
                                  totalTravelTime=totalTravelTime,
                                  vehiclesUtilizingArcs=simplifiedEpochSolution.vehiclesUtilizingArcs)
    return epochSolution
