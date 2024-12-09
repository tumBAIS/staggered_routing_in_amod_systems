from instance_module.instance import Instance


def append_arc_copy_to_instance(instance: Instance, arcToCopy: int, conflictingSet: list[int]) -> None:
    arcTravelTime = instance.travel_times_arcs[arcToCopy]
    arcNominalCapacity = instance.capacities_arcs[arcToCopy]
    instance.travel_times_arcs.append(arcTravelTime)
    instance.capacities_arcs.append(arcNominalCapacity)
    instance.conflicting_sets.append(conflictingSet)
    instance.undivided_conflicting_sets.append([conflictingSet])
    return


def update_path_vehicles_of_conflicting_set(instance: Instance, arc: int) -> None:
    lastArcCreated = len(instance.travel_times_arcs) - 1
    for vehicle in instance.conflicting_sets[lastArcCreated]:
        "substitute old arc with new arc"
        indexOldArcInPath = instance.trip_routes[vehicle].index(arc)
        instance.trip_routes[vehicle][indexOldArcInPath] = lastArcCreated
    return


def split_conflicting_sets(instance: Instance) -> None:
    """create an arc for each conflicting set and updates the instanceModule attribute PotentialConflictingSetsAfterPreProcessing"""
    instance.conflicting_sets = [[] for _ in range(len(instance.travel_times_arcs))]
    for arc, conflictingSetsOnArc in enumerate(instance.undivided_conflicting_sets):
        if not conflictingSetsOnArc:
            instance.conflicting_sets[arc] = []  # empty conflicting set
            continue
        for conflictingSetId, conflictingSet in enumerate(conflictingSetsOnArc):
            if conflictingSetId == 0:
                # "assign first conflicting set to original arc"
                instance.conflicting_sets[arc] = conflictingSet
                instance.undivided_conflicting_sets[arc] = [conflictingSet]
                continue
            append_arc_copy_to_instance(instance, arc, conflictingSet)
            update_path_vehicles_of_conflicting_set(instance, arc)

    return
