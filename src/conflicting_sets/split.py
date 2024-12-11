from instance_module.instance import Instance


def append_arc_copy_to_instance(instance: Instance, arc_to_copy: int, conflicting_set: list[int]) -> None:
    """
    Append a copy of an arc to the instance with its travel time, capacity, and conflicting set.
    """
    arc_travel_time = instance.travel_times_arcs[arc_to_copy]
    arc_nominal_capacity = instance.capacities_arcs[arc_to_copy]
    instance.travel_times_arcs.append(arc_travel_time)
    instance.capacities_arcs.append(arc_nominal_capacity)
    instance.conflicting_sets.append(conflicting_set)
    instance.undivided_conflicting_sets.append([conflicting_set])


def update_vehicle_paths_in_conflicting_set(instance: Instance, arc: int) -> None:
    """
    Update the paths of vehicles in a conflicting set by replacing the old arc with the newly created arc.
    """
    last_arc_created = len(instance.travel_times_arcs) - 1
    for vehicle in instance.conflicting_sets[last_arc_created]:
        # Replace the old arc with the new arc in the vehicle's path
        old_arc_index = instance.trip_routes[vehicle].index(arc)
        instance.trip_routes[vehicle][old_arc_index] = last_arc_created


def split_conflicting_sets(instance: Instance) -> None:
    """
    Create an arc for each conflicting set and update the instance's conflicting set attributes.
    """
    instance.conflicting_sets = [[] for _ in range(len(instance.travel_times_arcs))]

    for arc, conflicting_sets_on_arc in enumerate(instance.undivided_conflicting_sets):
        if not conflicting_sets_on_arc:
            instance.conflicting_sets[arc] = []  # No conflicting sets for this arc
            continue

        for conflicting_set_id, conflicting_set in enumerate(conflicting_sets_on_arc):
            if conflicting_set_id == 0:
                # Assign the first conflicting set to the original arc
                instance.conflicting_sets[arc] = conflicting_set
                instance.undivided_conflicting_sets[arc] = [conflicting_set]
            else:
                append_arc_copy_to_instance(instance, arc, conflicting_set)
                update_vehicle_paths_in_conflicting_set(instance, arc)
