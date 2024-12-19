import utils.prints
from input_data import SolverParameters, TOLERANCE
from MIP.model import construct_model, run_model
from problem.instance import Instance
from simplify.map_back import map_simplified_epoch_solution
from solutions.epoch_warm_start import get_epoch_warm_start
from solutions.model_solution import get_epoch_model_solution
from problem.solution import Solution
from typing import Optional
from problem.epoch_instance import EpochInstance
from solutions.status_quo import get_cpp_instance
import cpp_module as cpp
from utils.aliases import *


def print_header_offline_solution() -> None:
    """
    Prints a header for the offline solution computation section.
    """
    print("")
    print("=" * 50)
    print("Computing offline status quo".center(50))
    print("-" * 50)


def get_offline_solution(
        instance: Instance, cpp_instance: cpp.cpp_instance
) -> Solution:
    """
    Computes the offline global solution, which serves as a baseline for comparison.

    """
    print_header_offline_solution()
    cpp_scheduler = cpp.cpp_scheduler(cpp_instance)
    cpp_status_quo = cpp_scheduler.construct_solution(instance.release_times)
    delays_on_arcs = cpp_status_quo.get_delays_on_arcs()
    start_times = cpp_status_quo.get_start_times()
    free_flow_schedule = cpp_instance.get_free_flow_schedule(cpp_status_quo.get_start_times())

    offline_solution = Solution(
        delays_on_arcs=delays_on_arcs,
        free_flow_schedule=free_flow_schedule,
        start_times=start_times,
        total_delay=cpp_status_quo.get_total_delay(),
        congested_schedule=cpp_status_quo.get_schedule(),
        total_travel_time=cpp_status_quo.get_total_travel_time(),
        binaries=None,
    )

    offline_solution.print_congestion_info()

    utils.prints.print_trips_info(instance,
                                  offline_solution.congested_schedule,
                                  offline_solution.free_flow_schedule,
                                  offline_solution.delays_on_arcs)

    return offline_solution


def print_comparison_between_solution_and_status_quo(epoch_status_quo: Solution, epoch_solution: Solution,
                                                     epoch_instance: EpochInstance) -> None:
    """
    Prints information about the computed epoch solution, including delay reduction.
    """
    print("\n" + "=" * 50)
    print(f"Comparison Between Status Quo and Solution Epoch {epoch_instance.epoch_id}".center(50))
    print("=" * 50)

    # Print delays
    time_taken = epoch_instance.clock_end_epoch - epoch_instance.clock_start_epoch
    print(f"Time to complete the epoch: {time_taken:.2f} [s]")
    print(f"Total Delay (Status Quo): {epoch_status_quo.total_delay / 60:.2f} [min]")
    print(f"Total Delay (Computed Solution): {epoch_solution.total_delay / 60:.2f} [min]")

    # Compute and print delay reduction
    if epoch_status_quo.total_delay > TOLERANCE:
        delay_reduction = (
                (epoch_status_quo.total_delay - epoch_solution.total_delay) / epoch_status_quo.total_delay
        )
        print(f"Delay Reduction: {delay_reduction:.2%}")
    else:
        print("Delay Reduction: 0.00%")

    print("=" * 50)


def get_epoch_solution(
        simplified_instance: EpochInstance,
        simplified_status_quo: Solution,
        epoch_instance: EpochInstance,
        epoch_status_quo: Solution,
        solver_params: SolverParameters,
        cpp_epoch_instance: cpp.cpp_instance
) -> tuple[Solution, Optional[OptimizationMeasures]]:
    """
    Computes the solution for a single epoch, mapping it back to the full system.
    """
    # Handle the case where no optimization is required.
    if not simplified_status_quo.congested_schedule:
        return epoch_status_quo, None

    # Prepare the simplified instance for optimization.
    cpp_simplified_epoch_instance = get_cpp_instance(simplified_instance, solver_params)
    cpp_local_search = cpp.LocalSearch(cpp_simplified_epoch_instance)

    # Generate warm start for optimization.
    epoch_warm_start = get_epoch_warm_start(
        simplified_instance,
        simplified_status_quo,
        solver_params,
        cpp_local_search,
        cpp_simplified_epoch_instance
    )

    # Construct and solve the optimization model.
    model = construct_model(
        simplified_instance,
        simplified_status_quo,
        epoch_warm_start,
        solver_params
    )
    optimization_measures = run_model(
        model,
        simplified_instance,
        epoch_warm_start,
        solver_params,
        cpp_local_search
    )

    # Extract the solution from the optimization model.
    model_solution = get_epoch_model_solution(
        model,
        simplified_instance,
        simplified_status_quo,
        epoch_warm_start,
        solver_params,
        cpp_simplified_epoch_instance
    )

    # Map the solution back to the full system.
    epoch_solution = map_simplified_epoch_solution(
        epoch_instance,
        model_solution,
        cpp_epoch_instance
    )

    # Compare and log the results.
    print_comparison_between_solution_and_status_quo(
        epoch_status_quo,
        epoch_solution,
        epoch_instance
    )

    return epoch_solution, optimization_measures
