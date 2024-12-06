import shapely

from utils.classes import CompleteSolution
from instanceModule.instance import Instance


def mergeArcsOnPathsWhereNoConflictsCanHappen(instance: Instance, statusQuo: CompleteSolution) -> None:
    for vehicle, vehiclePath in enumerate(instance.trip_routes):
        listOfListOfArcsToMerge = _getArcsWhichCanBeMerged(vehicle, instance)
        if len(listOfListOfArcsToMerge) > 1:
            for listOfArcsToMerge in listOfListOfArcsToMerge:
                idMergedArc = _appendMergedArcToInstance(instance, listOfArcsToMerge)
                _mergeEntriesVehicleSchedule(vehiclePath, vehicle, statusQuo, listOfArcsToMerge, instance)
                _mergeArcsInPath(vehiclePath, listOfArcsToMerge, idMergedArc)

    return


def _mergeEntriesVehicleSchedule(vehiclePath: list[int], vehicle: int, statusQuo: CompleteSolution,
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


def _mergeArcsInPath(vehiclePath: list[int], listOfArcsToMerge: list[int], idMergedArc: int) -> None:
    idFirstArcToMerge = vehiclePath.index(listOfArcsToMerge[0])
    idLastArcToMerge = vehiclePath.index(listOfArcsToMerge[-1])
    del vehiclePath[idFirstArcToMerge: idLastArcToMerge + 1]
    vehiclePath.insert(idFirstArcToMerge, idMergedArc)


def _appendMergedArcToInstance(instance, listOfArcsToMerge: list[int]) -> int:
    travelTimeNewArc = sum([instance.travel_times_arcs[arc] for arc in listOfArcsToMerge])
    mergedArcInfo = {"typeOfArc": "merged",
                     "origin": instance.osm_info_arcs_utilized[listOfArcsToMerge[0]]["origin"],
                     "coordinates_origin": instance.osm_info_arcs_utilized[listOfArcsToMerge[0]]["coordinates_origin"],
                     "destination": instance.osm_info_arcs_utilized[listOfArcsToMerge[-1]]["destination"],
                     "coordinates_destination": instance.osm_info_arcs_utilized[listOfArcsToMerge[-1]][
                         "coordinates_destination"],
                     "geometry": shapely.LineString(
                         [instance.osm_info_arcs_utilized[listOfArcsToMerge[0]]["coordinates_origin"],
                          instance.osm_info_arcs_utilized[listOfArcsToMerge[-1]]["coordinates_destination"]]),
                     "length": sum([instance.osm_info_arcs_utilized[arc]["length"] for arc in listOfArcsToMerge])
                     }
    instance.osm_info_arcs_utilized.append(mergedArcInfo)
    instance.travel_times_arcs.append(travelTimeNewArc)
    instance.capacities_arcs.append(1)
    instance.conflicting_sets.append([])
    return len(instance.travel_times_arcs) - 1


def _getArcsWhichCanBeMerged(vehicle: int, instance: Instance) -> list[list[int]]:
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
