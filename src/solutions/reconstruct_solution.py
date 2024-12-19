import utils.prints
from input_data import ACTIVATE_ASSERTIONS, TOLERANCE
from problem.epoch_instance import EpochInstance
from problem.solution import Solution
from problem.instance import Instance
from utils.aliases import *
from congestion_model.core import (
    PY_get_delays_on_arcs,
    PY_get_free_flow_schedule,
    PY_get_total_delay,
    PY_get_total_travel_time,
    get_congested_schedule,
)
from congestion_model.conflict_binaries import get_conflict_binaries
from conflicting_sets.schedule_utilities import add_conflicting_sets_to_instance
from input_data import SolverParameters


def _merge_schedules(existing_schedule: list[float], new_schedule: list[float]) -> list[float]:
    """Merge two schedules by aligning overlapping portions."""
    if not new_schedule:
        return existing_schedule

    for idx, time in enumerate(existing_schedule):
        if abs(time - new_schedule[0]) < TOLERANCE:
            # Found a common element
            return existing_schedule[:idx] + new_schedule

    # No overlap, append the new schedule
    return existing_schedule + new_schedule


def _reconstruct_schedule(
        epoch_instances: list[EpochInstance],
        epoch_status_quo_list: list[Solution],
        global_instance: Instance,
) -> Schedules:
    """Reconstruct the global schedule from epoch solutions."""
    reconstructed_schedule = [[] for _ in range(len(global_instance.trip_routes))]

    for epoch_id, epoch_instance in enumerate(epoch_instances):
        for vehicle_epoch_id, vehicle_global_id in enumerate(epoch_instance.vehicles_original_ids):
            last_position = epoch_instance.last_position_for_reconstruction[vehicle_epoch_id]
            new_schedule = epoch_status_quo_list[epoch_id].congested_schedule[vehicle_epoch_id][:last_position]
            reconstructed_schedule[vehicle_global_id] = _merge_schedules(reconstructed_schedule[vehicle_global_id],
                                                                         new_schedule)

    return reconstructed_schedule


def _assert_congested_schedule_is_correct(global_instance: Instance, reconstructed_schedule: Schedules,
                                          solver_params: SolverParameters) -> None:
    """Ensure the reconstructed schedule matches the expected congested schedule."""
    if ACTIVATE_ASSERTIONS:
        release_times = [schedule[0] for schedule in reconstructed_schedule]
        cpp_schedule = get_congested_schedule(global_instance, release_times, solver_params)

        for vehicle, schedule in enumerate(reconstructed_schedule):
            if not all(abs(reconstructed - cpp) < TOLERANCE for reconstructed, cpp in
                       zip(schedule, cpp_schedule[vehicle])):
                _print_not_matching_schedules(reconstructed_schedule, cpp_schedule, vehicle)
                raise AssertionError(f"Schedules do not match for vehicle {vehicle}")


def _print_not_matching_schedules(
        reconstructed_schedule: Schedules,
        cpp_schedule: Schedules,
        vehicle: int,
) -> None:
    """Print details for mismatched schedules."""
    print(f"Schedules for vehicle {vehicle} do not match:")
    print(f"Reconstructed schedule: {reconstructed_schedule[vehicle]}")
    print(f"CPP schedule: {cpp_schedule[vehicle]}")
    mismatches = [
        idx for idx, (reconstructed, cpp) in enumerate(zip(reconstructed_schedule[vehicle], cpp_schedule[vehicle]))
        if abs(reconstructed - cpp) > TOLERANCE
    ]
    print(f"Mismatched positions: {mismatches}")


def reconstruct_solution(
        epoch_instances: list[EpochInstance],
        epoch_status_quo_list: list[Solution],
        global_instance: Instance,
        solver_params: SolverParameters
) -> Solution:
    """Reconstruct the global solution from epoch solutions."""
    # Reconstruct the global schedule
    utils.prints.print_unified_solution_construction_start()
    congested_schedule = _reconstruct_schedule(epoch_instances, epoch_status_quo_list, global_instance)
    _assert_congested_schedule_is_correct(global_instance, congested_schedule, solver_params)

    # Compute delays, free flow schedule, and other metrics
    delays_on_arcs = PY_get_delays_on_arcs(global_instance, congested_schedule)
    free_flow_schedule = PY_get_free_flow_schedule(global_instance, congested_schedule)
    release_times = [schedule[0] for schedule in congested_schedule]
    total_delay = PY_get_total_delay(free_flow_schedule, congested_schedule)
    total_travel_time = PY_get_total_travel_time(congested_schedule)

    # Update conflicting sets and binaries
    add_conflicting_sets_to_instance(global_instance, free_flow_schedule)
    binaries = get_conflict_binaries(global_instance.conflicting_sets, global_instance.trip_routes, congested_schedule)

    # Return the reconstructed solution
    return Solution(
        delays_on_arcs=delays_on_arcs,
        free_flow_schedule=free_flow_schedule,
        release_times=release_times,
        total_delay=total_delay,
        congested_schedule=congested_schedule,
        total_travel_time=total_travel_time,
        binaries=binaries,
    )
