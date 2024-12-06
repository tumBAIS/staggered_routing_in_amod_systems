from instanceModule.epochInstance import EpochInstance
from utils.classes import EpochSolution, CompleteSolution
from instanceModule.instance import Instance
from utils.aliases import VehicleSchedules
from congestion_model.core import getDelaysOnArcs, getFreeFlowSchedule, \
    getStaggeringApplicable, getTotalDelay, getTotalTravelTime, getCongestedSchedule

from congestion_model.conflict_binaries import getConflictBinaries
from conflicting_sets.get import add_conflicting_sets_to_instance

from inputData import ACTIVATE_ASSERTIONS


def _mergeSchedules(scheduleConstructedSoFar: list[float], scheduleToAdd: list[float]):
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


def _reconstructSchedule(epochInstances: list[EpochInstance], epochStatusQuoList: list[EpochSolution],
                         globalInstance: Instance) -> VehicleSchedules:
    reconstructedSchedule = [[] for _ in range(len(globalInstance.trip_routes))]  # type: ignore
    for epochID, epochInstance in enumerate(epochInstances):
        for vehicleEpochID, vehicleGlobalID in enumerate(epochInstance.vehiclesOriginalIDS):
            lastPosition = epochInstance.lastPositionForReconstruction[vehicleEpochID]
            reconstructedSchedule[vehicleGlobalID] = _mergeSchedules(reconstructedSchedule[vehicleGlobalID],
                                                                     epochStatusQuoList[epochID].congestedSchedule[
                                                                         vehicleEpochID][:lastPosition])
    return reconstructedSchedule


def _printNotMatchingSchedules(globalInstance, reconstructedSchedule, cppSchedule, vehicle):
    print(f"schedules of vehicle {vehicle} do not match")
    print("Reconstructed schedule:")
    print(reconstructedSchedule[vehicle])
    print("cpp Schedule vehicle:")
    print(cppSchedule[vehicle])
    notMatchingEntries = [position for position, departure in enumerate(reconstructedSchedule[vehicle]) if
                          abs(departure - cppSchedule[vehicle][position]) > 1e-4]
    print(f"Position entries not matching: {notMatchingEntries}")
    for arc in globalInstance.trip_routes[vehicle]:
        confSet = globalInstance.conflictingSets[arc]
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


def _assertCongestedScheduleIsCorrect(globalInstance, reconstructedSchedule):
    if ACTIVATE_ASSERTIONS:
        releaseTimes = [vehicleSchedule[0] for vehicleSchedule in reconstructedSchedule]
        cppSchedule = getCongestedSchedule(globalInstance, releaseTimes)
        for vehicle, schedule in enumerate(reconstructedSchedule):
            assert all(
                abs(rDeparture - cppDeparture) < 1e-4 for rDeparture, cppDeparture in
                zip(schedule, cppSchedule[
                    vehicle])), f"schedules do not coincide: " \
                                f"\n {_printNotMatchingSchedules(globalInstance, reconstructedSchedule, cppSchedule, vehicle)}"


def reconstruct_solution(epochInstances: list[EpochInstance], epochStatusQuoList: list[EpochSolution],
                         globalInstance: Instance) -> CompleteSolution:
    congestedSchedule = _reconstructSchedule(epochInstances, epochStatusQuoList, globalInstance)
    _assertCongestedScheduleIsCorrect(globalInstance, congestedSchedule)
    delaysOnArcs = getDelaysOnArcs(globalInstance, congestedSchedule)
    freeFlowSchedule = getFreeFlowSchedule(globalInstance, congestedSchedule)
    releaseTimes = [schedule[0] for schedule in congestedSchedule]
    staggeringApplied = [schedule[0] - datasetTime for schedule, datasetTime in
                         zip(congestedSchedule, globalInstance.releaseTimesDataset)]
    staggeringApplicable = getStaggeringApplicable(globalInstance, staggeringApplied)
    totalDelay = getTotalDelay(freeFlowSchedule, congestedSchedule)
    totalTravelTime = getTotalTravelTime(congestedSchedule)
    add_conflicting_sets_to_instance(globalInstance, freeFlowSchedule)
    binaries = getConflictBinaries(globalInstance.conflictingSets, globalInstance.trip_routes,
                                   congestedSchedule)

    return CompleteSolution(
        delaysOnArcs=delaysOnArcs,
        freeFlowSchedule=freeFlowSchedule,
        releaseTimes=releaseTimes,
        staggeringApplicable=staggeringApplicable,
        totalDelay=totalDelay,
        congestedSchedule=congestedSchedule,
        staggeringApplied=staggeringApplied,
        totalTravelTime=totalTravelTime,
        binaries=binaries
    )
