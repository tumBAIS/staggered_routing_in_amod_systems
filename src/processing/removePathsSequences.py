from utils.classes import CompleteSolution
from instanceModule.instance import Instance


def _assertEveryVehicleIsInAConflictingSet(instance: Instance, removedVehicles=None):
    if removedVehicles is None:
        removedVehicles = []
    allVehiclesAppearingInConfSets = sorted(
        list(set([vehicle for confSet in instance.conflictingSets for vehicle in confSet])))
    assert all(vehicle not in allVehiclesAppearingInConfSets for vehicle in removedVehicles)
    assert all(vehicle in allVehiclesAppearingInConfSets for vehicle in range(len(instance.trip_routes)) if
               vehicle not in removedVehicles)


def removeVehicleFromSystem(vehicleToRemove: int, instance: Instance, statusQuo: CompleteSolution) -> None:
    instance.maxStaggeringApplicable.pop(vehicleToRemove)
    instance.trip_routes.pop(vehicleToRemove)
    instance.latestDepartureTimes.pop(vehicleToRemove)
    instance.earliestDepartureTimes.pop(vehicleToRemove)
    instance.maxDelayOnArc.pop(vehicleToRemove)
    instance.minDelayOnArc.pop(vehicleToRemove)
    instance.deadlines.pop(vehicleToRemove)
    try:
        instance.dueDates.pop(vehicleToRemove)
    except:
        pass
    statusQuo.releaseTimes.pop(vehicleToRemove)
    statusQuo.congestedSchedule.pop(vehicleToRemove)
    assert sum(statusQuo.delaysOnArcs[vehicleToRemove]) < 1e-6
    statusQuo.delaysOnArcs.pop(vehicleToRemove)
    statusQuo.staggeringApplicable.pop(vehicleToRemove)
    statusQuo.freeFlowSchedule.pop(vehicleToRemove)
    statusQuo.staggeringApplied.pop(vehicleToRemove)

    return


def updateConflictingSetsAfterRemovingVehicles(conflictingSets: list[list[int]],
                                               removedVehicles: list[int]) -> None:
    conflictingSets[:] = [[vehicle - sum(removed < vehicle for removed in removedVehicles) for vehicle in confSet] for
                          confSet in conflictingSets]
    return


def _removeInitialPartOfVehiclePath(instance: Instance, statusQuo: CompleteSolution, vehicle: int) -> None:
    newIndexWhereToStartPath = 0
    for arc in instance.trip_routes[vehicle]:
        if vehicle not in instance.conflictingSets[arc]:
            newIndexWhereToStartPath += 1
            _deleteFirstEntrySchedulesVehicle(instance, statusQuo, vehicle)
        else:
            break
    instance.trip_routes[vehicle] = instance.trip_routes[vehicle][newIndexWhereToStartPath:]


def _assertMaxDelayIsZero(instance, vehicle):
    try:
        instance.maxDelayOnArc[vehicle] != []
    except:
        raise IndexError(f"vehicle {vehicle} has no maxDelayOnArc")
    try:
        instance.maxDelayOnArc[vehicle][0] < 1e-6, \
            f"vehicle {vehicle} can have delay {instance.maxDelayOnArc[vehicle][0]} on his first arc"
    except:
        raise IndexError(f"vehicle: {vehicle} len instanceModule.maxDelayOnArc: {len(instance.maxDelayOnArc[vehicle])}")


def _assertShiftApplicableIsCorrectAfterDeletion(instance, vehicle):
    if instance.latestDepartureTimes[vehicle] != []:
        assert abs(instance.latestDepartureTimes[vehicle][0] - (instance.earliestDepartureTimes[vehicle][0] + \
                                                                instance.maxStaggeringApplicable[
                                                                    vehicle])) < 1e-6, \
            "Shift applicable has changed while removing first part of paths: \n" \
            f"Vehicle: {vehicle}, " \
            f"latest departure time: {instance.latestDepartureTimes[vehicle][0]}, " \
            f"earliest departure time: {instance.earliestDepartureTimes[vehicle][0]} " \
            f"max staggering applicable: {instance.maxStaggeringApplicable[vehicle]}"


def _deleteFirstEntrySchedulesVehicle(instance, statusQuo, vehicle):
    _assertMaxDelayIsZero(instance, vehicle)
    instance.latestDepartureTimes[vehicle].pop(0)
    instance.earliestDepartureTimes[vehicle].pop(0)
    _assertShiftApplicableIsCorrectAfterDeletion(instance, vehicle)
    instance.maxDelayOnArc[vehicle].pop(0)
    instance.minDelayOnArc[vehicle].pop(0)
    statusQuo.congestedSchedule[vehicle].pop(0)
    statusQuo.freeFlowSchedule[vehicle].pop(0)
    assert statusQuo.delaysOnArcs[vehicle][
               0] < 1e-6, f"vehicle {vehicle} has delay {statusQuo.delaysOnArcs[vehicle][0]} on his first arc"
    statusQuo.delaysOnArcs[vehicle].pop(0)
    if statusQuo.congestedSchedule[vehicle]:
        statusQuo.releaseTimes[vehicle] = statusQuo.congestedSchedule[vehicle][0]
    return


def _deleteLastVehicleEntry(instance, statusQuo, vehicle) -> None:
    arcDeleted = instance.trip_routes[vehicle][-2]
    instance.trip_routes[vehicle].pop(-2)
    instance.latestDepartureTimes[vehicle].pop(-1)
    instance.earliestDepartureTimes[vehicle].pop(-1)
    instance.maxDelayOnArc[vehicle].pop(-1)
    instance.minDelayOnArc[vehicle].pop(-1)
    instance.deadlines[vehicle] -= instance.travel_times_arcs[arcDeleted]
    instance.dueDates[vehicle] -= instance.travel_times_arcs[arcDeleted]
    statusQuo.congestedSchedule[vehicle].pop(-1)
    statusQuo.freeFlowSchedule[vehicle].pop(-1)
    assert statusQuo.delaysOnArcs[vehicle][-1] < 1e-6
    statusQuo.delaysOnArcs[vehicle].pop(-1)
    return


def removeInitialPartOfPathsWithoutConflicts(instance: Instance, statusQuo: CompleteSolution) -> None:
    initialNumberOfVehicles = len(instance.trip_routes)
    removedVehicles = []
    for vehicle in sorted(range(initialNumberOfVehicles), reverse=True):
        _removeInitialPartOfVehiclePath(instance, statusQuo, vehicle)
        if not instance.trip_routes[vehicle]:
            removedVehicles.append(vehicle)
            removeVehicleFromSystem(vehicle, instance, statusQuo)

    instance.removedVehicles = removedVehicles[:]  # to map back to original id
    if initialNumberOfVehicles == len(removedVehicles):
        print("All vehicles removed from instanceModule: nothing to optimize.")
        return

    _assertEveryVehicleIsInAConflictingSet(instance, removedVehicles)
    updateConflictingSetsAfterRemovingVehicles(instance.conflictingSets, removedVehicles)
    _assertEveryVehicleIsInAConflictingSet(instance)

    print("Vehicles removed during preprocessing: ", len(removedVehicles))
    print(f"Final number of vehicles in instanceModule: {initialNumberOfVehicles - len(removedVehicles)}")


def removeFinalPartOfPathsWithoutConflicts(instance: Instance, statusQuo: CompleteSolution) -> None:
    for vehicle, path in enumerate(instance.trip_routes):
        for arc in reversed(path):
            if vehicle not in instance.conflictingSets[arc] and arc > 0:
                _deleteLastVehicleEntry(instance, statusQuo, vehicle)
            else:
                break
    return
