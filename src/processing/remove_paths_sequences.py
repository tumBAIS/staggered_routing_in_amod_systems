from utils.classes import Solution
from instance_module.epoch_instance import EpochInstance


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

    for trip in reversed(range(initial_vehicle_count)):
        initial_route = instance.trip_routes[trip][:]  # Modified in place

        for arc in initial_route:
            if trip in instance.conflicting_sets[arc]:
                break

            # Remove the arc from the vehicle's route and update the solution state
            instance.remove_arc_at_position_from_trip_route(trip, 0)
            status_quo.remove_trip_at_position_entry_from_solution(trip, 0)

        # Remove the trip if no routes are left
        if not instance.trip_routes[trip]:
            instance.remove_trip(trip)
            status_quo.remove_trip(trip)

    # Handle the case where all vehicles are removed
    if not instance.trip_routes:
        print("All vehicles removed. Nothing to optimize.")
        return

    # Update conflicting sets for the remaining vehicles
    instance.update_conflicting_sets_after_trip_removal()

    print(f"Vehicles removed: {len(instance.removed_vehicles)}")
    print(f"Remaining vehicles: {initial_vehicle_count - len(instance.removed_vehicles)}")


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
