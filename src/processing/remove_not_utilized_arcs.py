from input_data import ACTIVATE_ASSERTIONS
from instance_module.instance import Instance
from instance_module.epoch_instance import EpochInstance


def _get_vehicles_utilizing_arcs(instance: Instance) -> list[list[int]]:
    """
    Get a list of vehicles utilizing each arc.
    """
    vehicles_utilizing_arcs = [[] for _ in instance.travel_times_arcs]
    for vehicle, path in enumerate(instance.trip_routes):
        for arc in path:
            vehicles_utilizing_arcs[arc].append(vehicle)
    return vehicles_utilizing_arcs


def _update_trip_routes(instance: Instance, arcs_to_remove: list[int]) -> None:
    """
    Update the IDs in trip routes after removing arcs.
    """
    if arcs_to_remove:
        for path in instance.trip_routes:
            for i, arc in enumerate(path):
                path[i] -= sum(1 for removed_arc in arcs_to_remove if removed_arc < arc)


def _assert_arc_not_in_use(conflicting_set: list[int], paths: list[list[int]]) -> None:
    """
    Assert that an arc is not in use by any vehicle before removal.
    """
    if ACTIVATE_ASSERTIONS and conflicting_set:
        print(f"Conflicting set: {conflicting_set}")
        for vehicle in conflicting_set:
            print(f"Vehicle {vehicle}: {paths[vehicle]}")
        raise RuntimeError("Attempted to delete an arc that is still in use!")


def _remove_arcs(instance: Instance, arcs_to_remove: list[int]) -> None:
    """
    Remove arcs from the instance's data structures.
    """
    if arcs_to_remove:
        assert arcs_to_remove == sorted(arcs_to_remove), "Arcs to remove are not sorted!"
        for arc in reversed(arcs_to_remove):
            instance.travel_times_arcs.pop(arc)
            instance.capacities_arcs.pop(arc)
            _assert_arc_not_in_use(instance.conflicting_sets[arc], instance.trip_routes)
            instance.conflicting_sets.pop(arc)


def remove_not_utilized_arcs(instance: EpochInstance) -> list[int]:
    """
    Remove arcs that are not utilized by any vehicle and update the instance accordingly.
    """
    # Identify unused arcs
    vehicles_utilizing_arcs = _get_vehicles_utilizing_arcs(instance)
    arcs_to_remove = [arc for arc, vehicles in enumerate(vehicles_utilizing_arcs) if not vehicles]

    # Remove the unused arcs and update references
    _remove_arcs(instance, arcs_to_remove)
    _update_trip_routes(instance, arcs_to_remove)

    print(f"Arcs removed during preprocessing because they were not utilized: {len(arcs_to_remove)}")
    return arcs_to_remove
