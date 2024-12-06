import datetime

from congestion_model.core import get_congested_schedule, get_free_flow_schedule, \
    get_total_travel_time, get_total_delay, get_delays_on_arcs
from instanceModule.epoch_instance import EpochInstance
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

    congestedSchedule = get_congested_schedule(epochInstance, staggeredReleaseTimes)
    freeFlowSchedule = get_free_flow_schedule(epochInstance, congestedSchedule)
    totalDelay = get_total_delay(freeFlowSchedule, congestedSchedule)
    totalTravelTime = get_total_travel_time(congestedSchedule)
    delaysOnArcs = get_delays_on_arcs(epochInstance, congestedSchedule)
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
