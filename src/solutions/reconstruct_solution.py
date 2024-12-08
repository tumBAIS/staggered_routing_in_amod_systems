from instance_module.epoch_instance import EpochInstance
from utils.classes import EpochSolution, CompleteSolution
from instance_module.instance import Instance
from utils.aliases import VehicleSchedules
from congestion_model.core import get_delays_on_arcs, get_free_flow_schedule, \
    get_staggering_applicable, get_total_delay, get_total_travel_time, get_congested_schedule

from congestion_model.conflict_binaries import get_conflict_binaries
from conflicting_sets.schedule_utilities import add_conflicting_sets_to_instance

from input_data import ACTIVATE_ASSERTIONS


def _merge_schedules(scheduleConstructedSoFar: list[float], scheduleToAdd: list[float]):
    if not scheduleToAdd:
        return scheduleConstructedSoFar
    # Find the index of the first common element between list1 and list2
    common_element = None
    saved_idx = None
    for idx, item1 in enumerate(scheduleConstructedSoFar):
        if abs(item1 - scheduleToAdd[0]) < 1e-1:
            common_element = item1
            saved_idx = idx
            break

    if common_element is not None:

        # Remove elements from list1 starting from the common element
        scheduleConstructedSoFar = scheduleConstructedSoFar[:saved_idx]

        # Extend list1 with the elements from list2 starting from the common element
        scheduleConstructedSoFar.extend(scheduleToAdd)
    else:
        # If no common element found, simply extend list1 with list2
        scheduleConstructedSoFar.extend(scheduleToAdd)

    return scheduleConstructedSoFar


def _reconstruct_schedule(epochInstances: list[EpochInstance], epochStatusQuoList: list[EpochSolution],
                          globalInstance: Instance) -> VehicleSchedules:
    reconstructedSchedule = [[] for _ in range(len(globalInstance.trip_routes))]  # type: ignore
    for epochID, epochInstance in enumerate(epochInstances):
        for vehicleEpochID, vehicleGlobalID in enumerate(epochInstance.vehicles_original_ids):
            lastPosition = epochInstance.last_position_for_reconstruction[vehicleEpochID]
            reconstructedSchedule[vehicleGlobalID] = _merge_schedules(reconstructedSchedule[vehicleGlobalID],
                                                                      epochStatusQuoList[epochID].congested_schedule[
                                                                          vehicleEpochID][:lastPosition])
    return reconstructedSchedule


def _print_not_matching_schedules(globalInstance, reconstructedSchedule, cppSchedule, vehicle):
    print(f"schedules of vehicle {vehicle} do not match")
    print("Reconstructed schedule:")
    print(reconstructedSchedule[vehicle])
    print("cpp Schedule vehicle:")
    print(cppSchedule[vehicle])
    notMatchingEntries = [position for position, departure in enumerate(reconstructedSchedule[vehicle]) if
                          abs(departure - cppSchedule[vehicle][position]) > 1e-4]
    print(f"Position entries not matching: {notMatchingEntries}")
    for arc in globalInstance.trip_routes[vehicle]:
        confSet = globalInstance.conflicting_sets[arc]
        cppDepAndArrOnArc = []
        rekDepAndArrOnArc = []
        for otherVehicle in confSet:
            position = globalInstance.trip_routes[otherVehicle].index(arc)
            cppDeparture = cppSchedule[otherVehicle][position]
            cppArrival = cppSchedule[otherVehicle][position + 1]
            cppDepAndArrOnArc.append((cppDeparture, cppArrival, otherVehicle))

            rekDeparture = reconstructedSchedule[otherVehicle][position]
            rekArrival = reconstructedSchedule[otherVehicle][position + 1]
            rekDepAndArrOnArc.append((rekDeparture, rekArrival, otherVehicle))
        print(
            f"arc : {arc}, capacity: {globalInstance.capacities_arcs[arc]}. travel time : {globalInstance.travel_times_arcs[arc]}")
        print("cpp dep and arrivals")
        print(sorted(cppDepAndArrOnArc, key=lambda x: x[0])) if cppDepAndArrOnArc else None
        print("rek dep and arrivals")
        print(sorted(rekDepAndArrOnArc, key=lambda x: x[0])) if rekDepAndArrOnArc else None


def _assert_congested_schedule_is_correct(globalInstance, reconstructedSchedule):
    if ACTIVATE_ASSERTIONS:
        releaseTimes = [vehicleSchedule[0] for vehicleSchedule in reconstructedSchedule]
        cppSchedule = get_congested_schedule(globalInstance, releaseTimes)
        for vehicle, schedule in enumerate(reconstructedSchedule):
            assert all(
                abs(rDeparture - cppDeparture) < 1e-4 for rDeparture, cppDeparture in
                zip(schedule, cppSchedule[
                    vehicle])), f"schedules do not coincide: " \
                                f"\n {_print_not_matching_schedules(globalInstance, reconstructedSchedule, cppSchedule, vehicle)}"


def reconstruct_solution(epochInstances: list[EpochInstance], epochStatusQuoList: list[EpochSolution],
                         globalInstance: Instance) -> CompleteSolution:
    congestedSchedule = _reconstruct_schedule(epochInstances, epochStatusQuoList, globalInstance)
    _assert_congested_schedule_is_correct(globalInstance, congestedSchedule)
    delaysOnArcs = get_delays_on_arcs(globalInstance, congestedSchedule)
    freeFlowSchedule = get_free_flow_schedule(globalInstance, congestedSchedule)
    releaseTimes = [schedule[0] for schedule in congestedSchedule]
    staggeringApplied = [schedule[0] - datasetTime for schedule, datasetTime in
                         zip(congestedSchedule, globalInstance.release_times_dataset)]
    staggeringApplicable = get_staggering_applicable(globalInstance, staggeringApplied)
    totalDelay = get_total_delay(freeFlowSchedule, congestedSchedule)
    totalTravelTime = get_total_travel_time(congestedSchedule)
    add_conflicting_sets_to_instance(globalInstance, freeFlowSchedule)
    binaries = get_conflict_binaries(globalInstance.conflicting_sets, globalInstance.trip_routes,
                                     congestedSchedule)

    return CompleteSolution(
        delays_on_arcs=delaysOnArcs,
        free_flow_schedule=freeFlowSchedule,
        release_times=releaseTimes,
        staggering_applicable=staggeringApplicable,
        total_delay=totalDelay,
        congested_schedule=congestedSchedule,
        staggering_applied=staggeringApplied,
        total_travel_time=totalTravelTime,
        binaries=binaries
    )
