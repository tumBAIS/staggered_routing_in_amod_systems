import utils.prints
from input_data import ACTIVATE_ASSERTIONS, TOLERANCE
from problem.epoch_instance import EpochInstance
from problem.solution import Solution
from problem.instance import Instance
from utils.aliases import *
from congestion_model.core import (
    get_congested_schedule,
)
from input_data import SolverParameters
import cpp_module as cpp


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
        for vehicle_epoch_id, vehicle_global_id in enumerate(epoch_instance.trip_original_ids):
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
        epoch_solutions: list[Solution],
        cpp_instance: cpp.cpp_instance,
        instance: Instance) -> Solution:
    """Reconstruct the global solution from epoch solutions."""
    # Reconstruct the global schedule
    utils.prints.print_unified_solution_construction_start()
    reconstructed_start_times = [0.0 for _ in range(cpp_instance.get_number_of_trips())]

    for epoch_id, epoch_instance in enumerate(epoch_instances):
        epoch_start_times = epoch_solutions[epoch_id].start_times
        for epoch_trip_id, start_time in enumerate(epoch_start_times):
            original_trip_id = epoch_instance.get_trip_original_id(epoch_trip_id)
            reconstructed_start_times[original_trip_id] = start_time

    cpp_scheduler = cpp.cpp_scheduler(cpp_instance)
    cpp_solution = cpp_scheduler.construct_solution(reconstructed_start_times)

    # Return the reconstructed solution
    return Solution(
        delays_on_arcs=cpp_solution.get_delays_on_arcs(cpp_instance),
        start_times=cpp_solution.get_start_times(),
        total_delay=cpp_solution.get_total_delay(),
        congested_schedule=cpp_solution.get_schedule(),
        total_travel_time=cpp_solution.get_total_travel_time(),
    )
