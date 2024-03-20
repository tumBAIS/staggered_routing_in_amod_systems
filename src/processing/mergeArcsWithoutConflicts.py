import shapely

from utils.classes import CompleteSolution
from instanceModule.instance import Instance


def mergeArcsOnPathsWhereNoConflictsCanHappen(instance: Instance, statusQuo: CompleteSolution) -> None:
    for vehicle, vehiclePath in enumerate(instance.arcBasedShortestPaths):
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
    del statusQuo.congestedSchedule[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    assert sum(statusQuo.delaysOnArcs[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]) < 1e-6
    del statusQuo.delaysOnArcs[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    del statusQuo.freeFlowSchedule[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    del instance.latestDepartureTimes[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    del instance.earliestDepartureTimes[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    del instance.maxDelayOnArc[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]
    del instance.minDelayOnArc[vehicle][idFirstArcToMerge + 1: idLastArcToMerge + 1]


def _mergeArcsInPath(vehiclePath: list[int], listOfArcsToMerge: list[int], idMergedArc: int) -> None:
    idFirstArcToMerge = vehiclePath.index(listOfArcsToMerge[0])
    idLastArcToMerge = vehiclePath.index(listOfArcsToMerge[-1])
    del vehiclePath[idFirstArcToMerge: idLastArcToMerge + 1]
    vehiclePath.insert(idFirstArcToMerge, idMergedArc)


def _appendMergedArcToInstance(instance, listOfArcsToMerge: list[int]) -> int:
    travelTimeNewArc = sum([instance.travelTimesArcsUtilized[arc] for arc in listOfArcsToMerge])
    mergedArcInfo = {"typeOfArc": "merged",
                     "origin": instance.osmInfoArcsUtilized[listOfArcsToMerge[0]]["origin"],
                     "coordinates_origin": instance.osmInfoArcsUtilized[listOfArcsToMerge[0]]["coordinates_origin"],
                     "destination": instance.osmInfoArcsUtilized[listOfArcsToMerge[-1]]["destination"],
                     "coordinates_destination": instance.osmInfoArcsUtilized[listOfArcsToMerge[-1]][
                         "coordinates_destination"],
                     "geometry": shapely.LineString(
                         [instance.osmInfoArcsUtilized[listOfArcsToMerge[0]]["coordinates_origin"],
                          instance.osmInfoArcsUtilized[listOfArcsToMerge[-1]]["coordinates_destination"]]),
                     "length": sum([instance.osmInfoArcsUtilized[arc]["length"] for arc in listOfArcsToMerge])
                     }
    instance.osmInfoArcsUtilized.append(mergedArcInfo)
    instance.travelTimesArcsUtilized.append(travelTimeNewArc)
    instance.nominalCapacitiesArcs.append(1)
    instance.conflictingSets.append([])
    return len(instance.travelTimesArcsUtilized) - 1


def _getArcsWhichCanBeMerged(vehicle: int, instance: Instance) -> list[list[int]]:
    listOfListOfArcsToMerge: list[list[int]] = []
    listOfArcsToMerge: list[int] = []

    for position, arc in enumerate(instance.arcBasedShortestPaths[vehicle]):
        if vehicle not in instance.conflictingSets[arc] and arc != 0:
            # vehicle is not in conflicting set
            listOfArcsToMerge.append(arc)
        else:
            # vehicle is in conflicting set or arc is 0
            if len(listOfArcsToMerge) > 1:
                listOfListOfArcsToMerge.append(listOfArcsToMerge)
            listOfArcsToMerge = []

    return listOfListOfArcsToMerge
