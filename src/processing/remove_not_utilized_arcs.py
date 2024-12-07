from input_data import ACTIVATE_ASSERTIONS
from instance_module.instance import Instance


def _get_vehicles_utilizing_arcs(instance: Instance) -> list[list[int]]:
    vehiclesUtilizingArcs = [[] for _ in instance.travel_times_arcs]
    for vehicle, path in enumerate(instance.trip_routes):
        for arc in path:
            vehiclesUtilizingArcs[arc].append(vehicle)

    return vehiclesUtilizingArcs


def _update_used_arcs_ids(instance: Instance, arcsToRemove: list[int]) -> None:
    if not arcsToRemove:
        return
    instance.trip_routes = [[arc - len([arcRemoved for arcRemoved in arcsToRemove if arcRemoved < arc]) for
                             arc in path] for path in instance.trip_routes]
    return


def _assert_arc_is_not_utilized(conflictingSet: list[int], paths: list[list[int]]):
    if ACTIVATE_ASSERTIONS and conflictingSet:
        print(f"Conflicting set: {conflictingSet}")
        for vehicle in conflictingSet:
            print(f"Vehicle {vehicle}: {paths[vehicle]}")
        raise RuntimeError("deleted arc with conflicting set!")


def _remove_arcs(instance: Instance, arcsToRemove: list[int]) -> None:
    if not arcsToRemove:
        return
    assert arcsToRemove == sorted(arcsToRemove), "arcs to remove are not sored!"
    for arc in reversed(arcsToRemove):
        instance.travel_times_arcs.pop(arc)
        instance.osm_info_arcs_utilized.pop(arc)
        instance.capacities_arcs.pop(arc)
        _assert_arc_is_not_utilized(instance.conflicting_sets[arc], instance.trip_routes)
        instance.conflicting_sets.pop(arc)
    return


def remove_not_utilized_arcs(instance: Instance) -> None:
    """due to preprocessing some arcs are not utilized: we remove them and update consistently travel times,
    capacities and conflicting sets after preprocessing """
    vehiclesUtilizingArcs = _get_vehicles_utilizing_arcs(instance)
    arcsToRemove = [arc for arc, vehicles in enumerate(vehiclesUtilizingArcs) if not vehicles]

    _remove_arcs(instance, arcsToRemove)
    _update_used_arcs_ids(instance, arcsToRemove)
    print(f"Arcs removed during preprocessing because not utilized: {len(arcsToRemove)}")
    return
