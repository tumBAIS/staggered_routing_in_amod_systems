from utils.classes import Solution
from instance_module.epoch_instance import EpochInstance


def _assert_all_vehicles_in_conflicting_set(instance: EpochInstance, removed_vehicles=None) -> None:
    """
    Ensures all active vehicles are part of a conflicting set.
    """
    if removed_vehicles is None:
        removed_vehicles = []

    all_vehicles_in_conf_sets = sorted({
        vehicle for conf_set in instance.conflicting_sets for vehicle in conf_set
    })

    assert all(vehicle not in all_vehicles_in_conf_sets for vehicle in removed_vehicles), \
        "Removed vehicles are still in conflicting sets."
    assert all(vehicle in all_vehicles_in_conf_sets for vehicle in range(len(instance.trip_routes))
               if vehicle not in removed_vehicles), "Some active vehicles are not in conflicting sets."


def remove_vehicle_from_system(vehicle: int, instance: EpochInstance, status_quo: Solution) -> None:
    """
    Remove a vehicle from the system, including related schedules and instance properties.
    """
    instance.max_staggering_applicable.pop(vehicle)
    instance.trip_routes.pop(vehicle)
    instance.latest_departure_times.pop(vehicle)
    instance.earliest_departure_times.pop(vehicle)
    instance.max_delay_on_arc.pop(vehicle)
    instance.min_delay_on_arc.pop(vehicle)
    instance.deadlines.pop(vehicle)
    status_quo.release_times.pop(vehicle)
    status_quo.congested_schedule.pop(vehicle)
    assert sum(status_quo.delays_on_arcs[vehicle]) < 1e-6, "Vehicle has non-zero delays on arcs."
    status_quo.delays_on_arcs.pop(vehicle)
    status_quo.staggering_applicable.pop(vehicle)
    status_quo.free_flow_schedule.pop(vehicle)
    status_quo.staggering_applied.pop(vehicle)


def update_conflicting_sets(conflicting_sets: list[list[int]], removed_vehicles: list[int]) -> None:
    """
    Update conflicting sets after vehicles are removed.
    """
    conflicting_sets[:] = [
        [vehicle - sum(removed < vehicle for removed in removed_vehicles) for vehicle in conf_set]
        for conf_set in conflicting_sets
    ]


def remove_initial_part_of_path(instance: EpochInstance, status_quo: Solution, vehicle: int) -> None:
    """
    Remove the initial part of a vehicle's path where there are no conflicts.
    """
    initial_route = instance.trip_routes[vehicle][:]

    for arc in initial_route:
        if vehicle in instance.conflicting_sets[arc]:
            break

        # Remove the arc from the vehicle's route and update the solution state
        instance.remove_arc_at_position_from_trip_route(vehicle, 0)
        status_quo.remove_trip_at_position_entry_from_solution(vehicle, 0)


def _remove_first_entry(instance: EpochInstance, status_quo: Solution, vehicle: int) -> None:
    """
    Remove the first entry from the vehicle's schedules and paths.
    """
    instance.latest_departure_times[vehicle].pop(0)
    instance.earliest_departure_times[vehicle].pop(0)
    instance.max_delay_on_arc[vehicle].pop(0)
    instance.min_delay_on_arc[vehicle].pop(0)
    status_quo.congested_schedule[vehicle].pop(0)
    status_quo.free_flow_schedule[vehicle].pop(0)
    assert status_quo.delays_on_arcs[vehicle][0] < 1e-6, "Vehicle has delay on the first arc."
    status_quo.delays_on_arcs[vehicle].pop(0)

    if status_quo.congested_schedule[vehicle]:
        status_quo.release_times[vehicle] = status_quo.congested_schedule[vehicle][0]


def _remove_last_entry(instance: EpochInstance, status_quo: Solution, vehicle: int) -> None:
    """
    Remove the last entry from the vehicle's schedules and paths.
    """
    last_arc = instance.trip_routes[vehicle][-2]
    instance.trip_routes[vehicle].pop(-2)
    instance.latest_departure_times[vehicle].pop(-1)
    instance.earliest_departure_times[vehicle].pop(-1)
    instance.max_delay_on_arc[vehicle].pop(-1)
    instance.min_delay_on_arc[vehicle].pop(-1)
    instance.deadlines[vehicle] -= instance.travel_times_arcs[last_arc]
    status_quo.congested_schedule[vehicle].pop(-1)
    status_quo.free_flow_schedule[vehicle].pop(-1)
    assert status_quo.delays_on_arcs[vehicle][-1] < 1e-6, "Vehicle has non-zero delay on last arc."
    status_quo.delays_on_arcs[vehicle].pop(-1)


def remove_initial_paths(instance: EpochInstance, status_quo: Solution) -> None:
    """
    Remove the initial parts of paths without conflicts and remove vehicles with no remaining paths.
    """
    initial_vehicle_count = len(instance.trip_routes)
    removed_vehicles = []

    for vehicle in reversed(range(initial_vehicle_count)):
        remove_initial_part_of_path(instance, status_quo, vehicle)
        if not instance.trip_routes[vehicle]:
            removed_vehicles.append(vehicle)
            remove_vehicle_from_system(vehicle, instance, status_quo)

    instance.removed_vehicles = removed_vehicles

    if initial_vehicle_count == len(removed_vehicles):
        print("All vehicles removed. Nothing to optimize.")
        return

    _assert_all_vehicles_in_conflicting_set(instance, removed_vehicles)
    update_conflicting_sets(instance.conflicting_sets, removed_vehicles)
    _assert_all_vehicles_in_conflicting_set(instance)

    print(f"Vehicles removed: {len(removed_vehicles)}")
    print(f"Remaining vehicles: {initial_vehicle_count - len(removed_vehicles)}")


def remove_final_paths(instance: EpochInstance, status_quo: Solution) -> None:
    """
    Remove the final parts of paths without conflicts.
    """
    for vehicle, path in enumerate(instance.trip_routes):
        for arc in reversed(path):
            if vehicle not in instance.conflicting_sets[arc] and arc > 0:
                _remove_last_entry(instance, status_quo, vehicle)
            else:
                break
