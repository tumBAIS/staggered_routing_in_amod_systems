import datetime
from input_data import SolverParameters
from input_data import TOLERANCE
from problem.epoch_instance import EpochInstance
from problem.solution import Solution
from congestion_model.core import (
    PY_get_delays_on_arcs)
from congestion_model.conflict_binaries import get_conflict_binaries
import cpp_module as cpp


def _compute_remaining_time(instance: EpochInstance, solver_params: SolverParameters) -> float:
    """
    Calculates the remaining time for optimization based on algorithm and epoch limits.
    """
    algorithm_time_remaining = solver_params.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - solver_params.start_algorithm_clock
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
        cpp_local_search: cpp.LocalSearch, cpp_instance: cpp.cpp_instance
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

        cpp_solution = cpp_local_search.run(epoch_status_quo.start_times)
        print("Local search completed.")
    else:
        if not _is_time_left_for_optimization(epoch_instance, solver_params):
            print("No remaining time for optimization - ", end="")
        print("Using status quo as warm start.")
        print("=" * 50)
        return epoch_status_quo

    # Compute necessary metrics for the warm start solution
    congested_schedule = cpp_solution.get_schedule()
    total_delay = cpp_solution.get_total_delay()
    total_travel_time = cpp_solution.get_total_travel_time()
    start_times = cpp_solution.get_start_times()
    delays_on_arcs = cpp_solution.get_delays_on_arcs()
    binaries = get_conflict_binaries(epoch_instance.conflicting_sets, epoch_instance.trip_routes, congested_schedule)

    # Construct the warm start solution
    warm_start = Solution(
        total_delay=total_delay,
        congested_schedule=congested_schedule,
        delays_on_arcs=delays_on_arcs,
        start_times=start_times,
        binaries=binaries,
        free_flow_schedule=cpp_instance.get_free_flow_schedule(start_times),
        total_travel_time=total_travel_time,
    )

    # Print final metrics
    delay_percentage = total_delay / total_travel_time * 100
    print(f"Warm start solution computed successfully.")
    print(f" - Total Delay: {total_delay:.2f}")
    print(f" - Delay as % of Travel Time: {delay_percentage:.2f}%")
    print("=" * 50)

    return warm_start
