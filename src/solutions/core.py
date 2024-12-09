from input_data import SolverParameters
from MIP.model import construct_model, run_model
from solutions.status_quo import compute_solution_metrics, print_info_status_quo_metrics
from conflicting_sets.schedule_utilities import add_conflicting_sets_to_instance
from congestion_model.core import get_total_travel_time
from instance_module.instance import Instance
from solutions.map_simplified_epoch_solution import map_simplified_epoch_solution
from solutions.epoch_warm_start import get_epoch_warm_start
from solutions.model_solution import get_epoch_model_solution
from utils.classes import EpochSolution, CompleteSolution


def print_header_offline_solution():
    """Prints header for offline solution computation."""
    print("#" * 20)
    print("COMPUTING OFFLINE SOLUTION")
    print("#" * 20)


def get_offline_solution(instance: Instance, release_times: list[float],
                         solver_params: SolverParameters) -> CompleteSolution:
    """Compute the global status quo to compare solutions against."""
    print_header_offline_solution()
    solution_metrics = compute_solution_metrics(instance, release_times, solver_params)
    print_info_status_quo_metrics(solution_metrics)
    add_conflicting_sets_to_instance(instance, solution_metrics.free_flow_schedule)
    staggering_applied_in_epoch = [0.0] * len(solution_metrics.congested_schedule)

    return CompleteSolution(
        delays_on_arcs=solution_metrics.delays_on_arcs,
        free_flow_schedule=solution_metrics.free_flow_schedule,
        release_times=solution_metrics.release_times,
        staggering_applicable=instance.max_staggering_applicable[:],
        total_delay=solution_metrics.total_delay,
        congested_schedule=solution_metrics.congested_schedule,
        staggering_applied=staggering_applied_in_epoch,
        total_travel_time=get_total_travel_time(solution_metrics.congested_schedule),
        binaries=None
    )


def print_info_epoch_solution(epoch_status_quo, epoch_solution):
    """Prints information about the epoch solution."""
    print("#" * 20)
    print("INFO EPOCH SOLUTION")
    print("#" * 20)

    print(f"Total delay epoch status quo: {epoch_status_quo.total_delay / 60:.2f} [min]")
    print(f"Total delay epoch model solution: {epoch_solution.total_delay / 60:.2f} [min]")
    delay_reduction = (
        (epoch_status_quo.total_delay - epoch_solution.total_delay) / epoch_status_quo.total_delay
        if epoch_status_quo.total_delay > 1e-6 else 0
    )
    print(f"Total delay epoch reduction: {delay_reduction:.2%}")


def get_epoch_solution(simplified_instance, simplified_status_quo, epoch_instance, epoch_status_quo,
                       solver_params: SolverParameters) -> EpochSolution:
    """Compute the epoch solution."""
    if len(simplified_status_quo.congested_schedule):
        epoch_warm_start = get_epoch_warm_start(simplified_instance, simplified_status_quo, solver_params)
        model = construct_model(simplified_instance, simplified_status_quo, epoch_warm_start, solver_params)
        run_model(model, simplified_instance, epoch_warm_start, simplified_status_quo, solver_params)
        model_solution = get_epoch_model_solution(model, simplified_instance, simplified_status_quo, epoch_warm_start,
                                                  solver_params)
        # Map back to the full system
        epoch_solution = map_simplified_epoch_solution(epoch_instance, model_solution, solver_params)
        print_info_epoch_solution(epoch_status_quo, epoch_solution)
        return epoch_solution
    else:
        return epoch_status_quo
