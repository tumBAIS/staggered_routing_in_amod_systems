import MIP.support
import utils.prints
from input_data import SolverParameters, TOLERANCE
from MIP.model import construct_model, run_model
from solutions.status_quo import compute_solution_metrics
from congestion_model.core import get_total_travel_time
from instance_module.instance import Instance
from solutions.map_simplified_epoch_solution import map_simplified_epoch_solution
from solutions.epoch_warm_start import get_epoch_warm_start
from solutions.model_solution import get_epoch_model_solution
from utils.classes import Solution
from typing import Optional
from instance_module.epoch_instance import EpochInstance


def print_header_offline_solution() -> None:
    """
    Prints a header for the offline solution computation section.
    """
    print("")
    print("=" * 50)
    print("Computing offline status quo".center(50))
    print("-" * 50)


def get_offline_solution(
        instance: Instance, release_times: list[float], solver_params: SolverParameters
) -> Solution:
    """
    Computes the offline global solution, which serves as a baseline for comparison.

    Args:
        instance: The problem instance.
        release_times: List of vehicle release times.
        solver_params: Solver parameters.

    Returns:
        Solution: The computed offline solution.
    """
    print_header_offline_solution()

    solution_metrics = compute_solution_metrics(instance, release_times, solver_params)

    offline_solution = Solution(
        delays_on_arcs=solution_metrics.delays_on_arcs,
        free_flow_schedule=solution_metrics.free_flow_schedule,
        release_times=solution_metrics.release_times,
        staggering_applicable=instance.max_staggering_applicable[:],
        total_delay=solution_metrics.total_delay,
        congested_schedule=solution_metrics.congested_schedule,
        staggering_applied=[0.0] * len(solution_metrics.congested_schedule),
        total_travel_time=get_total_travel_time(solution_metrics.congested_schedule),
        binaries=None,
    )

    offline_solution.print_congestion_info()

    utils.prints.print_trips_info(instance,
                                  offline_solution.congested_schedule,
                                  offline_solution.free_flow_schedule,
                                  offline_solution.delays_on_arcs)

    return offline_solution


def print_info_epoch_solution(epoch_status_quo: Solution, epoch_solution: Solution) -> None:
    """
    Prints information about the computed epoch solution, including delay reduction.

    Args:
        epoch_status_quo: The current status quo solution for the epoch.
        epoch_solution: The computed solution for the epoch.
    """
    print("#" * 20)
    print("INFO EPOCH SOLUTION")
    print("#" * 20)

    print(f"Total delay epoch status quo: {epoch_status_quo.total_delay / 60:.2f} [min]")
    print(f"Total delay epoch model solution: {epoch_solution.total_delay / 60:.2f} [min]")

    if epoch_status_quo.total_delay > TOLERANCE:
        delay_reduction = (
                (epoch_status_quo.total_delay - epoch_solution.total_delay) / epoch_status_quo.total_delay
        )
        print(f"Total delay epoch reduction: {delay_reduction:.2%}")
    else:
        print("Total delay epoch reduction: 0.00%")


def get_epoch_solution(
        simplified_instance: EpochInstance,
        simplified_status_quo: Solution,
        epoch_instance: EpochInstance,
        epoch_status_quo: Solution,
        solver_params: SolverParameters,
) -> tuple[Solution, Optional[MIP.support.OptimizationMeasures]]:
    """
    Computes the solution for a single epoch, mapping it back to the full system.

    Args:
        simplified_instance: Simplified problem instance.
        simplified_status_quo: Simplified status quo solution.
        epoch_instance: Original problem instance for the epoch.
        epoch_status_quo: Status quo solution for the epoch.
        solver_params: Solver parameters.

    Returns:
        tuple: EpochSolution and corresponding optimization measures.
    """
    if len(simplified_status_quo.congested_schedule) > 0:
        epoch_warm_start = get_epoch_warm_start(simplified_instance, simplified_status_quo, solver_params)
        model = construct_model(simplified_instance, simplified_status_quo, epoch_warm_start, solver_params)
        optimization_measures = run_model(
            model, simplified_instance, epoch_warm_start, simplified_status_quo, solver_params
        )
        model_solution = get_epoch_model_solution(
            model, simplified_instance, simplified_status_quo, epoch_warm_start, solver_params
        )

        # Map the solution back to the full system
        epoch_solution = map_simplified_epoch_solution(epoch_instance, model_solution, solver_params)
        print_info_epoch_solution(epoch_status_quo, epoch_solution)

        return epoch_solution, optimization_measures
    else:
        return epoch_status_quo, None
