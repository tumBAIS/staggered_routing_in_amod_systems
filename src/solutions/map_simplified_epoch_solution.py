import datetime

from congestion_model.core import get_congested_schedule, get_free_flow_schedule, \
    get_total_travel_time, get_total_delay, get_delays_on_arcs
from instance_module.epoch_instance import EpochInstance
from utils.classes import EpochSolution


def map_simplified_epoch_solution(epochInstance: EpochInstance,
                                  simplifiedEpochSolution: EpochSolution) -> EpochSolution:
    releaseTimesEpoch = epochInstance.release_times
    removedVehicles = epochInstance.removed_vehicles  # to map back
    staggeringAppliedInEpoch = simplifiedEpochSolution.staggering_applied[:]
    staggeringApplicable = simplifiedEpochSolution.staggering_applicable[:]

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
    epochInstance.clock_end_epoch = datetime.datetime.now().timestamp()
    print(
        f"Time to complete the epoch: {epochInstance.clock_end_epoch - epochInstance.clock_start_epoch:.2f} [s]")
    print(f"total delay mapped solution: {totalDelay / 60:.2f} [min]")
    epochSolution = EpochSolution(total_delay=totalDelay,
                                  congested_schedule=congestedSchedule,
                                  delays_on_arcs=delaysOnArcs,
                                  release_times=staggeredReleaseTimes,
                                  staggering_applicable=staggeringApplicable,
                                  free_flow_schedule=freeFlowSchedule,
                                  staggering_applied=staggeringAppliedInEpoch,
                                  total_travel_time=totalTravelTime,
                                  vehicles_utilizing_arcs=simplifiedEpochSolution.vehicles_utilizing_arcs)
    return epochSolution
