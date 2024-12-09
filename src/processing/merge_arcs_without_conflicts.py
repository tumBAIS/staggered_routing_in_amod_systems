import shapely

from utils.classes import CompleteSolution
from instance_module.instance import Instance


def merge_arcs_on_paths_where_no_conflicts_can_happen(instance: Instance, statusQuo: CompleteSolution) -> None:
    for vehicle, vehiclePath in enumerate(instance.trip_routes):
        listOfListOfArcsToMerge = _get_arcs_which_can_be_merged(vehicle, instance)
        if len(listOfListOfArcsToMerge) > 1:
            for listOfArcsToMerge in listOfListOfArcsToMerge:
                idMergedArc = _append_merged_arc_to_instance(instance, listOfArcsToMerge)
                _merge_entries_vehicle_schedule(vehiclePath, vehicle, statusQuo, listOfArcsToMerge, instance)
                _merge_arcs_in_path(vehiclePath, listOfArcsToMerge, idMergedArc)

    return


def _merge_entries_vehicle_schedule(vehiclePath: list[int], vehicle: int, statusQuo: CompleteSolution,
                                    listOfArcsToMerge: list[int], instance: Instance) -> None:
    idFirstArcToMerge = vehiclePath.index(listOfArcsToMerge[0])
    idLastArcToMerge = vehiclePath.index(listOfArcsToMerge[-1])
    del statusQuo.congested_schedule[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    assert sum(statusQuo.delays_on_arcs[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]) < 1e-6
    del statusQuo.delays_on_arcs[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    del statusQuo.free_flow_schedule[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    del instance.latest_departure_times[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    del instance.earliest_departure_times[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    del instance.max_delay_on_arc[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    del instance.min_delay_on_arc[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]


def _merge_arcs_in_path(vehiclePath: list[int], listOfArcsToMerge: list[int], idMergedArc: int) -> None:
    idFirstArcToMerge = vehiclePath.index(listOfArcsToMerge[0])
    idLastArcToMerge = vehiclePath.index(listOfArcsToMerge[-1])
    del vehiclePath[idFirstArcToMerge: idLastArcToMerge + 1]
    vehiclePath.insert(idFirstArcToMerge, idMergedArc)


def _append_merged_arc_to_instance(instance, listOfArcsToMerge: list[int]) -> int:
    travelTimeNewArc = sum([instance.travel_times_arcs[arc] for arc in listOfArcsToMerge])
    instance.travel_times_arcs.append(travelTimeNewArc)
    instance.capacities_arcs.append(1)
    instance.conflicting_sets.append([])
    return len(instance.travel_times_arcs) - 1


def _get_arcs_which_can_be_merged(vehicle: int, instance: Instance) -> list[list[int]]:
    listOfListOfArcsToMerge: list[list[int]] = []
    listOfArcsToMerge: list[int] = []

    for position, arc in enumerate(instance.trip_routes[vehicle]):
        if vehicle not in instance.conflicting_sets[arc] and arc != 0:
            # vehicle is not in conflicting set
            listOfArcsToMerge.append(arc)
        else:
            # vehicle is in conflicting set or arc is 0
            if len(listOfArcsToMerge) > 1:
                listOfListOfArcsToMerge.append(listOfArcsToMerge)
            listOfArcsToMerge = []

    return listOfListOfArcsToMerge
