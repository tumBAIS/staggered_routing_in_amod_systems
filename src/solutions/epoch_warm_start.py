import datetime
from input_data import SolverParameters
from utils.aliases import *
from input_data import TOLERANCE
from instance_module.epoch_instance import EpochInstance
from utils.classes import Solution
from congestion_model.core import (
    get_free_flow_schedule,
    get_total_travel_time,
    get_delays_on_arcs,
    get_staggering_applicable,
)
from congestion_model.conflict_binaries import get_conflict_binaries
import cpp_module as cpp


def _compute_remaining_time(instance: EpochInstance, solver_params: SolverParameters) -> float:
    """
    Calculates the remaining time for optimization based on algorithm and epoch limits.
    """
    algorithm_time_remaining = solver_params.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - instance.start_solution_time
    )
    epoch_time_remaining = solver_params.epoch_time_limit - (
            datetime.datetime.now().timestamp() - instance.clock_start_epoch
    )
    return max(0.0, min(algorithm_time_remaining, epoch_time_remaining))


def _is_time_left_for_optimization(instance: EpochInstance, solver_params: SolverParameters) -> bool:
    """
    Checks whether there is sufficient time left for optimization.
    """
    return _compute_remaining_time(instance, solver_params) > TOLERANCE


def get_epoch_warm_start(
        epoch_instance: EpochInstance, epoch_status_quo: Solution, solver_params: SolverParameters,
        cpp_local_search: cpp.LocalSearch
) -> Solution:
    """
    Computes the warm start solution for the given epoch.

    If the solver parameters allow improving the warm start and there is time left for optimization,
    performs a local search. Otherwise, returns the status quo.
    """
    print("\n" + "=" * 50)
    print(f"Computing Warm Start Epoch {epoch_instance.epoch_id}".center(50))
    print("=" * 50)

    # Decide whether to improve warm start or use status quo
    if solver_params.improve_warm_start and _is_time_left_for_optimization(epoch_instance, solver_params):
        print("Improving warm start using local search...")

        time_remaining = _compute_remaining_time(epoch_instance, solver_params)
        cpp_solution = cpp_local_search.run(epoch_status_quo.release_times, epoch_status_quo.staggering_applicable,
                                            epoch_status_quo.staggering_applied)
        congested_schedule = cpp_solution.get_schedule()
        print("Local search completed.")
    else:
        if not _is_time_left_for_optimization(epoch_instance, solver_params):
            print("No remaining time for optimization - ", end="")
        print("Using status quo as warm start.")
        print("=" * 50)
        return epoch_status_quo

    # Compute necessary metrics for the warm start solution
    release_times = [schedule[0] for schedule in congested_schedule]
    free_flow_schedule = get_free_flow_schedule(epoch_instance, congested_schedule)
    staggering_applied = [
        congested_schedule[vehicle][0] - release_time
        for vehicle, release_time in enumerate(epoch_status_quo.release_times)
    ]
    staggering_applicable = get_staggering_applicable(epoch_instance, staggering_applied)
    delays_on_arcs = get_delays_on_arcs(epoch_instance, congested_schedule)
    total_delay = sum(sum(delays) for delays in delays_on_arcs)
    binaries = get_conflict_binaries(epoch_instance.conflicting_sets, epoch_instance.trip_routes, congested_schedule)
    total_travel_time = get_total_travel_time(congested_schedule)

    # Construct the warm start solution
    warm_start = Solution(
        total_delay=total_delay,
        congested_schedule=congested_schedule,
        delays_on_arcs=delays_on_arcs,
        release_times=release_times,
        staggering_applicable=staggering_applicable,
        binaries=binaries,
        free_flow_schedule=free_flow_schedule,
        staggering_applied=staggering_applied,
        total_travel_time=total_travel_time,
        vehicles_utilizing_arcs=epoch_status_quo.vehicles_utilizing_arcs,
    )

    # Print final metrics
    delay_percentage = total_delay / total_travel_time * 100
    print(f"Warm start solution computed successfully.")
    print(f" - Total Delay: {total_delay:.2f}")
    print(f" - Delay as % of Travel Time: {delay_percentage:.2f}%")
    print("=" * 50)

    return warm_start
