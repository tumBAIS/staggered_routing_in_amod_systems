from utils.classes import Solution
from instance_module.epoch_instance import EpochInstance


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
            instance.remove_arc_at_position_from_trip_route(trip, 0, "first")
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
    Remove the final parts of paths without conflicts, starting from the second-to-last arc.

    Args:
        instance (EpochInstance): The problem instance containing trip routes and conflict data.
        status_quo (Solution): The current solution state to be updated.
    """
    for trip, route in enumerate(instance.trip_routes):
        reversed_route = list(reversed(route[:-1]))
        for index, arc in enumerate(reversed_route, 1):  # Start from the second-to-last arc
            position = len(reversed_route) - index  # Calculate the original index in the route
            if trip in instance.conflicting_sets[arc]:
                break
            instance.remove_arc_at_position_from_trip_route(trip, position, "last")
            status_quo.remove_trip_at_position_entry_from_solution(trip, position + 1)
