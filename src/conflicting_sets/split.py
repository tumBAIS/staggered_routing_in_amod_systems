from instanceModule.instance import Instance


def _appendArcCopyToInstance(instance: Instance, arcToCopy: int, conflictingSet: list[int]) -> None:
    arcTravelTime = instance.travel_times_arcs[arcToCopy]
    arcNominalCapacity = instance.capacities_arcs[arcToCopy]
    osmInfo = instance.osmInfoArcsUtilized[arcToCopy]
    instance.travel_times_arcs.append(arcTravelTime)
    instance.osmInfoArcsUtilized.append(osmInfo)
    instance.capacities_arcs.append(arcNominalCapacity)
    instance.conflictingSets.append(conflictingSet)
    instance.undividedConflictingSets.append([conflictingSet])
    return


def _updatePathVehiclesOfConflictingSet(instance: Instance, arc: int) -> None:
    lastArcCreated = len(instance.travel_times_arcs) - 1
    for vehicle in instance.conflictingSets[lastArcCreated]:
        "substitute old arc with new arc"
        indexOldArcInPath = instance.trip_routes[vehicle].index(arc)
        instance.trip_routes[vehicle][indexOldArcInPath] = lastArcCreated
    return


def splitConflictingSets(instance: Instance) -> None:
    "create an arc for each conflicting set,\
    and updates the instanceModule attribute PotentialConflictingSetsAfterPreProcessing"
    instance.conflictingSets = [[] for _ in range(len(instance.travel_times_arcs))]
    for arc, conflictingSetsOnArc in enumerate(instance.undividedConflictingSets):
        if not conflictingSetsOnArc:
            instance.conflictingSets[arc] = []  # empty conflicting set
            continue
        for conflictingSetId, conflictingSet in enumerate(conflictingSetsOnArc):
            if conflictingSetId == 0:
                "assign first conflicting set to original arc"
                instance.conflictingSets[arc] = conflictingSet
                instance.undividedConflictingSets[arc] = [conflictingSet]
                continue
            _appendArcCopyToInstance(instance, arc, conflictingSet)
            _updatePathVehiclesOfConflictingSet(instance, arc)

    return
