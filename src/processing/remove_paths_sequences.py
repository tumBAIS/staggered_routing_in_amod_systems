from utils.classes import CompleteSolution
from instanceModule.instance import Instance


def _assert_every_vehicle_is_in_a_conflicting_set(instance: Instance, removedVehicles=None):
    if removedVehicles is None:
        removedVehicles = []
    allVehiclesAppearingInConfSets = sorted(
        list(set([vehicle for confSet in instance.conflicting_sets for vehicle in confSet])))
    assert all(vehicle not in allVehiclesAppearingInConfSets for vehicle in removedVehicles)
    assert all(vehicle in allVehiclesAppearingInConfSets for vehicle in range(len(instance.trip_routes)) if
               vehicle not in removedVehicles)


def remove_vehicle_from_system(vehicleToRemove: int, instance: Instance, statusQuo: CompleteSolution) -> None:
    instance.max_staggering_applicable.pop(vehicleToRemove)
    instance.trip_routes.pop(vehicleToRemove)
    instance.latest_departure_times.pop(vehicleToRemove)
    instance.earliest_departure_times.pop(vehicleToRemove)
    instance.max_delay_on_arc.pop(vehicleToRemove)
    instance.min_delay_on_arc.pop(vehicleToRemove)
    instance.deadlines.pop(vehicleToRemove)
    try:
        instance.due_dates.pop(vehicleToRemove)
    except:
        pass
    statusQuo.release_times.pop(vehicleToRemove)
    statusQuo.congested_schedule.pop(vehicleToRemove)
    assert sum(statusQuo.delays_on_arcs[vehicleToRemove]) < 1e-6
    statusQuo.delays_on_arcs.pop(vehicleToRemove)
    statusQuo.staggering_applicable.pop(vehicleToRemove)
    statusQuo.free_flow_schedule.pop(vehicleToRemove)
    statusQuo.staggering_applied.pop(vehicleToRemove)

    return


def update_conflicting_sets_after_removing_vehicles(conflictingSets: list[list[int]],
                                                    removedVehicles: list[int]) -> None:
    conflictingSets[:] = [[vehicle - sum(removed < vehicle for removed in removedVehicles) for vehicle in confSet] for
                          confSet in conflictingSets]
    return


def _remove_initial_part_of_vehicle_path(instance: Instance, statusQuo: CompleteSolution, vehicle: int) -> None:
    newIndexWhereToStartPath = 0
    for arc in instance.trip_routes[vehicle]:
        if vehicle not in instance.conflicting_sets[arc]:
            newIndexWhereToStartPath += 1
            _delete_first_entry_schedules_vehicle(instance, statusQuo, vehicle)
        else:
            break
    instance.trip_routes[vehicle] = instance.trip_routes[vehicle][newIndexWhereToStartPath:]


def _assert_max_delay_is_zero(instance, vehicle):
    try:
        instance.max_delay_on_arc[vehicle] != []
    except IndexError:
        raise IndexError(f"vehicle {vehicle} has no maxDelayOnArc")
    try:
        instance.max_delay_on_arc[vehicle][0] < 1e-6, \
            f"vehicle {vehicle} can have delay {instance.max_delay_on_arc[vehicle][0]} on his first arc"
    except IndexError:
        raise IndexError(
            f"vehicle: {vehicle} len instanceModule.maxDelayOnArc: {len(instance.max_delay_on_arc[vehicle])}")


def _assert_shift_applicable_is_correct_after_deletion(instance, vehicle):
    if instance.latest_departure_times[vehicle]:
        assert abs(instance.latest_departure_times[vehicle][0] - (instance.earliest_departure_times[vehicle][0] +
                                                                  instance.max_staggering_applicable[
                                                                      vehicle])) < 1e-6, \
            "Shift applicable has changed while removing first part of paths: \n" \
            f"Vehicle: {vehicle}, " \
            f"latest departure time: {instance.latest_departure_times[vehicle][0]}, " \
            f"earliest departure time: {instance.earliest_departure_times[vehicle][0]} " \
            f"max staggering applicable: {instance.max_staggering_applicable[vehicle]}"


def _delete_first_entry_schedules_vehicle(instance, statusQuo, vehicle):
    _assert_max_delay_is_zero(instance, vehicle)
    instance.latest_departure_times[vehicle].pop(0)
    instance.earliest_departure_times[vehicle].pop(0)
    _assert_shift_applicable_is_correct_after_deletion(instance, vehicle)
    instance.max_delay_on_arc[vehicle].pop(0)
    instance.min_delay_on_arc[vehicle].pop(0)
    statusQuo.congested_schedule[vehicle].pop(0)
    statusQuo.free_flow_schedule[vehicle].pop(0)
    assert statusQuo.delays_on_arcs[vehicle][
               0] < 1e-6, f"vehicle {vehicle} has delay {statusQuo.delays_on_arcs[vehicle][0]} on his first arc"
    statusQuo.delays_on_arcs[vehicle].pop(0)
    if statusQuo.congested_schedule[vehicle]:
        statusQuo.release_times[vehicle] = statusQuo.congested_schedule[vehicle][0]
    return


def _delete_last_vehicle_entry(instance, statusQuo, vehicle) -> None:
    arcDeleted = instance.trip_routes[vehicle][-2]
    instance.trip_routes[vehicle].pop(-2)
    instance.latest_departure_times[vehicle].pop(-1)
    instance.earliest_departure_times[vehicle].pop(-1)
    instance.max_delay_on_arc[vehicle].pop(-1)
    instance.min_delay_on_arc[vehicle].pop(-1)
    instance.deadlines[vehicle] -= instance.travel_times_arcs[arcDeleted]
    instance.due_dates[vehicle] -= instance.travel_times_arcs[arcDeleted]
    statusQuo.congested_schedule[vehicle].pop(-1)
    statusQuo.free_flow_schedule[vehicle].pop(-1)
    assert statusQuo.delays_on_arcs[vehicle][-1] < 1e-6
    statusQuo.delays_on_arcs[vehicle].pop(-1)
    return


def remove_initial_part_of_paths_without_conflicts(instance: Instance, statusQuo: CompleteSolution) -> None:
    initialNumberOfVehicles = len(instance.trip_routes)
    removedVehicles = []
    for vehicle in sorted(range(initialNumberOfVehicles), reverse=True):
        _remove_initial_part_of_vehicle_path(instance, statusQuo, vehicle)
        if not instance.trip_routes[vehicle]:
            removedVehicles.append(vehicle)
            remove_vehicle_from_system(vehicle, instance, statusQuo)

    instance.removed_vehicles = removedVehicles[:]  # to map back to original id
    if initialNumberOfVehicles == len(removedVehicles):
        print("All vehicles removed from instanceModule: nothing to optimize.")
        return

    _assert_every_vehicle_is_in_a_conflicting_set(instance, removedVehicles)
    update_conflicting_sets_after_removing_vehicles(instance.conflicting_sets, removedVehicles)
    _assert_every_vehicle_is_in_a_conflicting_set(instance)

    print("Vehicles removed during preprocessing: ", len(removedVehicles))
    print(f"Final number of vehicles in instanceModule: {initialNumberOfVehicles - len(removedVehicles)}")


def remove_final_part_of_paths_without_conflicts(instance: Instance, statusQuo: CompleteSolution) -> None:
    for vehicle, path in enumerate(instance.trip_routes):
        for arc in reversed(path):
            if vehicle not in instance.conflicting_sets[arc] and arc > 0:
                _delete_last_vehicle_entry(instance, statusQuo, vehicle)
            else:
                break
    return
