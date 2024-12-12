from input_data import ACTIVATE_ASSERTIONS
from instance_module.epoch_instance import EpochInstance
from utils.classes import EpochSolution, CompleteSolution
from instance_module.instance import Instance
from utils.aliases import *
from congestion_model.core import (
    get_delays_on_arcs,
    get_free_flow_schedule,
    get_staggering_applicable,
    get_total_delay,
    get_total_travel_time,
    get_congested_schedule,
)
from congestion_model.conflict_binaries import get_conflict_binaries
from conflicting_sets.schedule_utilities import add_conflicting_sets_to_instance


def _merge_schedules(existing_schedule: list[float], new_schedule: list[float]) -> list[float]:
    """Merge two schedules by aligning overlapping portions."""
    if not new_schedule:
        return existing_schedule

    for idx, time in enumerate(existing_schedule):
        if abs(time - new_schedule[0]) < 1e-1:
            # Found a common element
            return existing_schedule[:idx] + new_schedule

    # No overlap, append the new schedule
    return existing_schedule + new_schedule


def _reconstruct_schedule(
        epoch_instances: list[EpochInstance],
        epoch_status_quo_list: list[EpochSolution],
        global_instance: Instance,
) -> TripSchedules:
    """Reconstruct the global schedule from epoch solutions."""
    reconstructed_schedule = [[] for _ in range(len(global_instance.trip_routes))]

    for epoch_id, epoch_instance in enumerate(epoch_instances):
        for vehicle_epoch_id, vehicle_global_id in enumerate(epoch_instance.vehicles_original_ids):
            last_position = epoch_instance.last_position_for_reconstruction[vehicle_epoch_id]
            new_schedule = epoch_status_quo_list[epoch_id].congested_schedule[vehicle_epoch_id][:last_position]
            reconstructed_schedule[vehicle_global_id] = _merge_schedules(reconstructed_schedule[vehicle_global_id],
                                                                         new_schedule)

    return reconstructed_schedule


def _assert_congested_schedule_is_correct(global_instance: Instance, reconstructed_schedule: TripSchedules) -> None:
    """Ensure the reconstructed schedule matches the expected congested schedule."""
    if ACTIVATE_ASSERTIONS:
        release_times = [schedule[0] for schedule in reconstructed_schedule]
        cpp_schedule = get_congested_schedule(global_instance, release_times)

        for vehicle, schedule in enumerate(reconstructed_schedule):
            if not all(abs(reconstructed - cpp) < 1e-4 for reconstructed, cpp in zip(schedule, cpp_schedule[vehicle])):
                _print_not_matching_schedules(global_instance, reconstructed_schedule, cpp_schedule, vehicle)
                raise AssertionError(f"Schedules do not match for vehicle {vehicle}")


def _print_not_matching_schedules(
        global_instance: Instance,
        reconstructed_schedule: TripSchedules,
        cpp_schedule: TripSchedules,
        vehicle: int,
) -> None:
    """Print details for mismatched schedules."""
    print(f"Schedules for vehicle {vehicle} do not match:")
    print(f"Reconstructed schedule: {reconstructed_schedule[vehicle]}")
    print(f"CPP schedule: {cpp_schedule[vehicle]}")
    mismatches = [
        idx for idx, (reconstructed, cpp) in enumerate(zip(reconstructed_schedule[vehicle], cpp_schedule[vehicle]))
        if abs(reconstructed - cpp) > 1e-4
    ]
    print(f"Mismatched positions: {mismatches}")


def reconstruct_solution(
        epoch_instances: list[EpochInstance],
        epoch_status_quo_list: list[EpochSolution],
        global_instance: Instance
) -> CompleteSolution:
    """Reconstruct the global solution from epoch solutions."""
    # Reconstruct the global schedule
    congested_schedule = _reconstruct_schedule(epoch_instances, epoch_status_quo_list, global_instance)
    _assert_congested_schedule_is_correct(global_instance, congested_schedule)

    # Compute delays, free flow schedule, and other metrics
    delays_on_arcs = get_delays_on_arcs(global_instance, congested_schedule)
    free_flow_schedule = get_free_flow_schedule(global_instance, congested_schedule)
    release_times = [schedule[0] for schedule in congested_schedule]
    staggering_applied = [schedule[0] - global_release for schedule, global_release in
                          zip(congested_schedule, global_instance.release_times)]
    staggering_applicable = get_staggering_applicable(global_instance, staggering_applied)
    total_delay = get_total_delay(free_flow_schedule, congested_schedule)
    total_travel_time = get_total_travel_time(congested_schedule)

    # Update conflicting sets and binaries
    add_conflicting_sets_to_instance(global_instance, free_flow_schedule)
    binaries = get_conflict_binaries(global_instance.conflicting_sets, global_instance.trip_routes, congested_schedule)

    # Return the reconstructed solution
    return CompleteSolution(
        delays_on_arcs=delays_on_arcs,
        free_flow_schedule=free_flow_schedule,
        release_times=release_times,
        staggering_applicable=staggering_applicable,
        total_delay=total_delay,
        congested_schedule=congested_schedule,
        staggering_applied=staggering_applied,
        total_travel_time=total_travel_time,
        binaries=binaries,
    )
