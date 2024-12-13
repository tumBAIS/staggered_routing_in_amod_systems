from utils.classes import Solution
from instance_module.epoch_instance import EpochInstance


def merge_arcs_on_paths_where_no_conflicts_can_happen(instance: EpochInstance, status_quo: Solution) -> None:
    """
    Merge arcs in vehicle paths where no conflicts can occur.
    """
    for trip, route in enumerate(instance.trip_routes):
        arc_sequences_to_merge = get_arc_sequences_to_merge(trip, instance)
        if arc_sequences_to_merge:
            for arc_sequence_to_merge in arc_sequences_to_merge:
                # Update schedules and instance timing information
                start_idx = route.index(arc_sequence_to_merge[0])
                end_idx = route.index(arc_sequence_to_merge[-1])
                instance.merge_arc_sequence_in_trip_route(arc_sequence_to_merge, trip, start_idx, end_idx)
                status_quo.remove_trip_arcs_between_indices(trip, start_idx, end_idx)


def get_arc_sequences_to_merge(vehicle: int, instance: EpochInstance) -> list[list[int]]:
    """
    Identify groups of arcs in a vehicle's path that can be merged.
    """
    arcs_to_merge_groups = []
    current_group = []

    for arc in instance.trip_routes[vehicle]:
        if arc != 0 and vehicle not in instance.conflicting_sets[arc]:
            current_group.append(arc)
        else:
            if len(current_group) > 1:
                arcs_to_merge_groups.append(current_group)
            current_group = []

    # Add any remaining group at the end of the loop
    if len(current_group) > 1:
        arcs_to_merge_groups.append(current_group)

    return arcs_to_merge_groups
