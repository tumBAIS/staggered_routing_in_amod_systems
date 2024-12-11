import shapely
from utils.classes import CompleteSolution
from instance_module.instance import Instance


def merge_arcs_on_paths_where_no_conflicts_can_happen(instance: Instance, status_quo: CompleteSolution) -> None:
    """
    Merge arcs in vehicle paths where no conflicts can occur.
    """
    for vehicle, vehicle_path in enumerate(instance.trip_routes):
        arcs_to_merge_groups = _get_arcs_eligible_for_merging(vehicle, instance)
        if arcs_to_merge_groups:
            for arcs_to_merge in arcs_to_merge_groups:
                merged_arc_id = _add_merged_arc_to_instance(instance, arcs_to_merge)
                _update_vehicle_schedule(vehicle_path, vehicle, status_quo, arcs_to_merge, instance)
                _replace_arcs_with_merged_arc(vehicle_path, arcs_to_merge, merged_arc_id)


def _get_arcs_eligible_for_merging(vehicle: int, instance: Instance) -> list[list[int]]:
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


def _add_merged_arc_to_instance(instance: Instance, arcs_to_merge: list[int]) -> int:
    """
    Add a new merged arc to the instance and return its ID.
    """
    merged_travel_time = sum(instance.travel_times_arcs[arc] for arc in arcs_to_merge)
    instance.travel_times_arcs.append(merged_travel_time)
    instance.capacities_arcs.append(1)
    instance.conflicting_sets.append([])
    return len(instance.travel_times_arcs) - 1


def _update_vehicle_schedule(
        vehicle_path: list[int], vehicle: int, status_quo: CompleteSolution,
        arcs_to_merge: list[int], instance: Instance
) -> None:
    """
    Update the vehicle's schedule and associated data after merging arcs.
    """
    start_idx = vehicle_path.index(arcs_to_merge[0])
    end_idx = vehicle_path.index(arcs_to_merge[-1])

    # Update schedules and instance timing information
    del status_quo.congested_schedule[vehicle][start_idx + 1:end_idx + 1]
    del status_quo.free_flow_schedule[vehicle][start_idx + 1:end_idx + 1]
    del status_quo.delays_on_arcs[vehicle][start_idx + 1:end_idx + 1]

    del instance.latest_departure_times[vehicle][start_idx + 1:end_idx + 1]
    del instance.earliest_departure_times[vehicle][start_idx + 1:end_idx + 1]
    del instance.max_delay_on_arc[vehicle][start_idx + 1:end_idx + 1]
    del instance.min_delay_on_arc[vehicle][start_idx + 1:end_idx + 1]


def _replace_arcs_with_merged_arc(vehicle_path: list[int], arcs_to_merge: list[int], merged_arc_id: int) -> None:
    """
    Replace the specified arcs in the vehicle's path with a single merged arc.
    """
    start_idx = vehicle_path.index(arcs_to_merge[0])
    end_idx = vehicle_path.index(arcs_to_merge[-1])

    del vehicle_path[start_idx:end_idx + 1]
    vehicle_path.insert(start_idx, merged_arc_id)
